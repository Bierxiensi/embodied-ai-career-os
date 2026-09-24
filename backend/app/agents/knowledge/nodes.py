"""Paper Knowledge Agent 节点。

两节点 LangGraph：
    - retrieve_node：RAG 检索 → 命中 chunks
    - answer_node：基于 chunks 组答（**LLM 优先，规则兜底**）

设计要点：
- retrieve 复用 Day 2 的 rag.retriever（语义检索 + section 过滤 + 富化）
- answer 分两路（2026-09-23 接通 LLM）：
    ① LLM 组答：把 top-N chunk 作为 context 交给 get_llm() 生成成句回答
    ② 规则组答：LLM 不可用（未配置 provider / 调用失败）时，回落为
       "提取最相关 chunk 文本 + 引用列表 + 置信度评估" 的拼接实现
  返回结构 KnowledgeAnswer 两路完全一致，另用 `answer_mode` 标注实际走的哪条路
  （llm / rule），避免"降级了但看不出来"。
- 引用可追溯：每条答案带 chunk_id / paper_title / section，便于前端展示
"""

from __future__ import annotations

import warnings
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
# 置信度阈值：基于 top score（检索质量）——**与组答走 LLM 还是规则无关**，检索不到就是检索不到。
#
# 🔴 2026-09-23 重新标定（原判据有 bug）：
#   原实现为 `if top_score >= 0.35 or len(chunks) >= 3` —— 但检索**总是返回 top_k 条**
#   （默认 5），所以 `len(chunks) >= 3` 恒真 → **置信度永远是 high**。
#   实测后果：问"如何修复 React 内存泄漏"（完全在语料外）也返回 high。
#
#   用真语义嵌入（all-MiniLM-L6-v2）实测两组问题的 top score 分布：
#     相关问题（5 题）：0.582 / 0.661 / 0.582 / 0.729 / 0.723   → min 0.582
#     无关问题（5 题）：0.215 / 0.399 / 0.295 / 0.304 / 0.268   → max 0.399
#   分离间隙 0.183，故 high 阈值取 0.50（落在间隙内）、medium 取 0.35。
#   ⚠️ 这两个数是**跟当前嵌入模型绑定**的；换嵌入模型后必须用
#      `.workbuddy/tmp/calibrate_confidence.py` 重新标定。
_HIGH_CONFIDENCE_THRESHOLD = 0.50
_MEDIUM_CONFIDENCE_THRESHOLD = 0.35
# LLM 组答时喂给模型的 context 字符预算（chunk 单块约 800-1000 字符）
_MAX_CONTEXT_CHARS = 6000


def _compose_with_llm(question: str, chunks: list[dict[str, Any]]) -> str | None:
    """用 LLM 基于检索片段生成成句回答。不可用时返回 None（调用方回落规则组答）。

    回落条件（任一）：
      1. 客户端是 MockClient —— 未配置真实 provider。Mock 的固定模板文案
         **绝不能当成"知识库答案"返回给用户**，必须回落规则组答。
      2. 调用抛异常 / 返回空串。

    与 `agents/research/nodes.py:_match_with_llm`、`agents/supervisor/nodes.py:_analyze_intent_llm`
    同款契约：**失败返回 None，由调用方决定降级路径**，保证 API 永不 500。
    参照实现：`api/practice.py` 的 `_llm_score` 用 `_parse_error` 判 mock，
    这里走的是纯文本 chat，无 JSON 可解析，故显式判 MockClient 类型。
    """
    from app.llm import ChatMessage, get_llm
    from app.llm.providers import MockClient

    try:
        llm = get_llm()
    except Exception as e:  # noqa: BLE001
        warnings.warn(f"知识库取 LLM 客户端失败，回落规则组答：{e}", stacklevel=2)
        return None

    if isinstance(llm, MockClient):
        return None

    # 组装 context（按检索得分从高到低，超出预算即停）
    parts: list[str] = []
    total = 0
    for c in chunks:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        snippet = (
            f"[{c.get('section', 'unknown')}] {c.get('paper_title', '')}\n{text}"
        )
        if total + len(snippet) > _MAX_CONTEXT_CHARS:
            break
        parts.append(snippet)
        total += len(snippet)
    if not parts:
        return None

    context = "\n\n---\n\n".join(parts)
    messages = [
        ChatMessage(
            role="system",
            content=(
                "你是论文知识库助手。只依据用户给出的资料片段回答问题。"
                "资料里没有的信息就回答「资料中未提及」，不要用常识补全，不要编造引用。"
                "回答控制在 300 字以内。"
            ),
        ),
        ChatMessage(
            role="user",
            content=f"资料片段：\n{context}\n\n问题：{question}",
        ),
    ]

    try:
        answer = (llm.chat(messages) or "").strip()
    except Exception as e:  # noqa: BLE001
        warnings.warn(f"知识库 LLM 组答失败，回落规则组答：{e}", stacklevel=2)
        return None

    return answer or None


def answer_node(state: KnowledgeState) -> dict[str, Any]:
    """基于检索 chunks 组答：LLM 优先，规则兜底。

    策略：
    1. 无命中 → 返回"未找到相关内容"低置信度答案（answer_mode=rule）
    2. 有命中 → 先试 `_compose_with_llm`（成句回答，带引用）
    3. LLM 不可用 → 回落：取 top-N chunks 文本拼接为答案
    4. 置信度：**只看 top score**（>=0.50 → high；>=0.35 → medium；否则 low）。
       与走 LLM 还是规则无关 —— 检索不到就是检索不到。
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
                answer_mode="rule",
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

    # 答案生成：LLM 优先，失败/无真 LLM 时回落规则拼接
    llm_answer = _compose_with_llm(question, chunks)

    if llm_answer:
        answer_text = llm_answer
        answer_mode = "llm"
    else:
        # 规则组答：取最相关的 chunk 文本（截断到 _MAX_ANSWER_CHARS）
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
        answer_mode = "rule"

    # 置信度评估：只看 top score。
    # ⚠️ 原实现带 `or len(chunks) >= 3` —— 检索总是返回 top_k 条，该条件恒真，
    #    导致置信度永远是 high（实测语料外问题也报 high）。已移除。
    top_score = chunks[0].get("score", 0.0)
    if top_score >= _HIGH_CONFIDENCE_THRESHOLD:
        confidence = "high"
    elif top_score >= _MEDIUM_CONFIDENCE_THRESHOLD:
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
            answer_mode=answer_mode,
        )
    }
