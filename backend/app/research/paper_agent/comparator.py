"""多论文对比器：横向分析多篇论文的差异与共性。

Day 4 核心模块。基于 Day 1 的结构化摘要（Paper 模型）和 Day 2 的 RAG 检索，
对多篇论文进行字段级对比，输出差异表格 + 共性 + 差异点 + 项目关联对比。

设计要点：
- 复用 Paper ORM 的结构化字段（method/dataset/contribution/relation_to_my_project）
  做字段级对比，无需 LLM
- 差异检测：同字段不同值标记为差异，相同标记为共性
- 关键词抽取：从 method 字段抽取技术关键词，对比技术栈差异
- 项目关联对比：解析 relation_to_my_project 中的项目命中（SO101/LeRobot/...）
  展示各论文与具身智能项目的关联度

输出结构 CompareResult：
    - papers：参与对比的论文基本信息
    - fields：字段级差异矩阵（method/dataset/contribution/relation）
    - commonalities：共性点列表
    - differences：差异点列表（按字段分组）
    - project_relations：各论文项目命中对比
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.paper import Paper


# 具身智能项目关键词（与 summarizer 的 _PROJECT_KEYWORDS 保持一致）
_PROJECT_KEYWORDS = [
    "SO101", "LeRobot", "Isaac", "ACT", "VLA",
    "Franka", "Robomimic", "Robosuite",
]


@dataclass
class PaperBrief:
    """论文基本信息（对比展示用）。"""

    paper_id: str
    title: str
    method: str
    dataset: str
    contribution: str
    relation_to_my_project: str
    confidence: str


@dataclass
class FieldDiff:
    """单字段差异。"""

    field: str              # 字段名：method/dataset/contribution/relation
    values: dict[str, str]  # paper_id -> 该字段值
    is_common: bool         # True=所有论文该字段相似，False=存在差异
    # RAG #12 修复：key 与展示分离。values 用 paper_id 作 key（避免 title 重复覆盖），
    # titles 提供 paper_id -> title 映射供展示层使用。
    titles: dict[str, str] = None  # type: ignore[assignment]  # paper_id -> title


@dataclass
class CompareResult:
    """多论文对比结果。"""

    papers: list[PaperBrief]
    fields: list[FieldDiff]
    commonalities: list[str]
    differences: list[str]
    project_relations: dict[str, list[str]]  # paper_title -> 命中项目列表
    paper_count: int


def compare_papers(
    db: Session,
    paper_ids: list[str],
) -> CompareResult:
    """对比多篇论文的结构化摘要。

    Args:
        db: 数据库会话
        paper_ids: 待对比论文 ID 列表（至少 2 篇）

    Returns:
        CompareResult：字段差异矩阵 + 共性 + 差异 + 项目关联

    Raises:
        ValueError: paper_ids 少于 2 篇或论文不存在
    """
    if len(paper_ids) < 2:
        raise ValueError(f"多论文对比至少需要 2 篇，实际 {len(paper_ids)} 篇")

    # 查询论文（保持 paper_ids 顺序）
    papers = (
        db.query(Paper)
        .filter(Paper.id.in_(paper_ids))
        .all()
    )
    if len(papers) < 2:
        raise ValueError(
            f"仅找到 {len(papers)} 篇论文（需要 {len(paper_ids)} 篇），"
            f"请确认 paper_id 正确且论文已 ingest"
        )

    # 按 paper_ids 顺序排列
    paper_map = {p.id: p for p in papers}
    ordered = [paper_map[pid] for pid in paper_ids if pid in paper_map]

    briefs = [_to_brief(p) for p in ordered]

    # 字段级对比
    fields = _compare_fields(briefs)

    # 共性 / 差异提取
    commonalities = _extract_commonalities(fields)
    differences = _extract_differences(fields)

    # 项目关联对比
    project_relations = _extract_project_relations(briefs)

    return CompareResult(
        papers=briefs,
        fields=fields,
        commonalities=commonalities,
        differences=differences,
        project_relations=project_relations,
        paper_count=len(briefs),
    )


def _to_brief(paper: Paper) -> PaperBrief:
    """Paper ORM → 对比用摘要。"""
    return PaperBrief(
        paper_id=paper.id,
        title=paper.title,
        method=paper.method or "",
        dataset=paper.dataset or "",
        contribution=paper.contribution or "",
        relation_to_my_project=paper.relation_to_my_project or "",
        confidence=paper.confidence or "low",
    )


def _compare_fields(briefs: list[PaperBrief]) -> list[FieldDiff]:
    """逐字段对比，判断是否相似。"""
    field_names = ["method", "dataset", "contribution", "relation_to_my_project"]
    # RAG #12 修复：title 可能重复，用 paper_id 作 key；titles 提供 paper_id -> title 映射
    titles = {b.paper_id: b.title for b in briefs}
    results: list[FieldDiff] = []

    for fname in field_names:
        values = {b.paper_id: getattr(b, fname) for b in briefs}
        # 相似判定：所有论文该字段值相同（精确匹配，保守策略）
        unique_vals = {v.strip().lower() for v in values.values() if v}
        is_common = len(unique_vals) <= 1 and len(unique_vals) >= 1
        results.append(FieldDiff(
            field=fname, values=values, is_common=is_common, titles=titles,
        ))

    return results


def _extract_commonalities(fields: list[FieldDiff]) -> list[str]:
    """提取共性点（is_common=True 的字段）。"""
    common = []
    for f in fields:
        if f.is_common and f.values:
            # 取第一个非空值作为代表
            val = next((v for v in f.values.values() if v), "")
            if val:
                common.append(f"[{f.field}] 共性：{val[:80]}")
    return common


def _extract_differences(fields: list[FieldDiff]) -> list[str]:
    """提取差异点（is_common=False 的字段）。"""
    diffs = []
    for f in fields:
        if not f.is_common:
            # RAG #12：values 用 paper_id 作 key，展示时用 titles 映射回 title
            titles = f.titles or {}
            parts = [
                f"{titles.get(pid, pid)}: {val[:60] or '空'}"
                for pid, val in f.values.items()
            ]
            diffs.append(f"[{f.field}] 差异：" + " | ".join(parts))
    return diffs


def _extract_project_relations(briefs: list[PaperBrief]) -> dict[str, list[str]]:
    """从 relation_to_my_project 提取各论文命中的项目关键词。

    返回 {paper_id: [命中的项目关键词]}（RAG #12：用 paper_id 作 key 避免 title 重复）。
    展示层可通过 papers 列表的 paper_id -> title 映射还原标题。
    """
    relations: dict[str, list[str]] = {}
    for b in briefs:
        text = b.relation_to_my_project
        # 大小写不敏感匹配项目关键词（保留原大小写展示）
        hits: list[str] = []
        for kw in _PROJECT_KEYWORDS:
            if re.search(re.escape(kw), text, re.IGNORECASE):
                # 避免重复（如 ACT 与 act）
                if kw not in hits:
                    hits.append(kw)
        relations[b.paper_id] = hits
    return relations


def compare_to_dict(result: CompareResult) -> dict[str, Any]:
    """CompareResult → 可序列化 dict（API 响应用）。

    RAG #12：内部用 paper_id 作 key 避免重复，序列化时转回 title 作 key 供前端展示。
    papers 列表同时保留 paper_id + title，前端可按需用 paper_id 精确引用。
    """
    # paper_id -> title 映射（用于展示层转换）
    title_map = {b.paper_id: b.title for b in result.papers}

    return {
        "paper_count": result.paper_count,
        "papers": [
            {
                "paper_id": b.paper_id,
                "title": b.title,
                "method": b.method,
                "dataset": b.dataset,
                "contribution": b.contribution,
                "relation_to_my_project": b.relation_to_my_project,
                "confidence": b.confidence,
            }
            for b in result.papers
        ],
        "fields": [
            {
                "field": f.field,
                # values 内部用 paper_id 作 key，输出转 title（展示友好）
                "values": {title_map.get(pid, pid): val for pid, val in f.values.items()},
                "is_common": f.is_common,
            }
            for f in result.fields
        ],
        "commonalities": result.commonalities,
        "differences": result.differences,
        # project_relations 内部用 paper_id，输出转 title
        "project_relations": {
            title_map.get(pid, pid): hits for pid, hits in result.project_relations.items()
        },
    }
