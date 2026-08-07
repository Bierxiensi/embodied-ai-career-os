"""Agent 执行记录模型。

记录每次 Agent（如 Planner）的输入上下文与输出结果，
用于：
- Agent Debug：为什么推荐这个任务？
- Prompt 优化：对比不同输入的输出差异
- 面试展示：展示 Agent 决策可追溯性
- Observability：Day 6 起含 status / duration_ms / trace_id 独立字段，
  支持 SQL 查询与 Dashboard 展示

字段演进：
- Phase 1 Day6：id / agent_name / input_context / output_result / created_at
- Phase 2 Day6：新增 status / duration_ms / trace_id（独立字段，便于查询）
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentRun(Base):
    """Agent 执行记录。"""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # 用 UUID 字符串主键，避免自增暴露量级

    # Agent 名称：planner / reviewer / career / research / supervisor
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # 输入上下文（JSON 字符串）：技能缺口/时间/能量等
    input_context: Mapped[str] = mapped_column(Text, nullable=False)

    # 输出结果（JSON 字符串）：生成的任务等
    output_result: Mapped[str] = mapped_column(Text, nullable=False)

    # ===== Phase 2 Day6 新增：Observability 字段 =====
    # 执行状态：success / failed（默认 success，兼容旧数据）
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success", server_default="success"
    )
    # 执行耗时（毫秒），旧数据为 0
    duration_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # 追踪 ID（UUID 字符串），关联一次完整调用链
    # 旧数据无 trace_id，允许为 NULL
    trace_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
