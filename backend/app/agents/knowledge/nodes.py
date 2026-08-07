"""Paper Knowledge Agent 节点。

两节点 LangGraph：
    - retrieve_node：RAG 检索 → 命中 chunks
    - answer_node：基于 chunks 规则组答（Day 3 无 LLM）

设计要点：
- retrieve 复用 Day 2 的 rag.retriever（语义检索 + section 过滤 + 富化）
- answer 用规则拼接：提取最相关 chunk 文本 + 引用列表 + 置信度评估
  （Week 2+ 接 LLM 后，answer_node 替换为 LLM 调用，签名不变）
- 引用可追溯：每条答案带 chunk_id / paper_title / section，便于前端展示
"""

from __future__ import annotations

from typing import Any

from app.db.base import SessionLocal
from app.research.paper_agent.rag.embedder import get_embedder
from app.research.paper_agent.rag.retriever import search, search_by_paper
from app.research.paper_agent.rag.vector_store import get_vector_store

from app.agents.knowledge.state import Citation, KnowledgeAnswer, KnowledgeState


# ============================================================
# 节点 1：检索
# ============================================================

def retrieve_node(state: KnowledgeState) -> dict[str, Any]:
    """RAG 检索：question → 命中 chunks。

    支持 paper_id 限定单篇论文、section 过滤章节。
    db 未注入时用 SessionLocal 自建（独立 session）。
    """
    question = state.get("question", "").strip()
    if not question:
        return {"retrieved_chunks": []}

    top_k = state.get("top_k", 5)
    section = state.get("section") or None
    paper_id = state.get("paper_id") or None

    # db 由 API 层注入；未注入时自建（节点内独立 session）
    db = state.get("db")
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        embedder = get_embedder()
        store = get_vector_store()

        if paper_id:
            # 限定单篇论文检索
            hits = search_by_paper(
                db, question, paper_id,
                top_k=top_k, section=section,
                embedder=embedder, store=store,
            )
        else:
            hits = search(
                db, question,
                top_k=top_k, section=section,
                embedder=embedder, store=store,
            )
        return {"retrieved_chunks": hits}
    finally:
        if own_session:
            db.close()


# ============================================================
# 节点 2：组答
# ============================================================

# 答案最大字符数（避免拼接过长）
_MAX_ANSWER_CHARS = 800
# 单条引用原文最大字符数
_MAX_CITATION_TEXT = 200
# 置信度阈值：top score 高于此值为 high，否则按命中数判定
_HIGH_CONFIDENCE_THRESHOLD = 0.35


def answer_node(state: KnowledgeState) -> dict[str, Any]:
    """基于检索 chunks 规则组答。

    策略：
    1. 无命中 → 返回"未找到相关内容"低置信度答案
    2. 有命中 → 取 top-N chunks 文本拼接为答案，附引用列表
    3. 置信度：top score >= 阈值 or 命中数 >= 3 → high；命中 1-2 → medium
    """
    chunks = state.get("retrieved_chunks", [])
    question = state.get("question", "")
    embedder = get_embedder()

    if not chunks:
        return {
            "answer": KnowledgeAnswer(
                question=question,
                answer="未在知识库中找到与该问题相关的内容。请先通过 /api/paper/ingest 导入论文并执行 /api/paper/index 构建索引。",
                citations=[],
                confidence="low",
                model_name=embedder.model_name,
                hit_count=0,
            )
        }

    # 构造引用列表（保留全部命中，前端可展示来源）
    citations: list[Citation] = []
    for c in chunks:
        citations.append(Citation(
            chunk_id=c.get("chunk_id", ""),
            paper_id=c.get("paper_id", ""),
            paper_title=c.get("paper_title", ""),
            section=c.get("section", "unknown"),
            page=c.get("page", 1),
            score=c.get("score", 0.0),
            text=c.get("text", "")[:_MAX_CITATION_TEXT],
        ))

    # 拼接答案：取最相关的 chunk 文本（截断到 _MAX_ANSWER_CHARS）
    answer_parts: list[str] = []
    total_len = 0
    for c in chunks:
        text = c.get("text", "").strip()
        if not text:
            continue
        # 标注来源章节，便于阅读
        section = c.get("section", "unknown")
        snippet = f"[{section}] {text}"
        if total_len + len(snippet) > _MAX_ANSWER_CHARS:
            # 截断到最后一个完整句
            remain = _MAX_ANSWER_CHARS - total_len
            snippet = snippet[:remain].rsplit(". ", 1)[0] + "..."
        answer_parts.append(snippet)
        total_len += len(snippet)
        if total_len >= _MAX_ANSWER_CHARS:
            break

    answer_text = "\n\n".join(answer_parts)

    # 置信度评估
    top_score = chunks[0].get("score", 0.0)
    if top_score >= _HIGH_CONFIDENCE_THRESHOLD or len(chunks) >= 3:
        confidence = "high"
    elif len(chunks) >= 1:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "answer": KnowledgeAnswer(
            question=question,
            answer=answer_text,
            citations=citations,
            confidence=confidence,
            model_name=embedder.model_name,
            hit_count=len(chunks),
        )
    }
