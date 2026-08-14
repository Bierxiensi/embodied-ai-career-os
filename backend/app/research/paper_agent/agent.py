"""PaperAgent 适配类 + LangGraph。

复用 Phase 2 core/ 框架（BaseAgent / AgentExecutor / AgentRegistry）。
将 parser → chunker → summarizer → persist → index 编排为 LangGraph：

    START → parse_node → chunk_node → summarize_node → persist_node → index_node → END

Day 5 新增 index_node：persist 后自动对 chunks 构建 RAG 向量索引，
实现"ingest 即可检索"的一体化流程，无需再手动调 /api/paper/index。

每个节点接收 state，返回 dict（LangGraph 合并到状态）。
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.agents.core.agent import BaseAgent
from app.agents.core.state import AgentState
from app.db.base import SessionLocal
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk as PaperChunkModel
from app.research.paper_agent.chunker import chunk as chunk_text
from app.research.paper_agent.parser import parse as parse_paper
from app.research.paper_agent.schema import PaperChunk, PaperMeta, PaperSummary
from app.research.paper_agent.summarizer import summarize as summarize_chunks


class PaperAgentState(AgentState, total=False):
    """PaperAgent 状态。

    输入：file_path / auto_index
    中间产物：text / meta / chunks / summary
    输出：paper_id / indexed_count / index_model
    """

    file_path: str                       # 输入：论文文件路径
    auto_index: bool                     # 输入：是否 ingest 后自动建索引（默认 True）
    text: str                            # parser 产出
    meta: PaperMeta                      # parser 产出
    chunks: list[PaperChunk]             # chunker 产出
    summary: PaperSummary                # summarizer 产出
    paper_id: str                        # persist 产出
    indexed_count: int                   # index 产出：本次索引的 chunk 数
    index_model: str                     # index 产出：嵌入模型名


# ============================================================
# Graph 节点
# ============================================================

def parse_node(state: PaperAgentState) -> dict:
    """节点1：解析论文文件 → 文本 + 元数据。"""
    file_path = state.get("file_path", "")
    if not file_path:
        raise ValueError("file_path 不能为空")

    text, meta = parse_paper(file_path)
    return {"text": text, "meta": meta}


def chunk_node(state: PaperAgentState) -> dict:
    """节点2：分块 → 语义 chunk 列表。

    paper_id 在此节点预生成，供 chunker 写入 chunk.paper_id。
    """
    text = state.get("text", "")
    meta = state.get("meta", {})
    paper_id = str(uuid.uuid4())  # 预生成 paper_id

    chunks = chunk_text(text, meta, paper_id)
    return {"chunks": chunks, "paper_id": paper_id}


def summarize_node(state: PaperAgentState) -> dict:
    """节点3：摘要 → PaperSummary。"""
    chunks = state.get("chunks", [])
    meta = state.get("meta", {})
    summary = summarize_chunks(chunks, meta)
    return {"summary": summary}


def persist_node(state: PaperAgentState) -> dict:
    """节点4：持久化 → papers + paper_chunks 表。

    db 由 API 层注入；未注入时用 SessionLocal 自建（独立 session）。
    """
    db = state.get("db")
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        meta = state.get("meta", {})
        summary = state.get("summary", {})
        chunks = state.get("chunks", [])
        paper_id = state.get("paper_id", str(uuid.uuid4()))

        # 写 papers 表
        paper = Paper(
            id=paper_id,
            title=summary.get("title", meta.get("title_hint", "Unknown")),
            source_path=meta.get("source_path", ""),
            file_type=meta.get("file_type", "txt"),
            arxiv_id=meta.get("arxiv_id"),
            method=summary.get("method", ""),
            dataset=summary.get("dataset", ""),
            contribution=summary.get("contribution", ""),
            relation_to_my_project=summary.get("relation_to_my_project", ""),
            confidence=summary.get("confidence", "low"),
            page_count=meta.get("page_count", 1),
            chunk_count=len(chunks),
        )
        db.add(paper)

        # 写 paper_chunks 表（批量）
        for c in chunks:
            db.add(PaperChunkModel(
                id=c.get("chunk_id", str(uuid.uuid4())),
                paper_id=paper_id,
                text=c.get("text", ""),
                section=c.get("section", "unknown"),
                page=c.get("page", 1),
                char_offset=c.get("char_offset", 0),
                token_count=c.get("token_count", 0),
            ))

        db.commit()
        return {"paper_id": paper_id}
    except Exception:
        db.rollback()
        raise
    finally:
        if own_session:
            db.close()


def index_node(state: PaperAgentState) -> dict:
    """节点5：RAG 索引构建（Day 5 新增）。

    persist 后自动对新入库的 chunks 嵌入入向量库，
    实现"ingest 即可检索"。auto_index=False 时跳过。

    复用 Day 2 的 indexer.build_index，限定 paper_id 增量索引。
    db 复用 persist 的 session（若注入），否则自建。
    """
    # auto_index 默认 True；显式 False 才跳过
    if state.get("auto_index", True) is False:
        return {"indexed_count": 0, "index_model": ""}

    # 延迟导入避免循环依赖（rag.indexer 导入 models，与本模块无环）
    from app.research.paper_agent.rag.indexer import build_index

    paper_id = state.get("paper_id", "")
    if not paper_id:
        return {"indexed_count": 0, "index_model": ""}

    db = state.get("db")
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        # 限定本论文增量索引（只嵌入刚入库的 chunks）
        # API #2 修复：index 失败不中断已 persist 的论文。
        # persist_node 已成功落库论文与 chunks，index 仅是增强检索能力，
        # 失败时返回 partial success（indexed_count=0），论文仍可正常展示与重试索引。
        result = build_index(db, paper_id=paper_id)
        return {
            "indexed_count": result.indexed,
            "index_model": result.model_name,
        }
    except Exception as e:  # noqa: BLE001
        # 索引失败：记录日志但不抛出，保留已 persist 的论文数据
        import logging
        logging.getLogger(__name__).warning(
            "index_node 构建索引失败（论文 %s 已 persist，索引可重试）: %s", paper_id, e
        )
        return {"indexed_count": 0, "index_model": ""}
    finally:
        if own_session:
            db.close()


# ============================================================
# Graph 构建
# ============================================================

def build_paper_graph() -> Any:
    """构建 PaperAgent LangGraph。

    流程：parse → chunk → summarize → persist → index

    Day 5 新增 index 节点，ingest 后自动建 RAG 索引。
    """
    graph = StateGraph(PaperAgentState)
    graph.add_node("parse", parse_node)
    graph.add_node("chunk", chunk_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("persist", persist_node)
    graph.add_node("index", index_node)

    graph.add_edge(START, "parse")
    graph.add_edge("parse", "chunk")
    graph.add_edge("chunk", "summarize")
    graph.add_edge("summarize", "persist")
    graph.add_edge("persist", "index")
    graph.add_edge("index", END)

    return graph.compile()


# ============================================================
# PaperAgent 适配类
# ============================================================

class PaperAgent(BaseAgent):
    """Paper Agent，复用 Phase 2 core/ 框架。

    业务逻辑全部在 parser / chunker / summarizer，本类仅做框架适配。
    """

    _graph: Any = None

    def __init__(self) -> None:
        if PaperAgent._graph is None:
            PaperAgent._graph = build_paper_graph()

    @property
    def name(self) -> str:
        return "paper"

    @property
    def state_class(self) -> type:
        return PaperAgentState

    def build_graph(self) -> Any:
        """返回预编译的 CompiledGraph。"""
        return PaperAgent._graph
