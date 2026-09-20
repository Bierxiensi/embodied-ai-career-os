"""职业阶段模式模型（Career Mode / Mode Transition）。

产品依据：docs/PRD_CAREER_OS_MODES.md §4、§7.1（Milestone A 模式骨架）
工程依据：docs/CODEX_MODULAR_DESIGN_STANDARD.md §1（career_mode 模块只负责
「当前阶段、模式切换、赛道策略」，不负责 JD 解析与任务 CRUD）

两张表，各自职责单一：

- ``career_modes``      模式定义 + 当前生效标记。定义来自 presets.py（单一来源），
                        本表是它的物化副本，额外承载"哪一个是当前模式"这一状态。
- ``mode_transitions``  切换历史。**只追加，不修改、不删除** —— 供未来回溯
                        "什么时候因为什么原因换了阶段"。

================================================================================
为什么切换模式不会丢数据（PRD §7.1 / 约束 §2.1）
================================================================================
本模块**不持有**任何业务数据的引用：没有外键指向岗位、任务、投递、面试、
技能，切换模式只写 ``career_modes.is_current`` 与 ``mode_transitions`` 两处。
代价是失去数据库级的级联保护，收益是"切换阶段绝不可能级联影响既有历史"
由表结构本身保证，而不是靠调用方自觉。赛道过滤属于 Milestone B，届时也只
影响查询口径，不影响数据本身。
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CareerMode(Base):
    """一个职业阶段模式的定义 + 它是否为当前模式。

    ``key`` 是稳定业务标识（job_hunt / long_term_transition），前端与
    ``mode_transitions`` 都按它引用；``name``/``objective`` 是给人看的文案，
    允许改叫法而不破坏引用。
    """

    __tablename__ = "career_modes"

    # 不变量：至多一行 is_current 为真。
    #
    # 为什么放到数据库而不是只靠服务层自觉：读取当前模式时若有两行为真，
    # `.first()` 会静默挑一条，页面显示的模式与库里的真实状态不一致却毫无提示。
    # 加了唯一索引后这种状态根本无法落库，问题在写入那一刻就暴露。
    # 两个方言各写各的部分索引条件（SQLite 用 1，PostgreSQL 需要布尔字面量）。
    __table_args__ = (
        Index(
            "ux_career_modes_current",
            "is_current",
            unique=True,
            sqlite_where=text("is_current = 1"),
            postgresql_where=text("is_current = TRUE"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 模式标识：job_hunt / long_term_transition
    key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)

    # 展示名，如「求职冲刺模式」
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 该阶段的北极星目标（PRD §2），一句话说清"这段时间为了什么"
    objective: Mapped[str] = mapped_column(Text, nullable=False)

    # 目标期限；NULL 表示该阶段没有硬截止（长期转型按季度/里程碑推进）
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    # 该阶段推动的赛道 key（JSON 数组）。Milestone A 只存不执行。
    active_track_keys: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    # 该阶段冻结的赛道 key（JSON 数组）：只看不推，历史资产保留。
    frozen_track_keys: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    # 当前生效标记，全局至多一行为真（见 __table_args__）
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class ModeTransition(Base):
    """一次模式切换的历史记录（只追加）。

    ``from_mode`` 可为 NULL —— 首次激活（数据库初始化时把默认模式置为当前）
    没有来源模式，这是正常状态而非脏数据。
    """

    __tablename__ = "mode_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 来源模式 key；NULL = 系统首次激活默认模式
    from_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # 目标模式 key
    to_mode: Mapped[str] = mapped_column(String(40), nullable=False)

    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # 用户备注：为什么切换（PRD F1.4）。可空，但不能丢 —— 只是回溯的线索。
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
