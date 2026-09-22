"""小测验会话题目模型（Quiz Session Question）。

存放**一次测验中实际下发给用户的那道题**。

为什么需要这张表（2026-09-22）：
``POST /api/interview/quiz/start`` 会用 LLM 把题库原题改写成 choice / judge /
fill 变体。变体的正确答案只存在于生成它的那一次调用里，如果不落库，
判分端点只能拿题库原题的 ``options`` 列去找正确答案 —— 而它对生成题是 NULL。
结果就是「生成的正确答案被丢弃」，choice / judge 题被当成开放题按关键词评分。

落库后判分按 ``(session_id, question_id)`` 取回该题，生成题才判得对；
同时正确答案不下发浏览器（下发的 ``options`` 里不含哪一个是正确的）。
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuizSessionQuestion(Base):
    """一次测验中下发给用户的一道题（含真实答案，仅后端可见）。"""

    __tablename__ = "quiz_session_questions"
    # 索引名必须与 migrations/0026_quiz_session_questions.sql 保持一致，
    # 否则测试库（create_all 建）与开发库（迁移建）会长出两个同名用途的索引。
    __table_args__ = (
        Index("idx_quiz_session_questions_session", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_id: Mapped[str] = mapped_column(String(50), nullable=False)

    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interview_questions.id"), nullable=False
    )

    # 本次实际下发的题型：open / choice / judge / fill
    question_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # 本次实际下发的题干（可能是 LLM 改写后的文本）
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON string[]：choice / judge 的选项；open 为 NULL
    options: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 生成题的真实答案（不随 /quiz/start 响应下发）
    correct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)

    skill_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 在本次测验中的顺序（0 起）
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def option_list(self) -> list[str] | None:
        """把 ``options`` 解析成 list[str]；缺失或坏数据返回 None。"""

        if not self.options:
            return None
        try:
            parsed = json.loads(self.options)
        except (json.JSONDecodeError, ValueError):
            return None
        return parsed if isinstance(parsed, list) else None

    @staticmethod
    def dump_options(options: list[str] | None) -> str | None:
        """把选项列表序列化成入库用的 JSON 文本。"""

        if not options:
            return None
        return json.dumps(options, ensure_ascii=False)
