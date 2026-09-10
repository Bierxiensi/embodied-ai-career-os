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


def _load_milestones_by_project(db: Session) -> dict[int, list[Milestone]]:
    """一次查询取出所有里程碑并按 project_id 分组。

    2026-09-10：list 接口此前只返回统计数（total/completed），**不返回 milestones 数组**。
    后果是 /projects 卡片拿不到当前进行中的里程碑，只能兜底显示"全部完成"
    —— 项目明明有 7 个未开始里程碑却写"全部完成"，是错误信息。
    改为在这里一次批量取回（12 行级别，代价可忽略），让 list 与 detail 同形。
    用一次 query + 内存分组，避免逐项目查的 N+1。
    """
    rows = (
        db.query(Milestone)
        .order_by(Milestone.project_id, Milestone.sort_order)
        .all()
    )
    by_project: dict[int, list[Milestone]] = {}
    for m in rows:
        by_project.setdefault(m.project_id, []).append(m)
    return by_project


@router.get("")
def list_projects(
    include_test: bool = False, db: Session = Depends(get_db)
) -> ApiResponse[list[dict]]:
    """获取全部项目，按 sort_order 排序，含 milestones 列表与进度统计。

    `include_test`：默认 False，即排除 `source="test"` 的测试残留。
    审计发现 dev 库里 214 个项目中真实只有 2 个（其余为 pytest 写入的
    "M Test Project" 等），不默认过滤会让 /projects 页彻底被淹没。
    """
    q = db.query(Project)
    if not include_test:
        q = q.filter(Project.source != "test")
    projects = q.order_by(Project.sort_order).all()
    by_project = _load_milestones_by_project(db)

    out: list[dict] = []
    for p in projects:
        ms = by_project.get(p.id, [])
        total = len(ms)
        completed = sum(1 for m in ms if m.status == "completed")
        out.append({
            **ProjectOut.model_validate(p).model_dump(),
            "milestones": [MilestoneOut.model_validate(m).model_dump() for m in ms],
            "milestone_total": total,
            "milestone_completed": completed,
            "progress_pct": round(completed / total * 100) if total > 0 else 0,
        })
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
