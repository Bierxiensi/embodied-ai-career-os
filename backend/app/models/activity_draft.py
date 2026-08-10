"""活动草稿模型。

被动感知层（GitHub commit / 文件变更）产出的待确认活动。
用户确认后触发 Reviewer 复盘。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityDraft(Base):
    __tablename__ = "activity_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # source: github_commit | evening_checkin | manual
    source_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 引用：commit_sha / task_id
    task_guess: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_guess: Mapped[str | None] = mapped_column(String(100), nullable=True)
    suggested_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_confirm", index=True)
    # status: pending_confirm | confirmed | rejected | expired
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
