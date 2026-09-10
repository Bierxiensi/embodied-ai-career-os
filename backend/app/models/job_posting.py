"""岗位池模型（Job Posting Pool）。

求职看板 Batch 1 核心表：把"刷到的 JD"与"已投递记录"解耦——
先看 JD、算匹配、再决定是否投（对应 JobApplication）。

设计要点：
- tier：战略梯队（1=主攻 / 2=卡位 / 3=保底），与 target_roles 对齐
- track：对标的岗位赛道 key（llm / vlm / ai-algo / embodied / other），
  匹配引擎据此取行业分与兜底技能集
- required_skills：从 jd_text 解析出的结构化技能关键词（JSON 数组），
  匹配技术栈维度直接使用；为空时由匹配引擎回落到 track 的 required_skills
- dedup_key：去重键（公司+岗位小写），避免重复录入同一 JD
- status：open（在池）/ closed（下架）/ filled（已投/已填）
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 战略梯队枚举（与 target_roles 对齐）
TIER_PRIMARY = 1    # 主攻（llm）
TIER_CARD = 2        # 卡位（vlm）
TIER_SAFE = 3        # 保底（ai-algo）

TIER_LABELS: dict[int, str] = {
    TIER_PRIMARY: "主攻",
    TIER_CARD: "卡位",
    TIER_SAFE: "保底",
}

# 岗位状态
POSTING_OPEN = "open"
POSTING_CLOSED = "closed"
POSTING_FILLED = "filled"

POSTING_STATUS_ORDER = [POSTING_OPEN, POSTING_CLOSED, POSTING_FILLED]


class JobPosting(Base):
    """一条岗位 JD（尚未投递，在池中待匹配）。"""

    __tablename__ = "job_postings"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_job_postings_dedup"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    company: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # JD 全文（录入原始文本，解析出的技能存 required_skills）
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 来源渠道：Boss直聘 / 猎聘 / 内推 / 官网 / 其他
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    posted_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # 战略梯队 1/2/3（与 target_roles 对齐）
    tier: Mapped[int] = mapped_column(Integer, default=TIER_CARD, nullable=False)
    # 对标赛道 key（匹配引擎取行业分 / 兜底技能）
    track: Mapped[str] = mapped_column(String(50), default="llm", nullable=False)

    # 从 jd_text 解析出的结构化技能关键词
    required_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 硬性条件（规则常量维度使用）
    education: Mapped[str | None] = mapped_column(String(50), nullable=True)   # 本科 / 硕士 / 博士
    min_years: Mapped[int | None] = mapped_column(Integer, nullable=True)     # 经验年数要求
    paper_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 去重键（公司+岗位小写），为空表示未计算
    dedup_key: Mapped[str | None] = mapped_column(String(300), nullable=True, unique=True)

    status: Mapped[str] = mapped_column(String(20), default=POSTING_OPEN, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
