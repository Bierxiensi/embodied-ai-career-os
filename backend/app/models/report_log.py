"""报告存档模型（Batch 4）。

日报 / 周报每次生成后落库，作用有二：

1. ``/reports`` 页展示历史，不必每次重算；
2. **幂等**：同一 ``(kind, period_key)`` 已发送则跳过，
   避免调度器随 dev server 重启后重复推送同一天的日报。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 报告类型
KIND_DAILY = "daily"
KIND_WEEKLY = "weekly"


class ReportLog(Base):
    """一次生成的日报 / 周报存档。"""

    __tablename__ = "report_logs"
    __table_args__ = (
        UniqueConstraint("kind", "period_key", name="uq_report_log_period"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # daily | weekly
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # 期次标识：日报 2026-09-10 / 周报 2026-W37
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sections: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 是否已推送（生成成功但推送失败时保持 False，便于重试）
    sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
