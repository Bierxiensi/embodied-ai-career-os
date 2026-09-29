"""FastAPI 应用入口。

Phase 1 Day1：/health 健康检查 + CORS
Phase 1 Day2：启动建表 + /health/db 数据库连通检查
Phase 1 Day5：Planner Agent 路由
Phase 1 Day6：Career/Skill/Task CRUD + 统一 /api 前缀 + 种子数据
Phase 1 Day7：LearningLog + Reviewer Agent（Learning Loop 闭环）
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.agent import router as agent_router
from app.api.career import router as career_router
from app.api.career_mode import router as career_mode_router
from app.api.github import router as github_router
from app.api.interviews import router as interviews_router
from app.api.practice import router as practice_router
from app.api.job_applications import router as job_applications_router
from app.api.job_hunt import router as job_hunt_router
from app.api.job_postings import router as job_postings_router
from app.api.reports import router as reports_router
from app.api.resume import router as resume_router
from app.api.learning_logs import router as learning_logs_router
from app.api.mastery import router as mastery_router
from app.api.dashboard import router as dashboard_router
from app.api.milestones import router as milestones_router
from app.api.paper import router as paper_router
from app.api.phd import router as phd_router
from app.api.experiments import router as experiments_router
from app.api.plan import router as plan_router
from app.api.planner import router as planner_router
from app.api.projects import router as projects_router
from app.api.reviewer import router as reviewer_router
from app.api.risk import router as risk_router
from app.api.skills import router as skills_router
from app.api.tasks import router as tasks_router
from app.api.teach_back import router as teach_back_router
from app.api.today import router as today_router
from app.api.tools import router as tools_router
from app.api.transition import router as transition_router
from app.agents.registry_setup import setup_default_agents
from app.core.config import settings
from app.db.base import SessionLocal, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时建表 + 注册 Agent。

    Agent 注册放在 init_db 之后，确保 DB 就绪；
    幂等设计，dev server 热重载多次触发不会报错。
    """

    init_db()
    setup_default_agents()
    # ---- V2: 启动提醒调度器 ----
    from app.services.reminder.scheduler import (
        start_scheduler as start_reminder,
        stop_scheduler as stop_reminder,
    )
    start_reminder()
    # ---------------------------
    try:
        yield
    finally:
        # S6 修复：应用退出时显式关闭调度器，避免后台线程泄漏 / 资源未释放
        stop_reminder()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# 允许前端开发端口访问，属于连通性必需项，非业务功能
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册业务路由（统一 /api 前缀，便于前端代理）
api_prefix = "/api"
app.include_router(career_router, prefix=api_prefix)
app.include_router(career_mode_router, prefix=api_prefix)
app.include_router(skills_router, prefix=api_prefix)
app.include_router(tasks_router, prefix=api_prefix)
app.include_router(tools_router, prefix=api_prefix)
app.include_router(planner_router, prefix=api_prefix)
app.include_router(learning_logs_router, prefix=api_prefix)
app.include_router(reviewer_router, prefix=api_prefix)
app.include_router(agent_router, prefix=api_prefix)
app.include_router(github_router, prefix=api_prefix)
app.include_router(paper_router, prefix=api_prefix)
app.include_router(phd_router, prefix=api_prefix)
app.include_router(projects_router, prefix=api_prefix)
app.include_router(milestones_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(job_applications_router, prefix=api_prefix)
app.include_router(job_hunt_router, prefix=api_prefix)
app.include_router(job_postings_router, prefix=api_prefix)
app.include_router(resume_router, prefix=api_prefix)
app.include_router(interviews_router, prefix=api_prefix)
app.include_router(practice_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)
# 30 天施工执行台：课程脊梁 + 今日施工单 + 四件套（见 docs/platform-direction-30day.md）
app.include_router(experiments_router, prefix=api_prefix)
app.include_router(plan_router, prefix=api_prefix)
# 今日单聚合端点（spec §4.4）：施工单 + 今日日志 + 容量预检一次取齐
app.include_router(today_router, prefix=api_prefix)
# 掌握单元双环（spec §3.3/§4.5）：单元懒生成 + 答题实证 + SM-2 复习推进
app.include_router(mastery_router, prefix=api_prefix)
# Teach-Back 口述回收（spec §4.2）：判定 + 自动学习日志 + 错项入 SM-2
app.include_router(teach_back_router, prefix=api_prefix)
app.include_router(risk_router, prefix=api_prefix)
# Phase 3 统一落地页：职业进度 + 当前工作 + 学术与博士（/today 页的数据源之一）
app.include_router(transition_router, prefix=api_prefix)


@app.get("/health")
def health() -> dict:
    """健康检查端点。"""

    return {
        "status": "ok",
        "service": "backend",
        "version": settings.app_version,
    }


@app.get("/health/db")
def health_db() -> dict:
    """数据库连通性检查。执行简单查询验证连接。"""

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception as e:  # noqa: BLE001
        return {"db": "error", "detail": str(e)}
    finally:
        db.close()


@app.get("/")
def root() -> dict:
    """根路径，返回服务基本信息。"""

    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
