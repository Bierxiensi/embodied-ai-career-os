"""Task API 路由。

Day6 范围：GET 列表 + POST 创建 + PATCH 状态。
不做 DELETE（历史任务服务 Day7 Reviewer Agent，是宝贵数据）。

任务范围（哪个轴的过滤）在这里是**显式参数**，不是隐含行为：
``scope=all`` 是原始全量（CRUD / 审计用，默认，保持既有契约），
``scope=current_mode`` 是平台默认视图口径（由当前 CareerMode 决定，与
``/api/job-hunt``、``/api/plan/today`` 共用同一个服务）。
这两者必须能分开：把默认改成"按阶段过滤"会让项目详情页等既有调用方
静默丢数据（见 docs/CODEX_MODULAR_DESIGN_STANDARD.md §4.5）。
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.skill import Skill
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskOut, TaskStatusPatch
from app.services.action_planning.task_scope import resolve_task_scope, select_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(
    project_id: int | None = None,
    track_key: str | None = None,
    plan_day_id: int | None = None,
    include_untracked: bool = False,
    include_test: bool = False,
    scope: Literal["all", "current_mode"] = "all",
    db: Session = Depends(get_db),
) -> ApiResponse[list[TaskOut]]:
    """获取任务列表。支持按项目 / 赛道 / 课程日过滤。按创建时间倒序。

    `track_key`：按赛道过滤（llm / vlm / ai-algo / embodied）。
    这是**显式**的赛道查询（例如"查看某赛道的全部任务"），
    与"平台默认视图口径"是两件事 —— 后者走 `scope=current_mode`。

    `plan_day_id`：按课程日过滤（见 migrations/0011）。
    与 `track_key` 正交：track_key 说「属于哪条赛道」，plan_day_id 说「属于课程第几天」。

    `include_untracked`：`track_key` 过滤时是否一并返回未归类（track_key IS NULL）
    的历史 / 手写任务。默认 False（视角过滤应干净）；
    需要"全部"语义时前端不传 track_key 即可。

    `include_test`：默认 False，即排除 `source="test"` 的测试残留
    （审计发现 dev 库里大量 pytest 写入的重复任务，会淹没真实数据）。

    `scope`（Milestone B 收尾新增，可选，默认 `all` = 既有行为不变）：

    - `all`：原始全量。不施加任何阶段口径 —— 冻结赛道的任务也在里面。
      这是 CRUD / 审计口径，**不是**平台默认统计口径。
    - `current_mode`：平台**默认视图口径**，由当前 CareerMode 决定
      （求职冲刺模式排除冻结赛道；长期转型模式暂不限制赛道）。
      判定与 /api/job-hunt、/api/plan/today 共用
      ``services/action_planning/task_scope.py``，因此三个视图的数字天然一致，
      且只随 **CareerMode** 变化。

    **不提供**任何"视角 / 角色"维度的过滤：Dashboard 的展示视角（ViewRole）
    是纯前端概念，不得改变任务请求范围、统计或推荐
    （docs/PRD_CAREER_OS_MODES.md §5 F5；Milestone B 契约）。
    """

    q = db.query(Task)
    if project_id is not None:
        q = q.filter(Task.project_id == project_id)
    if plan_day_id is not None:
        q = q.filter(Task.plan_day_id == plan_day_id)
    if track_key is not None:
        if include_untracked:
            q = q.filter((Task.track_key == track_key) | (Task.track_key.is_(None)))
        else:
            q = q.filter(Task.track_key == track_key)
    if not include_test:
        q = q.filter(Task.source != "test")
    q = q.order_by(Task.created_at.desc())

    if scope == "current_mode":
        # 唯一权威实现：本路由只调用，不自己拼 track_key 条件。
        # select_tasks 吃"已过滤好的候选集"，因此上面的项目 / 赛道 / 课程日
        # 轴与这里的阶段轴是正交的，各自留在自己的模块里。
        scoped = select_tasks(q, resolve_task_scope(db))
        return ok([TaskOut.model_validate(t) for t in scoped.included])

    return ok([TaskOut.model_validate(t) for t in q.all()])



@router.post("", include_in_schema=False)
def create_task(
    payload: TaskCreate, db: Session = Depends(get_db)
) -> ApiResponse[TaskOut]:
    """DEPRECATED（2026-09-24 收敛）：零前端消费，保数据不删路由。

    创建任务。

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
        plan_day_id=payload.plan_day_id,
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
