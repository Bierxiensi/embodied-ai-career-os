"""JD 匹配结果模型（Job Match）。

JobPosting 1:1 JobMatch：匹配结果单独存，可重算、可对比、可解释。
维度分与差距以 JSON 存储，前端抽屉里逐维展示"为什么是这个分"。

评分口径严格对齐《求职 Agent 开发与运行规范 v2.0 §22》：
    match_score = 技术栈 40% + 项目 25% + 学历/年限 15% + 科研 10% + 行业 10%
    A ≥ 80（强匹配优先投）| B ≥ 65（正常投）| C ≥ 50（有缺口可练手）| D < 50（不推荐）
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 匹配等级阈值（v2.0 §22）
GRADE_A = "A"   # ≥ 80
GRADE_B = "B"   # ≥ 65
GRADE_C = "C"   # ≥ 50
GRADE_D = "D"   # < 50

GRADE_ORDER = [GRADE_A, GRADE_B, GRADE_C, GRADE_D]

# 5 维权重（v2.0 §22）
WEIGHT_TECH = 0.40
WEIGHT_PROJECT = 0.25
WEIGHT_EDU_EXP = 0.15
WEIGHT_RESEARCH = 0.10
WEIGHT_INDUSTRY = 0.10

# 维度键（dimension_scores 与前端一致）
DIM_TECH = "tech_stack"
DIM_PROJECT = "project"
DIM_EDU_EXP = "edu_exp"
DIM_RESEARCH = "research"
DIM_INDUSTRY = "industry"

GRADE_LABELS: dict[str, str] = {
    GRADE_A: "强匹配 · 优先投",
    GRADE_B: "正常投",
    GRADE_C: "有缺口 · 练手",
    GRADE_D: "暂不推荐",
}


def grade_of(score: int) -> str:
    """分数 → 等级（v2.0 §22 阈值）。"""
    if score >= 80:
        return GRADE_A
    if score >= 65:
        return GRADE_B
    if score >= 50:
        return GRADE_C
    return GRADE_D


class JobMatch(Base):
    """某岗位与当前能力画像的匹配结果（每岗位一条，重算即更新）。"""

    __tablename__ = "job_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联岗位（1:1，唯一）
    posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # 总分 0-100
    match_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 等级 A/B/C/D
    grade: Mapped[str] = mapped_column(String(4), default=GRADE_D, nullable=False)

    # 5 维分项（dict，键见 DIM_* 常量）
    dimension_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 差距清单：[{skill, level, required, gap}]，按 gap 降序
    gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 实际对标赛道（匹配时取的 track）
    matched_track: Mapped[str | None] = mapped_column(String(50), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
