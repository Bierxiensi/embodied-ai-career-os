"""论文索引器：paper_chunks → 向量库。

职责：
    扫描 paper_chunks 表 → 对未索引的 chunk 嵌入 → 写入向量库

设计要点：
- 增量构建：默认只索引未存在向量的 chunk，避免重复嵌入
- 批量嵌入：用 embed_batch 一次处理多个 chunk（ST 批量推理快一个数量级）
- 可选重建：force_rebuild=True 时清空旧向量重建（切换模型后用）
- 范围限定：可按 paper_id 限定索引范围
- 事务安全：整批嵌入后统一 commit，失败回滚
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.paper_chunk import PaperChunk
from app.research.paper_agent.rag.embedder import Embedder, get_embedder
from app.research.paper_agent.rag.vector_store import SQLiteVectorStore, get_vector_store


@dataclass
class IndexResult:
    """索引构建结果。"""

    total_chunks: int = 0       # 扫描的 chunk 总数
    indexed: int = 0            # 本次新嵌入数
    skipped: int = 0            # 已存在跳过数
    model_name: str = ""        # 使用的嵌入模型


def build_index(
    db: Session,
    paper_id: str | None = None,
    force_rebuild: bool = False,
    embedder: Embedder | None = None,
    store: SQLiteVectorStore | None = None,
    batch_size: int = 32,
) -> IndexResult:
    """构建论文 chunk 向量索引。

    Args:
        db: 数据库会话（调用方管理生命周期）
        paper_id: 限定单篇论文，None 则索引全部
        force_rebuild: True 时先删旧向量再重建（切模型后用）
        embedder: 嵌入器，None 用默认（工厂 fallback）
        store: 向量库，None 用默认单例
        batch_size: 批量嵌入批次大小

    Returns:
        IndexResult：扫描/新索引/跳过计数 + 模型名
    """
    embedder = embedder or get_embedder()
    store = store or get_vector_store()
    model_name = embedder.model_name

    # 1. 查询待索引 chunks
    query = db.query(PaperChunk)
    if paper_id:
        query = query.filter(PaperChunk.paper_id == paper_id)
    all_chunks = query.all()

    if not all_chunks:
        return IndexResult(total_chunks=0, model_name=model_name)

    # 2. 确定待嵌入集合（增量 or 全量重建）
    if force_rebuild:
        # 清空该模型下（可选 paper_id 范围）的旧向量
        for c in all_chunks:
            store.delete_by_chunk(db, c.id, model_name)
        db.flush()
        to_embed = all_chunks
        skipped = 0
    else:
        # 增量：跳过已索引
        indexed_ids = store.get_indexed_chunk_ids(db, model_name)
        to_embed = [c for c in all_chunks if c.id not in indexed_ids]
        skipped = len(all_chunks) - len(to_embed)

    # 3. 批量嵌入 + 入库
    indexed_count = 0
    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i : i + batch_size]
        texts = [c.text for c in batch]
        # 批量嵌入（HashEmbedder 逐个，ST 批量推理）
        vectors = embedder.embed_batch(texts)

        for chunk, vec in zip(batch, vectors):
            store.upsert(db, chunk.id, vec, model_name)
            indexed_count += 1

    db.commit()
    return IndexResult(
        total_chunks=len(all_chunks),
        indexed=indexed_count,
        skipped=skipped,
        model_name=model_name,
    )
