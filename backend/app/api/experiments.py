"""实验记录 API 路由（30 天执行台 · 证据闭环 P2）。

对应 docs/platform-direction-30day.md 决策 4（实验是一等公民）与 P2 验收：
「填一次 LoRA vs QLoRA 实验，页面直接渲染出对比表」。

端点：
    GET    /api/experiments              列表（?skill_name= / ?day_seq= 过滤）
    POST   /api/experiments              新增
    GET    /api/experiments/{id}         详情
    PATCH  /api/experiments/{id}         更新（结论 / 指标）
    DELETE /api/experiments/{id}         删除

设计：纯规则 CRUD，不烧 LLM；variants / metrics 原样存 JSON，前端渲染对比表。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.experiment import Experiment
from app.schemas.experiment import ExperimentCreate, ExperimentOut, ExperimentPatch

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("")
def list_experiments(
    skill_name: str | None = None,
    day_seq: int | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse[list[ExperimentOut]]:
    """实验列表（按 day_seq 升序）。可按技能 / 课程日过滤。"""

    q = db.query(Experiment)
    if skill_name:
        q = q.filter(Experiment.skill_name == skill_name)
    if day_seq is not None:
        q = q.filter(Experiment.day_seq == day_seq)
    rows = q.order_by(Experiment.day_seq.asc(), Experiment.id.asc()).all()
    return ok([ExperimentOut.model_validate(r) for r in rows])


@router.post("")
def create_experiment(
    payload: ExperimentCreate, db: Session = Depends(get_db)
) -> ApiResponse[ExperimentOut]:
    """新增一条实验记录。"""

    exp = Experiment(
        plan_day_id=payload.plan_day_id,
        day_seq=payload.day_seq,
        name=payload.name,
        kind=payload.kind,
        skill_name=payload.skill_name,
        variants=payload.variants,
        metrics=payload.metrics,
        conclusion=payload.conclusion,
        artifact_ids=payload.artifact_ids,
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return ok(ExperimentOut.model_validate(exp), message=f"已记录实验 {payload.name}")


@router.get("/{exp_id}")
def get_experiment(exp_id: int, db: Session = Depends(get_db)) -> ApiResponse[ExperimentOut]:
    """实验详情。"""

    exp = db.get(Experiment, exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ok(ExperimentOut.model_validate(exp))


@router.patch("/{exp_id}")
def patch_experiment(
    exp_id: int, payload: ExperimentPatch, db: Session = Depends(get_db)
) -> ApiResponse[ExperimentOut]:
    """更新实验（结论 / 指标 / 变体等）。仅开放已声明字段。"""

    exp = db.get(Experiment, exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exp, field, value)
    db.commit()
    db.refresh(exp)
    return ok(ExperimentOut.model_validate(exp), message="实验已更新")


@router.delete("/{exp_id}")
def delete_experiment(exp_id: int, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """删除一条实验记录。"""

    exp = db.get(Experiment, exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(exp)
    db.commit()
    return ok({"id": exp_id}, message="已删除实验")
