"""Reviewer Agent API 路由。

Day7 闭环核心入口：一次请求完成全链路。
  1. Task 状态 → done
  2. 写入 LearningLog
  3. 执行 Reviewer Agent（LangGraph 5 节点，只读提案）
  4. 契约裁决：verdict != "pass" → fail-closed 不落库（applied=False）
  5. pass → apply_review_proposal 落库（写库唯一通道，spec §4.3）+ 记录 agent_runs

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
from app.models.skill import Skill
from app.models.skill_assessment import SkillAssessment
from app.models.task import Task
from app.schemas.assessment import SkillAssessmentOut
from app.schemas.learning_log import LearningLogOut
from app.services.evidence_events import apply_review_proposal

router = APIRouter(prefix="/reviewer", tags=["reviewer"])

# 图编译一次复用（无状态，db 通过 state 注入）
_reviewer = build_reviewer_graph()


class ReviewerRequest(BaseModel):
    """Reviewer 请求体。前端"完成并复盘"表单提交。"""

    task_id: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=2000)
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    artifact_url: str | None = Field(default=None, max_length=500)


@router.post("/review", include_in_schema=False)
def review_task(
    req: ReviewerRequest, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """DEPRECATED（2026-09-24 收敛）：零前端消费，保数据不删路由。

    完成任务并复盘：Task→done + LearningLog + Reviewer Agent（只读提案）
    + 契约裁决 + apply_review_proposal 落库。

    事务分两段（spec §4.3 写库唯一通道）：
      - record_agent_run 节点提交 Task/LearningLog/AgentRun（事实与 tracing）；
      - SkillAssessment / skill 等级只经 apply_review_proposal 提交。
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

    # 4. 执行 Reviewer Agent（节点只读：产出契约 review，不写技能状态）
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

    # 6. 契约裁决 + 落库：非 pass 一律 fail-closed（含 review 缺失/verdict 非法）
    review = result.get("review")
    if not isinstance(review, dict):
        review = {"verdict": "block", "error": "contract:missing_review"}
    if review.get("verdict") != "pass":
        if review.get("verdict") != "block":
            review = {
                **review,
                "verdict": "block",
                "error": review.get("error") or "contract:verdict_invalid",
            }
        applied = False
        apply_out = None
        message = "Review blocked (fail-closed)"
    else:
        apply_out = apply_review_proposal(db, review)
        applied = bool(apply_out.get("applied"))
        message = "Task completed and reviewed" if applied else "Review not applied"

    # 7. 兼容旧响应字段（保数据不删路由）：assessment / updated_skill
    #    按 task_id 取本任务评估；apply 层写的行不带 task_id → 落库后按技能取最新
    assessment = (
        db.query(SkillAssessment)
        .filter(SkillAssessment.task_id == task.id)
        .order_by(SkillAssessment.created_at.desc())
        .first()
    )
    skill_row = None
    if applied and review.get("skill_name"):
        skill_row = db.query(Skill).filter(Skill.name == review["skill_name"]).first()
        if skill_row is not None and assessment is None:
            assessment = (
                db.query(SkillAssessment)
                .filter(SkillAssessment.skill_id == skill_row.id)
                .order_by(SkillAssessment.created_at.desc())
                .first()
            )

    assessment_out = (
        SkillAssessmentOut.model_validate(assessment)
        if assessment is not None
        else SkillAssessmentOut(
            skill_id=None,
            task_id=task.id,
            old_level=None,
            new_level=None,
            confidence=None,
            reason="无匹配技能或未生成评估",
            evidence_score=None,
        )
    )

    updated_skill = result.get("updated_skill", {})
    if applied and skill_row is not None:
        updated_skill = {
            "id": skill_row.id,
            "name": skill_row.name,
            "level": skill_row.level,
            "target_level": skill_row.target_level,
            "evidence": list(skill_row.evidence) if skill_row.evidence else [],
        }

    return ok(
        {
            "task": task_dict,
            "learning_log": LearningLogOut.model_validate(log),
            "assessment": assessment_out,
            "updated_skill": updated_skill,
            "review": review,
            "applied": applied,
            "apply": apply_out,
        },
        message=message,
    )
