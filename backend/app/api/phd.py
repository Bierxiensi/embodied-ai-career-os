"""DEPRECATED（2026-09-24 收敛）：归档线登记式写端点收口（spec D2/D5），保数据不删路由。

博士模块 API 路由（Phase 1）。

端点：
  GET   /api/phd/directions             研究方向列表
  POST  /api/phd/directions            新增方向
  GET   /api/phd/targets               机会列表（track_key / direction_key 过滤）
  POST  /api/phd/targets               新增机会
  GET   /api/phd/targets/{id}          机会详情
  PATCH /api/phd/targets/{id}          更新机会
  DELETE /api/phd/targets/{id}         删除机会
  GET   /api/phd/advisors              导师列表（含所属机会字段 + match_json）
  POST  /api/phd/advisors              新增导师
  GET   /api/phd/advisors/{id}         导师详情
  PATCH /api/phd/advisors/{id}         更新导师
  DELETE /api/phd/advisors/{id}        删除导师
  POST  /api/phd/advisors/{id}/match   计算并缓存六维匹配
  POST  /api/phd/advisors/match-all    重算全部导师匹配
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.phd.agent import PhDMatchEngine, _is_home_school
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.phd import PhDAdvisor, PhDTarget, ResearchDirection
from app.schemas.phd import (
    PhDAdvisorCreate,
    PhDAdvisorOut,
    PhDAdvisorPatch,
    PhDTargetCreate,
    PhDTargetOut,
    PhDTargetPatch,
    ResearchDirectionCreate,
    ResearchDirectionOut,
)

router = APIRouter(prefix="/phd", tags=["phd"])


# ============================================================
# ResearchDirection
# ============================================================

@router.get("/directions")
def list_directions(
    db: Session = Depends(get_db),
) -> ApiResponse[list[ResearchDirectionOut]]:
    """研究方向列表（六维匹配方向维度的基准分来源）。"""

    rows = db.query(ResearchDirection).order_by(ResearchDirection.id).all()
    return ok([ResearchDirectionOut.model_validate(r) for r in rows])


@router.post("/directions", include_in_schema=False)
def create_direction(
    payload: ResearchDirectionCreate, db: Session = Depends(get_db)
) -> ApiResponse[ResearchDirectionOut]:
    if (
        db.query(ResearchDirection)
        .filter(ResearchDirection.key == payload.key)
        .first()
    ):
        raise HTTPException(status_code=409, detail="direction key 已存在")
    row = ResearchDirection(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(ResearchDirectionOut.model_validate(row), message="direction created")


# ============================================================
# PhDTarget
# ============================================================

@router.get("/targets")
def list_targets(
    track_key: str | None = Query(default=None),
    direction_key: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ApiResponse[list[PhDTargetOut]]:
    q = db.query(PhDTarget)
    if track_key:
        q = q.filter(PhDTarget.track_key == track_key)
    if direction_key:
        q = q.filter(PhDTarget.direction_key == direction_key)
    rows = q.order_by(PhDTarget.id).all()
    return ok([PhDTargetOut.model_validate(r) for r in rows])


@router.post("/targets", include_in_schema=False)
def create_target(
    payload: PhDTargetCreate, db: Session = Depends(get_db)
) -> ApiResponse[PhDTargetOut]:
    row = PhDTarget(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(PhDTargetOut.model_validate(row), message="target created")


@router.get("/targets/{target_id}")
def get_target(
    target_id: int, db: Session = Depends(get_db)
) -> ApiResponse[PhDTargetOut]:
    row = db.get(PhDTarget, target_id)
    if row is None:
        raise HTTPException(status_code=404, detail="target not found")
    return ok(PhDTargetOut.model_validate(row))


@router.patch("/targets/{target_id}", include_in_schema=False)
def patch_target(
    target_id: int, payload: PhDTargetPatch, db: Session = Depends(get_db)
) -> ApiResponse[PhDTargetOut]:
    row = db.get(PhDTarget, target_id)
    if row is None:
        raise HTTPException(status_code=404, detail="target not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return ok(PhDTargetOut.model_validate(row), message="target updated")


@router.delete("/targets/{target_id}", include_in_schema=False)
def delete_target(
    target_id: int, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    row = db.get(PhDTarget, target_id)
    if row is None:
        raise HTTPException(status_code=404, detail="target not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": target_id})


# ============================================================
# PhDAdvisor
# ============================================================

def _enrich_advisor(row: PhDAdvisor, target: PhDTarget | None) -> PhDAdvisorOut:
    """把所属机会的展示字段反查到导师响应上，便于前端直接渲染。"""

    out = PhDAdvisorOut.model_validate(row)
    if target:
        out.institution = target.institution
        out.city = target.city
        out.tier = target.tier
        out.direction_key = target.direction_key
        out.track_key = target.track_key
        out.application_deadline = target.application_deadline
    return out


@router.get("/advisors")
def list_advisors(
    target_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ApiResponse[list[PhDAdvisorOut]]:
    q = db.query(PhDAdvisor)
    if target_id is not None:
        q = q.filter(PhDAdvisor.target_id == target_id)
    rows = q.order_by(PhDAdvisor.id).all()
    targets = {t.id: t for t in db.query(PhDTarget).all()}
    return ok([_enrich_advisor(r, targets.get(r.target_id)) for r in rows])


@router.post("/advisors", include_in_schema=False)
def create_advisor(
    payload: PhDAdvisorCreate, db: Session = Depends(get_db)
) -> ApiResponse[PhDAdvisorOut]:
    if payload.target_id is not None and db.get(PhDTarget, payload.target_id) is None:
        raise HTTPException(status_code=400, detail="target_id 不存在")
    row = PhDAdvisor(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    target = db.get(PhDTarget, row.target_id) if row.target_id else None
    return ok(_enrich_advisor(row, target), message="advisor created")


@router.get("/advisors/{advisor_id}")
def get_advisor(
    advisor_id: int, db: Session = Depends(get_db)
) -> ApiResponse[PhDAdvisorOut]:
    row = db.get(PhDAdvisor, advisor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="advisor not found")
    target = db.get(PhDTarget, row.target_id) if row.target_id else None
    return ok(_enrich_advisor(row, target))


@router.patch("/advisors/{advisor_id}", include_in_schema=False)
def patch_advisor(
    advisor_id: int, payload: PhDAdvisorPatch, db: Session = Depends(get_db)
) -> ApiResponse[PhDAdvisorOut]:
    row = db.get(PhDAdvisor, advisor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="advisor not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    target = db.get(PhDTarget, row.target_id) if row.target_id else None
    return ok(_enrich_advisor(row, target), message="advisor updated")


@router.delete("/advisors/{advisor_id}", include_in_schema=False)
def delete_advisor(
    advisor_id: int, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    row = db.get(PhDAdvisor, advisor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="advisor not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": advisor_id})


def _compute_and_store(row: PhDAdvisor, db: Session) -> dict:
    """计算并缓存某导师的六维匹配结果。"""

    target = db.get(PhDTarget, row.target_id) if row.target_id else None
    direction = (
        db.query(ResearchDirection)
        .filter(ResearchDirection.key == target.direction_key)
        .first()
        if target and target.direction_key
        else None
    )
    direction_interest = direction.interest_weight if direction else 70
    res = PhDMatchEngine.compute(
        direction_interest=direction_interest,
        tier=target.tier if target else None,
        city=target.city if target else None,
        min_publication=target.min_publication if target else None,
        target_in_service=target.in_service_friendly if target else False,
        advisor_in_service=row.in_service_friendly,
        application_deadline=target.application_deadline if target else None,
        is_home_school=_is_home_school(
            target.institution if target else "", row.name or ""
        ),
    )
    match_json = {
        "overall": res.overall,
        "grade": res.grade,
        "dimensions": res.dimensions,
        "gaps": res.gaps,
        "computed_at": datetime.utcnow().isoformat(),
    }
    row.match_json = match_json
    row.last_matched_at = datetime.utcnow()
    return match_json


@router.post("/advisors/{advisor_id}/match", include_in_schema=False)
def match_advisor(
    advisor_id: int, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """计算并缓存单个导师的六维匹配。"""

    row = db.get(PhDAdvisor, advisor_id)
    if row is None:
        raise HTTPException(status_code=404, detail="advisor not found")
    match_json = _compute_and_store(row, db)
    db.commit()
    return ok(match_json, message="match computed")


@router.post("/advisors/match-all", include_in_schema=False)
def match_all_advisors(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """重算全部导师的六维匹配（批量）。"""

    rows = db.query(PhDAdvisor).all()
    for r in rows:
        _compute_and_store(r, db)
    db.commit()
    return ok({"matched": len(rows)}, message="all advisors matched")
