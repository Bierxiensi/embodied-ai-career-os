"""数据库基础设施。

提供：
- engine：SQLAlchemy 引擎（按 DATABASE_URL 创建，SQLite/PostgreSQL 兼容）
- SessionLocal：会话工厂
- Base：所有模型的声明基类
- get_db：FastAPI 依赖，注入数据库会话
- init_db：启动时建表 + 首次启动插入种子数据
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _is_sqlite(url: str) -> bool:
    """判断是否为 SQLite 连接。"""
    return url.startswith("sqlite")


def _build_engine() -> Engine:
    """构建引擎。

    SQLite：开启外键约束 + check_same_thread=False（多线程）。
    PostgreSQL：标准连接，无额外参数。
    """
    connect_args: dict = {}

    if _is_sqlite(settings.database_url):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False,
    )

    # SQLite 显式开启外键约束
    if _is_sqlite(settings.database_url):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_fk(dbapi_conn, _):  # noqa: ANN001
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
    if _is_sqlite(settings.database_url):
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
    from app.models.milestone import Milestone
    from app.models.project import Project
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

        # Task 种子：3 项
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

        # V2 Project 种子
        if db.query(Project).count() == 0:
            p = Project(
                name="SO101 Embodied AI System",
                goal="打造 ROS2 + VLA 驱动的具身智能真机闭环系统",
                description="从 Python 控制 → ROS2 → MoveIt2 → ACT → SmolVLA → Isaac Lab → Sim2Real",
                status="active",
                current_version="V1",
                sort_order=0,
            )
            db.add(p)
            db.flush()

            seed_milestones = [
                Milestone(project_id=p.id, version="V0", title="Python 基础控制",
                          goal="Python 直接控制 SO101 舵机转动", status="completed", sort_order=0),
                Milestone(project_id=p.id, version="V1", title="ROS2 基础控制",
                          goal="通过 ROS2 topic 控制 SO101 关节", status="in_progress", sort_order=1),
                Milestone(project_id=p.id, version="V2", title="MoveIt2 集成",
                          goal="MoveIt2 运动规划 + 执行", status="locked", sort_order=2),
                Milestone(project_id=p.id, version="V3", title="ACT 模仿学习",
                          goal="ACT 训练 + 泛化实验", status="locked", sort_order=3),
                Milestone(project_id=p.id, version="V4", title="SmolVLA 接入",
                          goal="SmolVLA 推理 + 真机测试", status="locked", sort_order=4),
                Milestone(project_id=p.id, version="V5", title="Isaac Lab 仿真",
                          goal="仿真环境搭建 + 合成数据生成", status="locked", sort_order=5),
                Milestone(project_id=p.id, version="V6", title="Sim2Real 闭环",
                          goal="仿真训练 → 真机部署 → 评估完整闭环", status="locked", sort_order=6),
            ]
            for m in seed_milestones:
                db.add(m)

        db.commit()
    finally:
        db.close()
