"""职业目标模型。

对应 PRD Career Management：目标岗位、薪资目标、时间规划。
个人系统，单用户，故不带 user_id 外键。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Career(Base):
    """职业目标。单条记录代表当前职业规划。"""

    __tablename__ = "career_goal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 目标岗位，如 Robot AI Engineer
    target_role: Mapped[str] = mapped_column(String(100), nullable=False)

    # 薪资目标（RMB/月），存整数便于比较
    salary_target: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 时间规划，如 "6 months" / "2026-06"
    timeframe: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
