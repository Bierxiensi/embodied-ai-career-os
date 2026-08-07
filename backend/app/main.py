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
from app.api.learning_logs import router as learning_logs_router
from app.api.paper import router as paper_router
from app.api.planner import router as planner_router
from app.api.reviewer import router as reviewer_router
from app.api.skills import router as skills_router
from app.api.tasks import router as tasks_router
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
    yield


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
app.include_router(skills_router, prefix=api_prefix)
app.include_router(tasks_router, prefix=api_prefix)
app.include_router(planner_router, prefix=api_prefix)
app.include_router(learning_logs_router, prefix=api_prefix)
app.include_router(reviewer_router, prefix=api_prefix)
app.include_router(agent_router, prefix=api_prefix)
app.include_router(paper_router, prefix=api_prefix)


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
