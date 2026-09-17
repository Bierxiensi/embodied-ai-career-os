"""练习记录模型（Practice Record）。

记录每次答题的用户答案、正确性、得分和反馈，用于统计分析。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PracticeRecord(Base):
    """一次练习记录。"""

    __tablename__ = "practice_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interview_questions.id"), nullable=False
    )

    # 本次实际题型：open / choice / fill / judge
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)

    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    correct: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON string[]: 覆盖了哪些要点
    outline_covered: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON string[]: 缺了哪些要点
    outline_missed: Mapped[str | None] = mapped_column(Text, nullable=True)

    skill_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # single | quiz
    mode: Mapped[str] = mapped_column(String(20), default="single", nullable=False)

    # 小测验 session（同一套题共享一个 session_id）
    session_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
