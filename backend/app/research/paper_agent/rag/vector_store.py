"""向量库：存储 + 检索 chunk 向量。

抽象 + SQLite 实现：
    - VectorStore（抽象）：upsert / search / delete / count 统一契约
    - SQLiteVectorStore：向量存 JSON 于 paper_chunk_embeddings 表，
      检索用纯 Python 余弦相似度（数据量百级，全表扫描可接受）

设计要点：
- 零依赖：不引入 numpy / faiss，纯 Python 计算余弦
- 归一化假设：embedder 产出已 L2 归一化，余弦 = 点积，省去分母计算
- 多模型隔离：按 model_name 过滤，支持开发态 hash + 生产态 ST 共存
- section 过滤：检索时可选按 chunk section 缩小范围（method/experiment...）
- 线程安全：所有操作基于独立 db session，无共享可变状态
"""

from __future__ import annotations

import json
import math
import uuid
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from app.models.paper_chunk import PaperChunk
from app.models.paper_chunk_embedding import PaperChunkEmbedding


class VectorStore(ABC):
    """向量库抽象基类。

    子类需实现 upsert / search / delete / count。
    所有方法接收外部传入的 db session，调用方负责生命周期。
    """

    @abstractmethod
    def upsert(
        self,
        db: Session,
        chunk_id: str,
        embedding: list[float],
        model_name: str,
    ) -> str:
        """写入/更新单条向量（已存在同 chunk_id+model_name 则覆盖）。

        Returns:
            embedding 记录 id
        """
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        db: Session,
        query_vec: list[float],
        model_name: str,
        top_k: int = 5,
        section: str | None = None,
        paper_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """检索 top-k 最相似 chunk。

        Args:
            query_vec: 查询向量（应已归一化）
            model_name: 限定嵌入模型，避免跨模型比较
            top_k: 返回数量
            section: 可选，按 chunk.section 过滤
            paper_id: 可选，限定单篇论文检索（RAG #4：下推到向量库层过滤，
                避免全局取 top_k 后再过滤导致该论文 chunk 被挤出召回）

        Returns:
            [{"chunk_id", "text", "section", "page", "score"}, ...]
            按 score 降序，score ∈ [0, 1]（归一化向量的余弦）
        """
        raise NotImplementedError

    @abstractmethod
    def delete_by_chunk(self, db: Session, chunk_id: str, model_name: str) -> int:
        """删除指定 chunk 的向量。Returns: 删除条数。"""
        raise NotImplementedError

    @abstractmethod
    def count(self, db: Session, model_name: str) -> int:
        """统计某模型的向量总数。"""
        raise NotImplementedError


class SQLiteVectorStore(VectorStore):
    """基于 SQLite + paper_chunk_embeddings 表的向量库实现。

    向量以 JSON 字符串存储，检索时加载到内存计算余弦相似度。
    适用于百级 chunk 的开发态/小规模场景；万级以上需切 faiss / ChromaDB。
    """

    def upsert(
        self,
        db: Session,
        chunk_id: str,
        embedding: list[float],
        model_name: str,
    ) -> str:
        """写入向量，同 chunk_id+model_name 已存在则覆盖。"""
        existing = (
            db.query(PaperChunkEmbedding)
            .filter(
                PaperChunkEmbedding.chunk_id == chunk_id,
                PaperChunkEmbedding.model_name == model_name,
            )
            .first()
        )

        if existing is not None:
            # 覆盖更新（force_rebuild 场景）
            existing.embedding = json.dumps(embedding)
            existing.dim = len(embedding)
            db.flush()
            return existing.id

        rec = PaperChunkEmbedding(
            id=str(uuid.uuid4()),
            chunk_id=chunk_id,
            embedding=json.dumps(embedding),
            model_name=model_name,
            dim=len(embedding),
        )
        db.add(rec)
        db.flush()
        return rec.id

    def search(
        self,
        db: Session,
        query_vec: list[float],
        model_name: str,
        top_k: int = 5,
        section: str | None = None,
        paper_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """检索 top-k：加载同模型向量 → 纯 Python 余弦 → 排序截断。"""
        # 查询同模型的 embedding，join paper_chunks 取原文 + section
        query = (
            db.query(PaperChunkEmbedding, PaperChunk)
            .join(PaperChunk, PaperChunkEmbedding.chunk_id == PaperChunk.id)
            .filter(PaperChunkEmbedding.model_name == model_name)
        )
        if section:
            query = query.filter(PaperChunk.section == section)
        # RAG #4 修复：paper_id 下推到向量库层过滤，避免全局取 top_k 后再过滤
        if paper_id:
            query = query.filter(PaperChunk.paper_id == paper_id)

        rows = query.all()
        if not rows:
            return []

        # 计算余弦相似度（归一化向量点积）
        scored: list[tuple[float, PaperChunk]] = []
        for emb_rec, chunk in rows:
            try:
                vec = json.loads(emb_rec.embedding)
            except (json.JSONDecodeError, TypeError):
                continue
            score = _cosine(query_vec, vec)
            scored.append((score, chunk))

        # 降序排序取 top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "chunk_id": chunk.id,
                "paper_id": chunk.paper_id,
                "text": chunk.text,
                "section": chunk.section,
                "page": chunk.page,
                "score": round(score, 4),
            }
            for score, chunk in scored[:top_k]
        ]

    def delete_by_chunk(self, db: Session, chunk_id: str, model_name: str) -> int:
        """删除指定 chunk + 模型的向量记录。"""
        deleted = (
            db.query(PaperChunkEmbedding)
            .filter(
                PaperChunkEmbedding.chunk_id == chunk_id,
                PaperChunkEmbedding.model_name == model_name,
            )
            .delete(synchronize_session=False)
        )
        return int(deleted)

    def count(self, db: Session, model_name: str) -> int:
        """统计某模型的向量数。"""
        return (
            db.query(PaperChunkEmbedding)
            .filter(PaperChunkEmbedding.model_name == model_name)
            .count()
        )

    def get_indexed_chunk_ids(
        self, db: Session, model_name: str
    ) -> set[str]:
        """获取已索引的 chunk_id 集合（indexer 增量构建用）。"""
        rows = (
            db.query(PaperChunkEmbedding.chunk_id)
            .filter(PaperChunkEmbedding.model_name == model_name)
            .all()
        )
        return {r[0] for r in rows}


def _cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度。

    假设 a/b 已归一化（embedder 保证），退化为点积；
    但仍做分母兜底，防御未归一化输入。
    """
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return dot / (norm_a * norm_b)


# 模块级单例（无状态，全局复用）
_default_store: SQLiteVectorStore | None = None


def get_vector_store() -> SQLiteVectorStore:
    """获取默认 SQLiteVectorStore 单例（无状态，线程安全）。"""
    global _default_store
    if _default_store is None:
        _default_store = SQLiteVectorStore()
    return _default_store
