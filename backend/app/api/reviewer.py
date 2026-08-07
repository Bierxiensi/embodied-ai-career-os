"""Reviewer Agent API 路由。

Day7 闭环核心入口：一次请求完成全链路。
  1. Task 状态 → done
  2. 写入 LearningLog
  3. 执行 Reviewer Agent（LangGraph 5 节点）
  4. 产出 SkillAssessment + 更新 Skill + 记录 agent_runs

前端只需一个 POST，避免多步调用与状态不一致。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.reviewer.graph import build_reviewer_graph
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.learning_log import LearningLog
from app.models.task import Task
from app.schemas.assessment import SkillAssessmentOut
from app.schemas.learning_log import LearningLogOut

router = APIRouter(prefix="/reviewer", tags=["reviewer"])

# 图编译一次复用（无状态，db 通过 state 注入）
_reviewer = build_reviewer_graph()


class ReviewerRequest(BaseModel):
    """Reviewer 请求体。前端"完成并复盘"表单提交。"""

    task_id: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=2000)
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    artifact_url: str | None = Field(default=None, max_length=500)


class ReviewerResult(BaseModel):
    """Reviewer 评估结果。"""

    task: dict                  # 完成的任务
    learning_log: LearningLogOut  # 创建的学习日志
    assessment: SkillAssessmentOut  # 技能评估记录
    updated_skill: dict         # 更新后的技能状态


@router.post("/review")
def review_task(
    req: ReviewerRequest, db: Session = Depends(get_db)
) -> ApiResponse[ReviewerResult]:
    """完成任务并复盘：Task→done + LearningLog + Reviewer Agent + Skill Update。

    事务保证：全链路成功才提交，任一步骤失败回滚。
    """

    # 1. 查任务，校验存在性
    task = db.get(Task, req.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # 2. Task 状态 → done
    task.status = "done"

    # 3. 写入 LearningLog
    log = LearningLog(
        task_id=req.task_id,
        content=req.content,
        duration_minutes=req.duration_minutes,
        artifact_url=req.artifact_url,
    )
    db.add(log)
    db.flush()  # 取自增 ID，供 Reviewer 读取

    # 4. 执行 Reviewer Agent（db 通过 state 注入，节点内完成 DB 写入）
    #    task / learning_log 序列化为 dict 传入
    task_dict = {
        "id": task.id,
        "title": task.title,
        "skill_name": task.skill_name,
        "status": task.status,
        "acceptance": task.acceptance or [],
    }
    log_dict = {
        "id": log.id,
        "content": log.content,
        "artifact_url": log.artifact_url,
    }

    state = {
        "task": task_dict,
        "learning_log": log_dict,
        "db": db,
    }
    result = _reviewer.invoke(state)

    # 5. record_agent_run 节点已 commit，此处刷新关联对象
    db.refresh(log)

    # 6. 取 SkillAssessment（最新一条，由 apply_skill_update 节点写入）
    from app.models.skill_assessment import SkillAssessment

    assessment = (
        db.query(SkillAssessment)
        .order_by(SkillAssessment.created_at.desc())
        .first()
    )

    return ok(
        ReviewerResult(
            task=task_dict,
            learning_log=LearningLogOut.model_validate(log),
            assessment=SkillAssessmentOut.model_validate(assessment),
            updated_skill=result.get("updated_skill", {}),
        ),
        message="Task completed and reviewed",
    )
