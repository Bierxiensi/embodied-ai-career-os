"""GitHub Commit 建议模型。

AI 分析 commit 后生成技能关联建议，用户确认后作为 Reviewer 证据来源之一。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommitSuggestion(Base):
    __tablename__ = "commit_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    files_changed: Mapped[list] = mapped_column(JSON, default=list)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # status: pending | confirmed | rejected
    confirmed_skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
