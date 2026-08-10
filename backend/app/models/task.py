"""任务模型。

对应 PRD AI Planner：每天生成的学习任务。
状态机：todo → doing → done（与前端 TaskStatus 对齐）。
skill_name 冗余存储技能名（避免 join），skill_id 可选外键关联。

Day6 扩展字段：objective/duration/difficulty/acceptance/resources，
对齐 Planner Agent 的 TaskOutput Schema，支持 Day7 Reviewer Agent 评估。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Task(Base):
    """学习任务。"""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 任务标题
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # 学习目标（一句话描述达成什么）
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 预计时长（分钟）
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 难度：beginner / intermediate / advanced
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 任务状态：todo / doing / done（对齐前端三态）
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False)

    # 关联技能名（冗余字段，便于无 join 查询）
    skill_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 可选关联技能（外键），任务完成后可更新该技能等级
    skill_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )

    # V2 Project 模块：可选关联项目和里程碑
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    milestone_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True
    )

    # 验收标准清单（JSON 数组）
    acceptance: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 推荐资源（JSON 数组）
    resources: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 任务描述（保留向后兼容，新逻辑用 objective）
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
