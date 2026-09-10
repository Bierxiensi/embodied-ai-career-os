"""面试题库模型（Interview Question）。

支撑"模拟面试出题 / 题库练习"：按 category 分类，含难度、答题要点、来源、命中次数。
抽题为纯规则（见 agents/interview/engine.py pick_questions），不依赖 LLM。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 题库分类（对齐 v2.0：LLM / Multimodal / Project / Coding）
QUESTION_CATEGORY_LLM = "LLM"
QUESTION_CATEGORY_MULTIMODAL = "Multimodal"
QUESTION_CATEGORY_PROJECT = "Project"
QUESTION_CATEGORY_CODING = "Coding"

QUESTION_CATEGORIES: list[str] = [
    QUESTION_CATEGORY_LLM,
    QUESTION_CATEGORY_MULTIMODAL,
    QUESTION_CATEGORY_PROJECT,
    QUESTION_CATEGORY_CODING,
]

# 难度
DIFFICULTY_BEGINNER = "beginner"
DIFFICULTY_INTERMEDIATE = "intermediate"
DIFFICULTY_ADVANCED = "advanced"

DIFFICULTIES: list[str] = [
    DIFFICULTY_BEGINNER,
    DIFFICULTY_INTERMEDIATE,
    DIFFICULTY_ADVANCED,
]


class InterviewQuestion(Base):
    """一道面试题（题库）。"""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 分类：LLM / Multimodal / Project / Coding
    category: Mapped[str] = mapped_column(String(30), nullable=False)

    question: Mapped[str] = mapped_column(Text, nullable=False)

    # 难度：beginner / intermediate / advanced
    difficulty: Mapped[str] = mapped_column(String(20), default=DIFFICULTY_INTERMEDIATE, nullable=False)

    # 答题要点 / 参考答案大纲
    answer_outline: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 来源：面经 / 自编 / 论文 / 项目
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 被抽中/练习次数（抽题时 +1）
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
