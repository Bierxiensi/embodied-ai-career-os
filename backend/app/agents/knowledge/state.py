"""Paper Knowledge Agent 状态定义。

LangGraph StateGraph 在各节点间传递的状态。
total=False 允许各节点局部更新（LangGraph 合并语义）。

流转：retrieve → answer
"""

from __future__ import annotations

from typing import Any, TypedDict


class KnowledgeState(TypedDict, total=False):
    """Knowledge Agent 状态机。

    字段分组：
    - 输入：question（用户问题）、paper_id（可选限定论文）、section（可选过滤）
    - 中间态：retrieved_chunks（RAG 检索结果）
    - 输出：answer（结构化答案）
    """

    # ===== 输入 =====
    question: str                          # 用户自然语言问题
    paper_id: str                          # 可选，限定单篇论文检索
    section: str                           # 可选，按 chunk.section 过滤
    top_k: int                             # 检索返回数量，默认 5
    # S1 修复：db 必须在 schema 中声明，否则 LangGraph 静默丢弃 API 注入的 db，
    # 导致 retrieve_node 每次自建 SessionLocal，事务复用失效。
    db: Any                                # API 层注入的 db session（事务复用）

    # ===== 中间态 =====
    retrieved_chunks: list[dict[str, Any]]  # RAG 检索命中的 chunk 列表

    # ===== 输出 =====
    answer: "KnowledgeAnswer"              # 结构化答案（含引用）


class Citation(TypedDict, total=False):
    """单条引用（答案来源证据）。"""

    chunk_id: str          # chunk ID
    paper_id: str          # 所属论文 ID
    paper_title: str       # 论文标题
    section: str           # chunk 所属章节
    page: int              # 页码
    score: float           # 检索相似度分数
    text: str              # 引用原文片段


class KnowledgeAnswer(TypedDict, total=False):
    """结构化答案（answer_node 产出）。

    2026-09-23 起：answer 由 **LLM 优先、规则兜底** 两路生成，结构不变，
    另加 `answer_mode` 标注实际走的哪条路，避免"降级了但看不出来"。
    """

    question: str          # 原问题
    answer: str            # 答案正文
    citations: list[Citation]  # 引用列表（可追溯）
    confidence: str        # high / medium / low（恒基于检索质量）
    model_name: str        # 嵌入模型（标识检索来源）
    hit_count: int         # 命中 chunk 数
    answer_mode: str       # llm（成句回答）/ rule（片段拼接兜底）
