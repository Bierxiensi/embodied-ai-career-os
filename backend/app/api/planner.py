"""Planner Agent API 路由（Day6 迁移至 /api/planner 前缀）。

Day6 改动：
- 路由从 /planner 迁移到 /api/planner（统一前缀，便于前端代理）
- 生成任务后写入 tasks 表（Day6 闭环：Planner → DB → Dashboard）
- 写入 agent_runs 表记录 Agent 决策（可追溯）
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.planner.graph import build_planner_graph
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.agent_run import AgentRun
from app.models.task import Task

router = APIRouter(prefix="/planner", tags=["planner"])

# 图编译一次复用（无状态）
_planner = build_planner_graph()


class SkillIn(BaseModel):
    """技能输入项。"""

    name: str
    level: int = Field(ge=0, le=5)
    target: int = Field(ge=0, le=5)


class PlannerRequest(BaseModel):
    """Planner 请求体。"""

    available_minutes: int = Field(default=45, ge=5, le=480)
    target_role: str = Field(default="Robot AI Engineer")
    skills: list[SkillIn]
    energy_level: str = Field(default="normal")
    current_focus: str | None = Field(default=None)
    generator: str = Field(default="rule")
    # Day6 新增：是否将生成的任务持久化到 tasks 表
    persist: bool = Field(default=True)


class GeneratedTaskOut(BaseModel):
    """Planner 生成任务响应。"""

    title: str
    skill: str
    objective: str | None = None
    duration: int
    difficulty: str | None = None
    acceptance: list[str] = []
    resources: list[str] = []
    status: str = "todo"
    task_id: int | None = None  # 持久化后的任务 ID（persist=False 时为 None）


@router.post("/generate")
def generate_task(
    req: PlannerRequest, db: Session = Depends(get_db)
) -> ApiResponse[GeneratedTaskOut]:
    """调用 Planner Agent 生成每日核心学习任务。

    Day6 闭环：
      1. 执行 LangGraph 生成任务
      2. 写入 agent_runs 表（决策可追溯）
      3. 按 persist 选项写入 tasks 表
    """

    # 1. 组装状态并执行状态图
    state = {
        "available_minutes": req.available_minutes,
        "target_role": req.target_role,
        "skills": [s.model_dump() for s in req.skills],
        "energy_level": req.energy_level,
        "current_focus": req.current_focus,
        "generator": req.generator,
    }
    result = _planner.invoke(state)
    task_data = result.get("task") or {}

    # 2. 记录 Agent 执行（输入 + 输出 + tracing），便于 Debug / 面试展示
    run_id = str(uuid.uuid4())
    db.add(
        AgentRun(
            id=run_id,
            agent_name="planner",
            input_context=json.dumps(state, ensure_ascii=False),
            output_result=json.dumps(task_data, ensure_ascii=False),
            status="success",
            duration_ms=0,  # 直调 API 不计时，由 Orchestrator/Executor 统一追踪
            trace_id=run_id,
        )
    )

    # 3. 持久化任务到 tasks 表
    task_id = None
    if req.persist and task_data:
        new_task = Task(
            title=task_data.get("title", ""),
            objective=task_data.get("objective"),
            duration=task_data.get("duration"),
            difficulty=task_data.get("difficulty"),
            status=task_data.get("status", "todo"),
            skill_name=task_data.get("skill"),
            acceptance=task_data.get("acceptance", []),
            resources=task_data.get("resources", []),
        )
        db.add(new_task)
        db.flush()  # 取自增 ID
        task_id = new_task.id

    db.commit()

    return ok(
        GeneratedTaskOut(
            title=task_data.get("title", ""),
            skill=task_data.get("skill", ""),
            objective=task_data.get("objective"),
            duration=task_data.get("duration", 0),
            difficulty=task_data.get("difficulty"),
            acceptance=task_data.get("acceptance", []),
            resources=task_data.get("resources", []),
            status=task_data.get("status", "todo"),
            task_id=task_id,
        ),
        message=f"Planner generated task for {result.get('selected_skill')}",
    )
