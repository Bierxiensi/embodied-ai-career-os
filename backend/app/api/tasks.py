"""Task API 路由。

Day6 范围：GET 列表 + POST 创建 + PATCH 状态。
不做 DELETE（历史任务服务 Day7 Reviewer Agent，是宝贵数据）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.skill import Skill
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskOut, TaskStatusPatch

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    project_id: int | None = None,
    track_key: str | None = None,
    include_untracked: bool = False,
    include_test: bool = False,
    db: Session = Depends(get_db),
) -> ApiResponse[list[TaskOut]]:
    """获取任务列表。支持按项目 / 赛道过滤。按创建时间倒序。

    `track_key`：按赛道过滤（llm / vlm / ai-algo / embodied），
    用于让任务列表跟随看板视角 —— 切到「具身智能」视角时只看具身任务。

    `include_untracked`：`track_key` 过滤时是否一并返回未归类（track_key IS NULL）
    的历史 / 手写任务。默认 False（视角过滤应干净）；
    需要"全部"语义时前端不传 track_key 即可。

    `include_test`：默认 False，即排除 `source="test"` 的测试残留
    （审计发现 dev 库里大量 pytest 写入的重复任务，会淹没真实数据）。
    """
    q = db.query(Task)
    if project_id is not None:
        q = q.filter(Task.project_id == project_id)
    if track_key is not None:
        if include_untracked:
            q = q.filter((Task.track_key == track_key) | (Task.track_key.is_(None)))
        else:
            q = q.filter(Task.track_key == track_key)
    if not include_test:
        q = q.filter(Task.source != "test")
    tasks = q.order_by(Task.created_at.desc()).all()
    return ok([TaskOut.model_validate(t) for t in tasks])


@router.post("")
def create_task(
    payload: TaskCreate, db: Session = Depends(get_db)
) -> ApiResponse[TaskOut]:
    """创建任务。

    若 skill_name 提供且能在 skills 表匹配，自动回填 skill_id 外键。
    """

    task = Task(
        title=payload.title,
        objective=payload.objective,
        duration=payload.duration,
        difficulty=payload.difficulty,
        status=payload.status,
        skill_name=payload.skill_name,
        acceptance=payload.acceptance,
        resources=payload.resources,
        project_id=payload.project_id,
        milestone_id=payload.milestone_id,
        source=payload.source or "user",
        track_key=payload.track_key,
    )

    # 自动关联技能外键
    if payload.skill_name:
        skill = db.query(Skill).filter(Skill.name == payload.skill_name).first()
        if skill:
            task.skill_id = skill.id

    db.add(task)
    db.commit()
    db.refresh(task)
    return ok(TaskOut.model_validate(task), message="Task created")


@router.patch("/{task_id}/status")
def patch_task_status(
    task_id: int, payload: TaskStatusPatch, db: Session = Depends(get_db)
) -> ApiResponse[TaskOut]:
    """更新任务状态。仅允许 todo/doing/done 三态转换。"""

    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = payload.status
    db.commit()
    db.refresh(task)
    return ok(TaskOut.model_validate(task), message=f"Task status → {payload.status}")
