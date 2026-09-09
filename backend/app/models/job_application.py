"""求职投递记录模型。

Career OS 从"学习记录系统"转向"求职作战看板"的核心数据：
跟踪每一家公司的投递状态，避免在海投中丢失跟进节奏。

状态机：
    applied → screening → interview → offer
                     ↘ rejected（任意阶段）
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 投递状态（顺序即漏斗顺序）
STATUS_APPLIED = "applied"        # 已投递
STATUS_SCREENING = "screening"    # 简历通过 / HR 沟通
STATUS_INTERVIEW = "interview"    # 技术面试中
STATUS_OFFER = "offer"            # 已拿 offer
STATUS_REJECTED = "rejected"      # 已挂

STATUS_ORDER = [
    STATUS_APPLIED,
    STATUS_SCREENING,
    STATUS_INTERVIEW,
    STATUS_OFFER,
    STATUS_REJECTED,
]


class JobApplication(Base):
    """一次求职投递。"""

    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    company: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    # 岗位类别：对应目标岗位画像（agent / embodied / robot-software / other）
    track: Mapped[str] = mapped_column(String(50), default="other", nullable=False)
    # 来源渠道：boss直聘 / 猎聘 / 内推 / 官网 / 其他
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_APPLIED, nullable=False)
    # 薪资范围（如 "36-42K"），便于谈薪时对照
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    applied_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 下一步动作（如 "9/12 前发感谢信"）
    next_action: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
