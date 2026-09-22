"""技能依赖图模型（Phase 3）。

一条记录 = 一条先修边：``prerequisite -> dependent``，
语义是「必须先掌握 prerequisite，dependent 才学得动」。

为什么单独一张表（而不是塞进 skills 的 JSON 列）：
    skills 表的一行只描述"这项技能我现在几级"，它无法表达**技能之间的关系**。
    把边塞进 JSON 列会让"反向查询某技能的先修"变成全表扫描 + Python 侧过滤，
    而且没有唯一约束可依赖（同一对边会被种子脚本重复插入）。

为什么端点用技能名而不是 skills.id：
    与项目既有约定一致 —— target_roles.required_skills / tasks.skill_name /
    interview_questions.skill_name 全部按**规范名**引用技能。
    改 id 外键会让"技能改名"变成一次数据迁移，按名字引用则只需同步 skill_profile。
    代价是名字拼错不会被数据库拦住，所以由 tests/test_skill_graph.py
    断言每条边的两端都必须存在于 skills 表 / SKILL_PROFILE。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SkillDependency(Base):
    """技能先修边。"""

    __tablename__ = "skill_dependency"
    # 索引名必须与 migrations/0027_skill_dependency.sql 逐字一致，
    # 否则测试库（create_all 建）与开发库（迁移建）会各长一套索引。
    __table_args__ = (
        UniqueConstraint("prerequisite", "dependent", name="ux_skill_dependency_edge"),
        Index("idx_skill_dependency_dependent", "dependent"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 先修技能名（规范名，对应 skills.name）
    prerequisite: Mapped[str] = mapped_column(String(100), nullable=False)

    # 后继技能名（学得动 prerequisite 之后才推它）
    dependent: Mapped[str] = mapped_column(String(100), nullable=False)

    # 可选说明：为什么要先学它（写给自己看的一句话，不参与任何计算）
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
