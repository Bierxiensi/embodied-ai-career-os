"""论文检索器：query → top-k 相关 chunks。

组合 embedder + vector_store，提供高层检索 API。

设计要点：
- 单一职责：只做"查询 → 向量 → 检索"，不关心索引构建
- 线程安全：无状态，每次检索用传入的 db session
- section 过滤：支持按论文结构（method/experiment...）缩小范围，
  Day 3+ 的 Knowledge Agent 可据此精准定位
- 检索结果富化：关联 papers 表带出论文标题，便于展示
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.research.paper_agent.rag.embedder import Embedder, get_embedder
from app.research.paper_agent.rag.vector_store import SQLiteVectorStore, get_vector_store


def search(
    db: Session,
    query: str,
    top_k: int = 5,
    section: str | None = None,
    embedder: Embedder | None = None,
    store: SQLiteVectorStore | None = None,
) -> list[dict[str, Any]]:
    """语义检索论文 chunks。

    Args:
        db: 数据库会话
        query: 自然语言查询（如 "ACT 用了什么数据集"）
        top_k: 返回数量
        section: 可选，按 chunk.section 过滤（method/experiment/conclusion...）
        embedder: 嵌入器，None 用默认
        store: 向量库，None 用默认

    Returns:
        [{"chunk_id", "paper_id", "text", "section", "page",
          "score", "paper_title"}, ...]
        按 score 降序。
    """
    embedder = embedder or get_embedder()
    store = store or get_vector_store()

    if not query.strip():
        return []

    # 1. 查询向量化
    query_vec = embedder.embed(query)

    # 2. 向量库检索
    hits = store.search(
        db,
        query_vec,
        model_name=embedder.model_name,
        top_k=top_k,
        section=section,
    )

    if not hits:
        return []

    # 3. 富化：批量查 paper_title，避免 N+1
    paper_ids = {h["paper_id"] for h in hits if h.get("paper_id")}
    title_map: dict[str, str] = {}
    if paper_ids:
        rows = (
            db.query(Paper.id, Paper.title)
            .filter(Paper.id.in_(paper_ids))
            .all()
        )
        title_map = {pid: title for pid, title in rows}

    for h in hits:
        h["paper_title"] = title_map.get(h.get("paper_id", ""), "")

    return hits


def search_by_paper(
    db: Session,
    query: str,
    paper_id: str,
    top_k: int = 5,
    section: str | None = None,
    embedder: Embedder | None = None,
    store: SQLiteVectorStore | None = None,
) -> list[dict[str, Any]]:
    """限定单篇论文内检索（如"这篇论文的方法是什么"）。

    在通用 search 基础上过滤 paper_id，用于 Knowledge Agent 精读场景。
    """
    hits = search(db, query, top_k=top_k * 2, section=section,
                  embedder=embedder, store=store)
    # 过滤指定 paper（多取后过滤，避免 top_k 过小漏结果）
    filtered = [h for h in hits if h.get("paper_id") == paper_id]
    return filtered[:top_k]
