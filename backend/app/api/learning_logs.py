"""LearningLog API 路由。

Day7 范围：GET 列表 + POST 创建。
学习日志是 Reviewer Agent 的输入，也是 AI Engineer Portfolio 的证据来源。
不做 DELETE（历史日志是 Reviewer 决策依据，同 Task）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.learning_log import LearningLog
from app.models.task import Task
from app.schemas.learning_log import LearningLogCreate, LearningLogOut

router = APIRouter(prefix="/learning-logs", tags=["learning-logs"])


@router.get("")
def list_logs(
    task_id: int | None = None, db: Session = Depends(get_db)
) -> ApiResponse[list[LearningLogOut]]:
    """获取学习日志列表。支持按 task_id 过滤，按创建时间倒序。"""

    query = db.query(LearningLog)
    if task_id is not None:
        query = query.filter(LearningLog.task_id == task_id)
    logs = query.order_by(LearningLog.created_at.desc()).all()
    return ok([LearningLogOut.model_validate(log) for log in logs])


@router.post("")
def create_log(
    payload: LearningLogCreate, db: Session = Depends(get_db)
) -> ApiResponse[LearningLogOut]:
    """创建学习日志。

    若 task_id 提供但任务不存在，返回 404。
    """

    if payload.task_id is not None:
        task = db.get(Task, payload.task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

    log = LearningLog(
        task_id=payload.task_id,
        content=payload.content,
        duration_minutes=payload.duration_minutes,
        artifact_url=payload.artifact_url,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return ok(LearningLogOut.model_validate(log), message="Learning log created")
