"""简历事实锚点库（Resume Fact Anchor）。

防虚构的核心数据源：简历里每一条可对外陈述的 claim 都必须能在 ResumeFact 找到依据，
否则 ResumeAgent 会将其标红（见 backend/app/agents/resume/engine.py）。

category 取值（与《求职 Agent 设计》§3 对齐）：
- work    工作经历中的可量化事实
- project 项目经历中的可量化事实
- paper   学术论文 / 专利
- edu     教育背景
- metric  指标 / 技能栈自评（用于锚定"熟悉 X"类技能 claim）

facts 为可陈述事实清单（list[str]），诊断时与 claim 做归一化子串匹配。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 事实分类枚举
FACT_CATEGORY_WORK = "work"
FACT_CATEGORY_PROJECT = "project"
FACT_CATEGORY_PAPER = "paper"
FACT_CATEGORY_EDU = "edu"
FACT_CATEGORY_METRIC = "metric"

FACT_CATEGORIES: list[str] = [
    FACT_CATEGORY_WORK,
    FACT_CATEGORY_PROJECT,
    FACT_CATEGORY_PAPER,
    FACT_CATEGORY_EDU,
    FACT_CATEGORY_METRIC,
]

FACT_CATEGORY_LABELS: dict[str, str] = {
    FACT_CATEGORY_WORK: "工作",
    FACT_CATEGORY_PROJECT: "项目",
    FACT_CATEGORY_PAPER: "论文",
    FACT_CATEGORY_EDU: "教育",
    FACT_CATEGORY_METRIC: "指标/技能",
}


class ResumeFact(Base):
    """一条可对外陈述的真实事实（防虚构锚点）。"""

    __tablename__ = "resume_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 分类：work / project / paper / edu / metric
    category: Mapped[str] = mapped_column(String(20), nullable=False)

    # 事实主题（如"标书审核 Agent"、"STM-SHAP 论文"）
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # 所属组织 / 机构（可选）
    org: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 时间区间（可选，自由文本，如 "2026.01" / "2023.09-2026.12"）
    start: Mapped[str | None] = mapped_column(String(40), nullable=True)
    end: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # 可陈述事实清单（list[str]），诊断时与 claim 做归一化子串匹配
    facts: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 来源说明（如"工作自评" / "项目复盘" / "学术成果"），用于列出依据时展示
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
