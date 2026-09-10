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

    # 数据来源（user / seed / planner / test），语义见 app/models/project.py 顶部注释。
    # Planner 生成的任务标 "planner"；种子标 "seed"；测试标 "test"。
    source: Mapped[str] = mapped_column(
        String(20), default="user", server_default="user", nullable=False
    )

    # 任务所属赛道（llm / vlm / ai-algo / embodied），见 migrations/0008。
    # 与 source 正交：source 记「谁写的」，track_key 记「给哪条赛道写的」。
    # 看板切到某个视角时，只展示 track_key == 当前赛道 的任务；
    # NULL = 未归类（历史 / 手写任务），不参与视角过滤。
    track_key: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # 任务归属「课程第几天」（1..30），见 migrations/0011 与 app/models/plan_day.py。
    # 与 track_key 正交：plan_day_id 记「属于课程第几天」，track_key 记「属于哪条赛道」。
    # 今日施工单据此列出"今天该做的任务"；NULL = 不对应任何课程日（历史 / 手写任务）。
    plan_day_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("plan_days.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
