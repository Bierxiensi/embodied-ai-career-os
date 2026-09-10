"""课程脊梁模型（PlanDay）。

对应《30-Day LLM → VLM 求职施工计划 v2.0》的 Day 1..30。
内容来源是 app/core/plan_30d.py，本表只是它的数据库投影（由幂等种子脚本写入）。

设计要点（见 docs/platform-direction-30day.md §四 决策 1）：
    seq 是**不可变的课程序号**，绝不与日历日期绑定。
    "今天是第几天"由 DayProgress（P1）与日历共同推导，
    落后时只提示、不自动顺延 —— 否则滑一天后面全错位。

为什么不用 create_all 自动建表就够、还要写迁移：
    新表确实能被 Base.metadata.create_all 建出来，但项目约定
    （见 migrations/0002、0004）是所有 schema 变更都留迁移记录，
    否则 `run_migration.py --status` 会与实际库不一致，PG 部署也会漏建。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanDay(Base):
    """课程中的一天（Day 1..30）。"""

    __tablename__ = "plan_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 课程序号 1..30，唯一且不可变。全站"今天是 Day N"的唯一标识。
    seq: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # 阶段（周）1..4，用于总览页分带
    phase: Mapped[int] = mapped_column(Integer, nullable=False)
    phase_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 当天主题（一句话）
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # 技术域（Transformer / Training / PEFT / Inference / Vision / VLM / 实验 / 包装 / 面试 / 求职 / 验收）
    theme: Mapped[str] = mapped_column(String(50), nullable=False)

    # 学习目标（JSON 数组）
    objectives: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 验收标准（JSON 数组）—— "做到什么算过"
    acceptance: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 当天必须能回答的面试题主题（JSON 数组），题目本身由用户录入题库
    interview_topics: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 指定资源（JSON 数组），严格来自计划的 5 类资源，用于防"课程收藏"式发散
    resources: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 预计投入分钟数
    est_minutes: Mapped[int] = mapped_column(Integer, default=360, nullable=False)

    # 归属赛道：llm / vlm（复用 tasks.track_key 口径）
    track_key: Mapped[str] = mapped_column(String(40), nullable=False, default="llm")

    # 可选的补充说明（计划原文摘录 / 个人备注）
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
