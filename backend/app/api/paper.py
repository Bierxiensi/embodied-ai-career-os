"""Paper Agent API 路由。

Phase 3 Week 1：
    Day 1：POST /api/paper/ingest  论文解析入库（parser→chunker→summarizer→persist）
    Day 2：POST /api/paper/index   向量索引构建
           GET  /api/paper/search  语义检索
           GET  /api/paper/stats   索引统计
    Day 3：POST /api/paper/ask     论文问答（Knowledge Agent：retrieve → answer）
    Day 4：POST /api/paper/compare 多论文对比
    Day 5：ingest 自动建索引（parse→chunk→summarize→persist→index 一体化）

设计说明：
- ingest 触发 PaperAgent LangGraph，Day 5 起含 index 节点，ingest 即可检索
- index 触发 Day 2 的 indexer.build_index，对已入库 chunks 嵌入（批量重建用）
- search 是 Day 2 核心：自然语言 → top-k 相关 chunks
- stats 用于前端展示知识库规模（论文数 / chunk 数 / 索引覆盖率）
- ask 是 Day 3 核心：自然语言问题 → RAG 检索 → 结构化答案 + 引用
- compare 是 Day 4 核心：多论文字段级差异矩阵
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.research.paper_agent.agent import build_paper_graph
from app.research.paper_agent.rag.indexer import build_index
from app.research.paper_agent.rag.retriever import search as rag_search
from app.research.paper_agent.rag.embedder import get_embedder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/paper", tags=["paper"])

# API #3 修复：file_path 校验。允许的论文文件扩展名。
_ALLOWED_EXTS = {".pdf", ".md", ".markdown", ".txt"}


def _validate_file_path(file_path: str) -> str:
    """校验 ingest 文件路径：扩展名 + 路径穿越防护。

    Returns:
        解析后的绝对路径。

    Raises:
        HTTPException 422: 扩展名不支持或路径含穿越序列。
    """
    if not file_path or not file_path.strip():
        raise HTTPException(status_code=422, detail="file_path 不能为空")

    # 扩展名校验
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(
            status_code=422,
            detail=f"不支持的文件类型: {ext}，允许: {sorted(_ALLOWED_EXTS)}",
        )

    # 路径穿越防护：拒绝含 .. 的相对路径穿越（绝对路径解析后校验）
    raw = file_path.strip()
    if ".." in raw.split(os.sep):
        raise HTTPException(status_code=422, detail="file_path 含非法路径穿越序列")

    return raw


# ============================================================
# Day 1/5：论文解析入库（含自动索引）
# ============================================================

class IngestRequest(BaseModel):
    """论文导入请求。"""

    file_path: str = Field(..., description="论文文件路径（PDF/MD/TXT）")
    auto_index: bool = Field(
        default=True,
        description="ingest 后是否自动建 RAG 索引（Day 5，默认 True）",
    )


class IngestResponse(BaseModel):
    """论文导入结果。"""

    paper_id: str
    title: str
    chunk_count: int
    method: str = ""
    confidence: str = "low"
    indexed_count: int = 0       # Day 5：本次自动索引的 chunk 数
    index_model: str = ""        # Day 5：嵌入模型名


@router.post("/ingest")
def ingest_paper(
    payload: IngestRequest, db: Session = Depends(get_db)
) -> ApiResponse[IngestResponse]:
    """导入论文：解析 → 分块 → 摘要 → 持久化 → 索引（Day 5 一体化）。

    Day 5 起 ingest 自动建 RAG 索引，无需再手动调 /api/paper/index。
    auto_index=False 可关闭（批量 ingest 后统一索引场景）。

    API #2/#3 修复：file_path 校验 + 异常分类（404 文件不存在 / 422 解析失败 / 500 内部错误）。
    """
    # API #3：file_path 校验（扩展名 + 路径穿越）
    file_path = _validate_file_path(payload.file_path)

    # 文件不存在提前返回 404（避免进入 graph 后才报错，分类更清晰）
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")

    graph = build_paper_graph()
    try:
        out = graph.invoke({
            "file_path": file_path,
            "auto_index": payload.auto_index,
            "db": db,
        })
    except FileNotFoundError as e:
        # parser 层抛出的文件缺失（兜底，前面已预检）
        raise HTTPException(status_code=404, detail=f"文件不存在: {e}") from e
    except ValueError as e:
        # 解析失败（如 PDF 损坏、编码错误）
        raise HTTPException(status_code=422, detail=f"论文解析失败: {e}") from e
    except Exception as e:  # noqa: BLE001
        # 内部错误：rollback 已在 persist_node 处理，这里返回 500
        logger.exception("ingest_paper 内部错误: %s", e)
        raise HTTPException(status_code=500, detail=f"内部错误: {e}") from e

    summary = out.get("summary", {})
    return ok(IngestResponse(
        paper_id=out.get("paper_id", ""),
        title=summary.get("title", "Unknown"),
        chunk_count=len(out.get("chunks", [])),
        method=summary.get("method", ""),
        confidence=summary.get("confidence", "low"),
        indexed_count=out.get("indexed_count", 0),
        index_model=out.get("index_model", ""),
    ))


# ============================================================
# Day 2：向量索引
# ============================================================

class IndexRequest(BaseModel):
    """索引构建请求。"""

    paper_id: str | None = Field(
        default=None, description="限定单篇论文，None 则索引全部"
    )
    force_rebuild: bool = Field(
        default=False, description="强制重建（切换模型后用）"
    )


class IndexResponse(BaseModel):
    """索引构建结果。"""

    total_chunks: int
    indexed: int
    skipped: int
    model_name: str


@router.post("/index")
def build_paper_index(
    payload: IndexRequest, db: Session = Depends(get_db)
) -> ApiResponse[IndexResponse]:
    """构建向量索引：扫描 paper_chunks → 嵌入 → 入库。

    默认增量构建（跳过已索引）；force_rebuild=True 时清空重建。
    """
    result = build_index(
        db,
        paper_id=payload.paper_id,
        force_rebuild=payload.force_rebuild,
    )
    return ok(IndexResponse(
        total_chunks=result.total_chunks,
        indexed=result.indexed,
        skipped=result.skipped,
        model_name=result.model_name,
    ))


# ============================================================
# Day 2：语义检索
# ============================================================

class SearchHit(BaseModel):
    """单条检索结果。"""

    chunk_id: str
    paper_id: str
    paper_title: str
    text: str
    section: str
    page: int
    score: float


class SearchResponse(BaseModel):
    """检索响应。"""

    query: str
    top_k: int
    section: str | None
    model_name: str
    hits: list[SearchHit]


@router.get("/search")
def search_papers(
    query: str = Query(..., min_length=1, description="自然语言查询"),
    top_k: int = Query(default=5, ge=1, le=20),
    section: str | None = Query(default=None, description="按 section 过滤"),
    db: Session = Depends(get_db),
) -> ApiResponse[SearchResponse]:
    """语义检索论文 chunks。

    示例：
        GET /api/paper/search?query=ACT数据集&top_k=5&section=experiment
    """
    embedder = get_embedder()
    hits = rag_search(db, query, top_k=top_k, section=section)

    return ok(SearchResponse(
        query=query,
        top_k=top_k,
        section=section,
        model_name=embedder.model_name,
        hits=[SearchHit(**h) for h in hits],
    ))


# ============================================================
# 知识库统计（前端 Dashboard 用）
# ============================================================

class StatsResponse(BaseModel):
    """知识库统计。"""

    paper_count: int
    chunk_count: int
    indexed_chunk_count: int
    model_name: str
    coverage: float  # 已索引 chunk 占比


@router.get("/stats")
def paper_stats(db: Session = Depends(get_db)) -> ApiResponse[StatsResponse]:
    """知识库统计：论文数 / chunk 数 / 索引覆盖率。"""
    from app.models.paper_chunk_embedding import PaperChunkEmbedding

    paper_count = db.query(Paper).count()
    chunk_count = db.query(PaperChunk).count()

    # 取当前 embedder 模型名统计已索引数
    embedder = get_embedder()
    indexed = (
        db.query(PaperChunkEmbedding)
        .filter(PaperChunkEmbedding.model_name == embedder.model_name)
        .count()
    )

    coverage = round(indexed / chunk_count, 4) if chunk_count > 0 else 0.0
    return ok(StatsResponse(
        paper_count=paper_count,
        chunk_count=chunk_count,
        indexed_chunk_count=indexed,
        model_name=embedder.model_name,
        coverage=coverage,
    ))


# ============================================================
# Day 3：论文问答（Knowledge Agent）
# ============================================================

class AskRequest(BaseModel):
    """论文问答请求。"""

    question: str = Field(..., min_length=1, max_length=500, description="自然语言问题")
    paper_id: str | None = Field(
        default=None, description="限定单篇论文，None 则全库检索"
    )
    section: str | None = Field(
        default=None, description="按 section 过滤（method/experiment/...）"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="检索返回数量")


class CitationOut(BaseModel):
    """单条引用。"""

    chunk_id: str
    paper_id: str
    paper_title: str
    section: str
    page: int
    score: float
    text: str


class AskResponse(BaseModel):
    """论文问答响应。"""

    question: str
    answer: str
    citations: list[CitationOut]
    confidence: str
    model_name: str
    hit_count: int


@router.post("/ask")
def ask_paper(
    payload: AskRequest, db: Session = Depends(get_db)
) -> ApiResponse[AskResponse]:
    """论文问答：question → RAG 检索 → 结构化答案 + 引用。

    复用 Day 3 的 Knowledge Agent LangGraph（retrieve → answer），
    db 注入到 state 供 retrieve_node 复用。

    示例：
        POST /api/paper/ask
        {"question": "ACT 用了什么数据集？", "section": "experiment"}
    """
    from app.agents.knowledge.graph import build_knowledge_graph

    graph = build_knowledge_graph()
    out = graph.invoke({
        "question": payload.question,
        "paper_id": payload.paper_id,
        "section": payload.section,
        "top_k": payload.top_k,
        "db": db,
    })

    answer = out.get("answer", {})
    return ok(AskResponse(
        question=answer.get("question", payload.question),
        answer=answer.get("answer", ""),
        citations=[CitationOut(**c) for c in answer.get("citations", [])],
        confidence=answer.get("confidence", "low"),
        model_name=answer.get("model_name", ""),
        hit_count=answer.get("hit_count", 0),
    ))


# ============================================================
# Day 4：多论文对比
# ============================================================

class CompareRequest(BaseModel):
    """多论文对比请求。"""

    paper_ids: list[str] = Field(
        ..., min_length=2, max_length=10, description="待对比论文 ID 列表（至少 2 篇）"
    )


class CompareResponse(BaseModel):
    """多论文对比响应。"""

    paper_count: int
    papers: list[dict]
    fields: list[dict]
    commonalities: list[str]
    differences: list[str]
    project_relations: dict[str, list[str]]


@router.post("/compare")
def compare_papers_endpoint(
    payload: CompareRequest, db: Session = Depends(get_db)
) -> ApiResponse[CompareResponse]:
    """多论文对比：字段级差异矩阵 + 共性 + 差异 + 项目关联。

    基于 Day 1 的结构化摘要（Paper.method/dataset/contribution/relation）
    做横向对比，无需 LLM。

    示例：
        POST /api/paper/compare
        {"paper_ids": ["paper-id-1", "paper-id-2"]}
    """
    from app.research.paper_agent.comparator import compare_papers, compare_to_dict

    # API #4 修复：compare_papers 在 paper_ids 不足 2 篇或论文不存在时抛 ValueError，
    # 原实现未捕获导致 500。改为返回 400，让前端正确提示参数问题。
    try:
        result = compare_papers(db, payload.paper_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    data = compare_to_dict(result)
    return ok(CompareResponse(**data))
