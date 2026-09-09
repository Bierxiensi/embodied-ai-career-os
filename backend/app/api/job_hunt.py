"""求职看板聚合 API。

一次请求返回 /jobs 页面所需的全部数据，避免前端 N+1 拉取：
    - 目标岗位画像 + 匹配度 + 缺口
    - offer 倒计时
    - 技能 gap 排序
    - 求职项目里程碑
    - 本周任务
    - 投递漏斗
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.core.target_roles import (
    DEFAULT_OFFER_DEADLINE,
    JOB_HUNT_PROJECT_NAME,
    TARGET_ROLES,
)
from app.db.base import get_db
from app.models.career import Career
from app.models.job_application import JobApplication
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.skill import Skill
from app.models.task import Task

router = APIRouter(prefix="/job-hunt", tags=["job-hunt"])


def _parse_deadline(timeframe: str | None) -> date:
    """从 Career.timeframe 解析 offer 目标日期，失败回退默认值。"""
    if timeframe:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y"):
            try:
                d = datetime.strptime(timeframe, fmt).date()
                # 仅年月/年时对齐到该期间最后一天
                if fmt == "%Y-%m":
                    next_month = date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
                    return next_month.replace(day=1) - date.resolution
                if fmt == "%Y":
                    return date(d.year, 12, 31)
                return d
            except ValueError:
                continue
    return datetime.strptime(DEFAULT_OFFER_DEADLINE, "%Y-%m-%d").date()


@router.get("")
def job_hunt_board(db: Session = Depends(get_db)):
    """求职看板聚合数据。"""
    # ---- 职业目标 ----
    career = db.query(Career).first()
    deadline = _parse_deadline(career.timeframe if career else None)
    days_left = (deadline - date.today()).days

    # ---- 技能 ----
    skills = db.query(Skill).order_by(Skill.level).all()
    skill_map = {s.name.lower(): s for s in skills}

    # ---- 目标岗位匹配度 ----
    roles_out = []
    for role in TARGET_ROLES:
        matches = []
        for name in role.required_skills:
            s = skill_map.get(name.lower())
            level = s.level if s else 0
            matches.append({
                "name": name,
                "level": level,
                "required": role.required_level,
                "gap": max(role.required_level - level, 0),
                "missing": s is None,
            })
        need = sum(m["required"] for m in matches)
        have = sum(min(m["level"], m["required"]) for m in matches)
        roles_out.append({
            "key": role.key,
            "name": role.name,
            "priority": role.priority,
            "salary_range": role.salary_range,
            "note": role.note,
            "match_pct": round(have / need * 100) if need else 0,
            "skills": matches,
        })

    # ---- 技能缺口（按差值降序）----
    gaps = [
        {
            "name": s.name,
            "category": s.category,
            "level": s.level,
            "target_level": s.target_level,
            "gap": max(s.target_level - s.level, 0),
            "evidence": s.evidence or [],
        }
        for s in skills
    ]
    gaps.sort(key=lambda g: (-g["gap"], g["name"]))

    # ---- 求职项目里程碑 ----
    project = db.query(Project).filter(Project.name == JOB_HUNT_PROJECT_NAME).first()
    milestones = []
    if project:
        rows = (
            db.query(Milestone)
            .filter(Milestone.project_id == project.id)
            .order_by(Milestone.sort_order)
            .all()
        )
        milestones = [
            {
                "id": m.id,
                "version": m.version,
                "title": m.title,
                "goal": m.goal,
                "status": m.status,
                "sort_order": m.sort_order,
            }
            for m in rows
        ]

    # ---- 任务 ----
    tasks = db.query(Task).order_by(Task.id).all()
    task_out = [
        {
            "id": t.id,
            "title": t.title,
            "skill_name": t.skill_name,
            "status": t.status,
            "duration": t.duration,
            "objective": t.objective,
        }
        for t in tasks
    ]

    # ---- 投递漏斗 ----
    apps = db.query(JobApplication).order_by(JobApplication.id).all()
    counts = {"applied": 0, "screening": 0, "interview": 0, "offer": 0, "rejected": 0}
    for a in apps:
        counts[a.status] = counts.get(a.status, 0) + 1
    total_apps = len(apps)
    responded = counts["screening"] + counts["interview"] + counts["offer"]

    return ok({
        "career": {
            "target_role": career.target_role if career else None,
            "salary_target": career.salary_target if career else None,
            "timeframe": career.timeframe if career else None,
            "notes": career.notes if career else None,
        },
        "offer_deadline": deadline.isoformat(),
        "days_left": days_left,
        "target_roles": roles_out,
        "skill_gaps": gaps,
        "job_project": {
            "id": project.id if project else None,
            "name": project.name if project else None,
            "current_version": project.current_version if project else None,
            "milestones": milestones,
            "milestone_total": len(milestones),
            "milestone_completed": sum(1 for m in milestones if m["status"] == "completed"),
        },
        "tasks": {
            "total": len(task_out),
            "done": sum(1 for t in task_out if t["status"] == "done"),
            "doing": sum(1 for t in task_out if t["status"] == "doing"),
            "todo": sum(1 for t in task_out if t["status"] == "todo"),
            "items": task_out,
        },
        "applications": {
            "total": total_apps,
            "by_status": counts,
            "response_rate": round(responded / total_apps * 100) if total_apps else 0,
            "items": [
                {
                    "id": a.id,
                    "company": a.company,
                    "role": a.role,
                    "track": a.track,
                    "source": a.source,
                    "status": a.status,
                    "salary_range": a.salary_range,
                    "applied_at": a.applied_at.isoformat() if a.applied_at else None,
                    "next_action": a.next_action,
                    "notes": a.notes,
                }
                for a in apps
            ],
        },
    })
