"""Milestone API 路由。CRUD + 从 milestone 生成关联任务。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.task import Task
from app.schemas.project import MilestoneCreate, MilestoneOut, MilestonePatch

router = APIRouter(tags=["milestones"])


# ---- Milestone CRUD ----

@router.post("/projects/{project_id}/milestones")
def create_milestone(
    project_id: int,
    payload: MilestoneCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[MilestoneOut]:
    """在项目下创建里程碑。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    m = Milestone(
        project_id=project_id,
        version=payload.version,
        title=payload.title,
        goal=payload.goal,
        status=payload.status,
        sort_order=payload.sort_order,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return ok(MilestoneOut.model_validate(m), message="Milestone created")


@router.patch("/milestones/{milestone_id}")
def patch_milestone(
    milestone_id: int,
    payload: MilestonePatch,
    db: Session = Depends(get_db),
) -> ApiResponse[MilestoneOut]:
    """更新里程碑。标记 completed 时自动解锁下一个 locked 里程碑。"""
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    old_status = m.status
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)

    # 自动传播：completed → 解锁下一个 locked 里程碑
    if (
        payload.status == "completed"
        and old_status != "completed"
        and old_status != "completed"
    ):
        next_m = (
            db.query(Milestone)
            .filter(
                Milestone.project_id == m.project_id,
                Milestone.sort_order > m.sort_order,
                Milestone.status == "locked",
            )
            .order_by(Milestone.sort_order)
            .first()
        )
        if next_m:
            next_m.status = "in_progress"
            project = db.get(Project, m.project_id)
            if project:
                project.current_version = next_m.version

    db.commit()
    db.refresh(m)
    return ok(MilestoneOut.model_validate(m), message="Milestone updated")


@router.delete("/milestones/{milestone_id}")
def delete_milestone(
    milestone_id: int, db: Session = Depends(get_db)
) -> ApiResponse[None]:
    """删除里程碑。"""
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    db.delete(m)
    db.commit()
    return ok(message="Milestone deleted")


# ---- 从里程碑生成任务 ----

class SkillIn(BaseModel):
    name: str
    level: int = Field(ge=0, le=5)
    target: int = Field(ge=0, le=5)


class GenerateTasksRequest(BaseModel):
    available_minutes: int = Field(default=120, ge=5, le=480)
    skills: list[SkillIn]
    generator: str = "rule"


@router.post("/milestones/{milestone_id}/tasks")
def generate_tasks_from_milestone(
    milestone_id: int,
    req: GenerateTasksRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[list[dict]]:
    """从里程碑拆解生成子任务。

    按里程碑 goal 拆 2-5 个子任务，每个任务自动关联 project_id + milestone_id。
    """
    m = db.get(Milestone, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Milestone not found")

    milestone_tasks = _decompose_milestone(m.goal, req.available_minutes)

    created = []
    for task_input in milestone_tasks:
        t = Task(
            title=task_input["title"],
            objective=task_input.get("objective"),
            duration=task_input.get("duration"),
            difficulty=task_input.get("difficulty", "beginner"),
            status="todo",
            skill_name=task_input.get("skill"),
            acceptance=task_input.get("acceptance", []),
            resources=task_input.get("resources", []),
            project_id=m.project_id,
            milestone_id=milestone_id,
        )
        db.add(t)
        db.flush()
        created.append({
            "id": t.id,
            "title": t.title,
            "objective": t.objective,
            "duration": t.duration,
            "difficulty": t.difficulty,
            "status": t.status,
            "skill_name": t.skill_name,
            "project_id": t.project_id,
            "milestone_id": t.milestone_id,
        })

    db.commit()
    return ok(created, message=f"Generated {len(created)} tasks from milestone")


def _decompose_milestone(goal: str, available_minutes: int) -> list[dict]:
    """将里程碑 goal 拆解为 2-5 个子任务。基于关键词规则拆解。"""
    goal_lower = goal.lower()

    if "topic" in goal_lower or "ros2" in goal_lower:
        return [
            {"title": f"{goal} - Publisher 节点", "objective": "创建 publisher 发布数据",
             "duration": min(40, available_minutes // 3), "difficulty": "beginner",
             "skill": "ROS2"},
            {"title": f"{goal} - Subscriber 节点", "objective": "创建 subscriber 接收数据",
             "duration": min(40, available_minutes // 3), "difficulty": "beginner",
             "skill": "ROS2"},
            {"title": f"{goal} - Launch 文件", "objective": "创建 launch 文件启动多节点",
             "duration": min(30, available_minutes // 4), "difficulty": "beginner",
             "skill": "ROS2"},
        ]
    elif "moveit" in goal_lower:
        return [
            {"title": f"{goal} - URDF 建模", "objective": "创建 SO101 URDF 模型",
             "duration": min(45, available_minutes // 3), "difficulty": "intermediate",
             "skill": "ROS2"},
            {"title": f"{goal} - MoveIt 配置", "objective": "配置 MoveIt2 运动规划",
             "duration": min(45, available_minutes // 3), "difficulty": "intermediate",
             "skill": "ROS2"},
            {"title": f"{goal} - 真机执行", "objective": "MoveIt 规划 → SO101 执行",
             "duration": min(30, available_minutes // 4), "difficulty": "intermediate",
             "skill": "ROS2"},
        ]
    else:
        per_task = max(20, available_minutes // 3)
        return [
            {"title": f"{goal} - 第1步", "objective": goal,
             "duration": per_task, "difficulty": "beginner"},
            {"title": f"{goal} - 第2步", "objective": goal,
             "duration": per_task, "difficulty": "beginner"},
        ]
