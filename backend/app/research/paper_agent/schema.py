"""Paper Agent 数据契约。

定义 parser / chunker / summarizer 三个模块间传递的数据结构。
所有结构均为 TypedDict(total=False)，便于 LangGraph state 合并。
"""

from __future__ import annotations

from typing import TypedDict


class PaperMeta(TypedDict, total=False):
    """论文元数据（parser 产出）。

    描述论文来源与基础信息，贯穿整个 pipeline。
    """

    source_path: str          # 原始文件路径
    file_type: str            # pdf / md / txt
    page_count: int           # PDF 页数（MD/TXT 为 1）
    title_hint: str           # 从文件名或首行提取的标题线索
    arxiv_id: str             # arxiv 论文 ID（如 2407.01827），非 arxiv 为空


class PaperChunk(TypedDict, total=False):
    """单个 chunk（chunker 产出，Day 2 入向量库）。

    chunker 按 section 优先策略切分，每个 chunk 携带结构元数据，
    便于 Day 2 向量检索时按 section / page 过滤。
    """

    chunk_id: str             # UUID
    paper_id: str             # 关联 Paper.id
    text: str                 # chunk 文本
    section: str              # abstract / introduction / method / experiment / conclusion / unknown
    page: int                 # 来源页码
    char_offset: int          # 在原文中的字符偏移
    token_count: int          # 估算 token 数（Day 2 embedding 用）


class PaperSummary(TypedDict, total=False):
    """论文摘要（summarizer 产出，Day 1 验收输出）。

    Week 2 接 LLM 后，此结构不变，仅替换 summarizer 实现。
    """

    title: str
    method: str
    dataset: str
    contribution: str
    relation_to_my_project: str   # 与 SO101/LeRobot/Isaac/ACT/VLA 的关联
    confidence: str               # high / medium / low
