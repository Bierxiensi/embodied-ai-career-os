"""Project API 路由。CRUD + 详情含 milestones 进度。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.milestone import Milestone
from app.models.project import Project
from app.schemas.project import (
    MilestoneOut,
    ProjectCreate,
    ProjectOut,
    ProjectPatch,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(db: Session = Depends(get_db)) -> ApiResponse[list[ProjectOut]]:
    """获取全部项目，按 sort_order 排序。"""
    projects = db.query(Project).order_by(Project.sort_order).all()
    return ok([ProjectOut.model_validate(p) for p in projects])


@router.post("")
def create_project(
    payload: ProjectCreate, db: Session = Depends(get_db)
) -> ApiResponse[ProjectOut]:
    """创建项目。"""
    p = Project(
        name=payload.name,
        goal=payload.goal,
        description=payload.description,
        status=payload.status,
        current_version=payload.current_version,
        github_url=payload.github_url,
        sort_order=payload.sort_order,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ok(ProjectOut.model_validate(p), message="Project created")


@router.get("/{project_id}")
def get_project(
    project_id: int, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """获取项目详情，含 milestones 列表和完成率。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    milestones = (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.sort_order)
        .all()
    )

    total = len(milestones)
    completed = sum(1 for m in milestones if m.status == "completed")
    progress_pct = round(completed / total * 100) if total > 0 else 0

    return ok({
        **ProjectOut.model_validate(p).model_dump(),
        "milestones": [MilestoneOut.model_validate(m).model_dump() for m in milestones],
        "milestone_total": total,
        "milestone_completed": completed,
        "progress_pct": progress_pct,
    })


@router.patch("/{project_id}")
def patch_project(
    project_id: int, payload: ProjectPatch, db: Session = Depends(get_db)
) -> ApiResponse[ProjectOut]:
    """更新项目字段。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(p, field, value)

    db.commit()
    db.refresh(p)
    return ok(ProjectOut.model_validate(p), message="Project updated")


@router.delete("/{project_id}")
def delete_project(
    project_id: int, db: Session = Depends(get_db)
) -> ApiResponse[None]:
    """删除项目（级联删除 milestones）。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(p)
    db.commit()
    return ok(message="Project deleted")
