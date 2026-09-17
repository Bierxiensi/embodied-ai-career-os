"""面试题库模型（Interview Question）。

支撑"模拟面试出题 / 题库练习"：按 category 分类，含难度、答题要点、来源、命中次数。
抽题为纯规则（见 agents/interview/engine.py pick_questions），不依赖 LLM。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
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

    # 题型：open / choice / fill / judge（默认 open = 开放问答）
    question_type: Mapped[str] = mapped_column(
        String(20), default="open", server_default="open", nullable=False
    )
    # 手动配置的选项（JSON），仅 choice 类型有值
    # 格式：{"choices": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct": "B"}
    options: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 难度：beginner / intermediate / advanced
    difficulty: Mapped[str] = mapped_column(String(20), default=DIFFICULTY_INTERMEDIATE, nullable=False)

    # 答题要点 / 参考答案大纲
    answer_outline: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 来源：面经 / 自编 / 论文 / 项目
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # P2：题目归属的课程日序号（1..30），用于「四件套 questions 由题库条数自动判定」
    # 不绑定具体 plan_day_id，只绑 seq（与日历解耦，和 day_progress 同一哲学）
    source_day_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # P2：题目关联的技能名（evidence-gated 用，如 "LoRA/QLoRA"）
    skill_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # P2：是否通过面试验收验证（答得出来才算有效证据）
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )

    # 被抽中/练习次数（抽题时 +1）
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
