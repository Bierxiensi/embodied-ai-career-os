"""学习日志模型。

记录每次学习的产出，关联任务（可选）。
用于 Review Agent 分析学习结果、更新技能等级。

Day7 扩展：增加 artifact_url 字段，支持记录 GitHub/视频/代码等学习证明，
为 AI Engineer Portfolio 积累能力证据。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LearningLog(Base):
    """学习日志。一条记录代表一次学习产出。"""

    __tablename__ = "learning_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 可选关联任务（外键）
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )

    # 学习内容/产出（纯文本，含反思总结）
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 学习时长（分钟）
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Day7 新增：学习证明链接（GitHub repo / 视频 / 代码 / 博客）
    # Reviewer 据此加分，未来作为 Portfolio 能力证据
    artifact_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
