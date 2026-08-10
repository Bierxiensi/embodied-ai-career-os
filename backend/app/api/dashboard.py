"""Dashboard 聚合端点。返回项目进度等顶层数据。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.milestone import Milestone
from app.models.project import Project
from app.schemas.project import MilestoneOut, ProjectOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """聚合 Dashboard 所需数据：项目进度汇集。"""
    projects = db.query(Project).order_by(Project.sort_order).all()
    projects_data = []
    for p in projects:
        milestones = (
            db.query(Milestone)
            .filter(Milestone.project_id == p.id)
            .order_by(Milestone.sort_order)
            .all()
        )
        total = len(milestones)
        completed = sum(1 for m in milestones if m.status == "completed")
        progress_pct = round(completed / total * 100) if total > 0 else 0

        projects_data.append({
            **ProjectOut.model_validate(p).model_dump(),
            "milestones": [MilestoneOut.model_validate(m).model_dump() for m in milestones],
            "milestone_total": total,
            "milestone_completed": completed,
            "progress_pct": progress_pct,
        })

    return ok({
        "projects": projects_data,
    })
