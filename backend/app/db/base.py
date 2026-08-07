"""数据库基础设施。

提供：
- engine：SQLAlchemy 引擎（按 DATABASE_URL 创建，默认 SQLite）
- SessionLocal：会话工厂
- Base：所有模型的声明基类
- get_db：FastAPI 依赖，注入数据库会话
- init_db：启动时建表 + 首次启动插入种子数据
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _build_engine():
    """构建引擎。SQLite 需开启外键约束（默认关闭）。"""

    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # SQLite 多线程支持 + 外键约束
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False,
    )

    # SQLite 显式开启外键约束（PRAGMA 仅 SQLite 有效，对 PostgreSQL 无影响）
    if settings.database_url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _enable_fk(dbapi_conn, _):  # noqa: ANN001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类。"""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：注入数据库会话，请求结束自动关闭。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """启动时建表 + 首次启动插入种子数据。

    开发态用 create_all；生产环境或需要迁移历史时改用 Alembic。
    种子数据源自 docs/MY_CONTEXT.md 真实自评，确保前端不空。
    """

    # SQLite 文件型数据库需保证 data 目录存在
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite:///./", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    # 导入模型，确保 Base.metadata 感知所有表
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # 首次启动插入种子数据（表为空时）
    _seed_if_empty()


def _seed_if_empty() -> None:
    """表为空时插入种子数据。基于 docs/MY_CONTEXT.md 真实自评。"""

    from app.models.career import Career
    from app.models.skill import Skill
    from app.models.task import Task

    db = SessionLocal()
    try:
        # Career 种子
        if db.query(Career).count() == 0:
            db.add(
                Career(
                    target_role="Robot AI Engineer",
                    salary_target=30000,
                    timeframe="2027",
                    notes="从 AI Application Engineer 转型具身智能",
                )
            )

        # Skill 种子：10 项，源自 MY_CONTEXT 真实自评
        if db.query(Skill).count() == 0:
            seed_skills = [
                Skill(name="Frontend", category="Strong", level=5, target_level=5,
                      evidence=["6.5 年前端开发经验", "Vue / React / Cesium / WebGIS 项目"]),
                Skill(name="Web Engineering", category="Strong", level=5, target_level=5,
                      evidence=["工程化体系搭建", "性能优化与部署"]),
                Skill(name="Agent Application", category="Strong", level=4, target_level=5,
                      evidence=["Embodied AI Career OS 项目"]),
                Skill(name="Python", category="Strong", level=4, target_level=5,
                      evidence=["FastAPI 后端开发", "SO101 ACT 训练脚本"]),
                Skill(name="PyTorch", category="Medium", level=3, target_level=4,
                      evidence=["ACT 模型训练完成"]),
                Skill(name="Deep Learning", category="Medium", level=3, target_level=4,
                      evidence=["理解 Transformer / 扩散模型原理"]),
                Skill(name="ROS2", category="Weak", level=1, target_level=4, evidence=[]),
                Skill(name="Isaac", category="Weak", level=0, target_level=4, evidence=[]),
                Skill(name="Robot Learning", category="Weak", level=1, target_level=4,
                      evidence=["SO101 ACT 推理可用，泛化待提升"]),
                Skill(name="VLA", category="Weak", level=0, target_level=4, evidence=[]),
            ]
            for s in seed_skills:
                db.add(s)

        # Task 种子：3 项，源自 Day3 mock/tasks.ts
        if db.query(Task).count() == 0:
            seed_tasks = [
                Task(
                    title="ROS2 Topic 通信机制",
                    objective="掌握 publisher/subscriber 通信，写出可运行 demo",
                    duration=40, difficulty="beginner", status="doing",
                    skill_name="ROS2",
                    acceptance=["创建 publisher 节点发布字符串",
                                "创建 subscriber 节点接收消息",
                                "Git 提交可运行的 demo"],
                ),
                Task(
                    title="SO101 ACT 模型泛化调试",
                    objective="采集新数据重训 ACT，对比泛化成功率",
                    duration=30, difficulty="intermediate", status="todo",
                    skill_name="Robot Learning",
                    acceptance=["采集 20+ episodes 新数据",
                                "训练新模型并对比成功率",
                                "记录泛化效果到 LearningLog"],
                ),
                Task(
                    title="Career OS Day2 数据库层",
                    objective="完成 4 张表模型定义与健康检查端点",
                    duration=25, difficulty="beginner", status="done",
                    skill_name="Python",
                    acceptance=["完成 4 张表模型定义",
                                "/health/db 返回 ok",
                                "表结构验证通过"],
                ),
            ]
            for t in seed_tasks:
                db.add(t)

        db.commit()
    finally:
        db.close()
