"""面试记录模型（Interview Log）。

求职看板 Batch 3 核心表：一次面试的完整记录，用于
1) 沉淀面经（asked_questions）
2) 定位弱项（weak_questions / jd_gaps / knowledge_gaps）
3) 回写学习任务（next_actions → Task，见 agents/interview/engine.py）

与 InterviewQuestion（题库）分离：面经是"真实发生过"的，题库是"待练习"的。
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 面试轮次常见取值（自由文本，这里仅给前端下拉建议）
ROUNDS: list[str] = ["一面", "二面", "三面", "HR", "技术面", "交叉面", "终面"]


class InterviewLog(Base):
    """一次面试记录（面经）。"""

    __tablename__ = "interview_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    company: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    round: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 被问到的问题（JSON 数组 list[str]）
    asked_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 答得不好的问题（JSON 数组，弱项来源）
    weak_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # JD 相关的能力缺口（JSON 数组）
    jd_gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 知识盲区（JSON 数组）
    knowledge_gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 下一步行动（JSON 数组，可一键转学习任务）
    next_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    interviewed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 已回写生成的学习任务 id（JSON 数组，避免重复回写）
    generated_task_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
