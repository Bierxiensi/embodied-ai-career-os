"""简历版本（Resume Version）。

一岗一版：针对主攻 / 卡位 / 保底赛道分别维护一份简历 md，
content_md 是待诊断 / 投递的原文，is_primary 标记当前主版本。

target_tier 与战略梯队对齐（1=主攻 / 2=卡位 / 3=保底），
前端按 TIER→track 映射展示（1→llm / 2→vlm / 3→ai-algo）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.job_posting import TIER_CARD, TIER_PRIMARY, TIER_SAFE


class ResumeVersion(Base):
    """一份简历版本（md 原文）。"""

    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 版本标签，如 "LLM 主攻版" / "VLM 卡位版"
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # 简历 md 原文（待诊断 / 投递）
    content_md: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 战略梯队 1/2/3（与 target_roles 对齐）
    target_tier: Mapped[int] = mapped_column(Integer, default=TIER_CARD, nullable=False)

    # 是否当前主版本（全局仅一个 True）
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# 重新导出梯队常量，方便 API / 前端引用
TIER_PRIMARY = TIER_PRIMARY
TIER_CARD = TIER_CARD
TIER_SAFE = TIER_SAFE
