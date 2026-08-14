"""Project API 路由。CRUD + 详情含 milestones 进度。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
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


def _build_milestone_stats(db: Session) -> dict[int, tuple[int, int]]:
    """一次 group_by 查询所有项目的里程碑统计。

    返回 {project_id: (total, completed)}。
    前端 #1 + API #9 修复：避免前端逐项目拉 milestones（N+1），
    list 接口直接附带进度统计。
    """
    rows = db.query(
        Milestone.project_id,
        func.count(Milestone.id).label("total"),
        func.sum(case((Milestone.status == "completed", 1), else_=0)).label("completed"),
    ).group_by(Milestone.project_id).all()
    return {r.project_id: (int(r.total or 0), int(r.completed or 0)) for r in rows}


@router.get("")
def list_projects(db: Session = Depends(get_db)) -> ApiResponse[list[ProjectOut]]:
    """获取全部项目，按 sort_order 排序，含里程碑进度统计。"""
    projects = db.query(Project).order_by(Project.sort_order).all()
    stats = _build_milestone_stats(db)

    out: list[ProjectOut] = []
    for p in projects:
        total, completed = stats.get(p.id, (0, 0))
        progress_pct = round(completed / total * 100) if total > 0 else 0
        out.append(ProjectOut(
            id=p.id,
            name=p.name,
            goal=p.goal,
            description=p.description,
            status=p.status,
            current_version=p.current_version,
            github_url=p.github_url,
            readme=p.readme,
            sort_order=p.sort_order,
            milestone_total=total,
            milestone_completed=completed,
            progress_pct=progress_pct,
        ))
    return ok(out)


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
    """更新项目字段。标记 completed 时自动生成 README。"""
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(p, field, value)

    # 项目标记完成时自动生成 README
    if payload.status == "completed":
        from app.models.milestone import Milestone
        from app.models.task import Task

        milestones = (
            db.query(Milestone)
            .filter(Milestone.project_id == project_id)
            .order_by(Milestone.sort_order)
            .all()
        )

        # 收集关联技能
        skills_set: set[str] = set()
        for m in milestones:
            tasks = db.query(Task).filter(Task.milestone_id == m.id).all()
            for t in tasks:
                if t.skill_name:
                    skills_set.add(t.skill_name)

        # 构建 README
        lines = [
            f"# {p.name}",
            "",
            f"> {p.goal}",
            "",
            "## 里程碑",
            "",
        ]
        for m in milestones:
            status_icon = "✅" if m.status == "completed" else "⬜"
            lines.append(
                f"- {status_icon} **{m.version}**: {m.title} — {m.goal}"
            )

        lines.extend([
            "",
            "## 涉及技能",
            "",
        ])
        for skill in sorted(skills_set):
            lines.append(f"- {skill}")

        lines.extend([
            "",
            "---",
            "*由 Embodied AI Career OS 自动生成*",
        ])

        p.readme = "\n".join(lines)

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
