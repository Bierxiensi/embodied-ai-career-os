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
from app.models.job_match import GRADE_ORDER, JobMatch
from app.models.job_posting import JobPosting
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.skill import Skill
from app.models.task import Task
from app.schemas.task_scope import to_scoped_task_ref, to_task_scope_out
from app.services.action_planning.task_scope import (
    TaskTrackScope,
    resolve_task_scope,
    select_tasks,
)

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
            "frozen": role.frozen,
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
    # 口径（Milestone B）：由**当前 CareerMode** 决定哪些赛道进入默认视图。
    #
    # 规则与三分类（active / frozen / unclassified）全部在
    # ``services/action_planning/task_scope.py`` —— 赛道过滤的唯一权威实现；
    # 本路由只调用与序列化，不再自己拼 track_key 条件。
    #
    # 历史背景（勿删）：这里原本是 ``db.query(Task).order_by(Task.id).all()``
    # ——**全库裸查**。后果是 target_roles.py 中 frozen=True 的具身赛道任务
    # 被当成"仍在推动的待办"计入总数（2026-09-11 实测 23 条待办里混了 8 条具身），
    # 与"冻结赛道不占学习时间"的设计意图冲突。修法**不是**在路由里内联一段
    # ``track_key in frozen_keys``：/api/plan/today 也要遵守同一口径，写两遍
    # 就有两份真相（CODEBUDDY_IMPLEMENTATION_CONSTRAINTS / CODEX_MODULAR_DESIGN_STANDARD
    # §4.2 一条规则一个权威实现），所以判断整体收进上面那个服务模块。
    scoped = select_tasks(db.query(Task).order_by(Task.id), resolve_task_scope(db))

    task_out = [
        {
            "id": t.id,
            "title": t.title,
            "skill_name": t.skill_name,
            "status": t.status,
            "duration": t.duration,
            "objective": t.objective,
            "track_key": t.track_key,
            # 分类由服务给出（含"未归类"），前端只展示、不再自行判断赛道
            "scope": scoped.classification_of(t).value,
        }
        for t in scoped.included
    ]

    # 被口径排除的任务一并返回摘要，供用户**查看**（PRD §5 F5.3：
    # 隐藏不等于删除）。字段形状取自 schemas/task_scope.py 的 ScopedTaskRef ——
    # /api/plan/today 用的是同一个模型，两边不会各自漂移。
    frozen_items = [
        to_scoped_task_ref(t, TaskTrackScope.FROZEN) for t in scoped.frozen_items
    ]

    # ---- 投递漏斗 ----
    apps = db.query(JobApplication).order_by(JobApplication.id).all()
    counts = {"applied": 0, "screening": 0, "interview": 0, "offer": 0, "rejected": 0}
    for a in apps:
        counts[a.status] = counts.get(a.status, 0) + 1
    total_apps = len(apps)
    responded = counts["screening"] + counts["interview"] + counts["offer"]

    # ---- 岗位池摘要（Batch 1：推荐岗位直接进求职看板）----
    postings = db.query(JobPosting).all()
    pmatches = {m.posting_id: m for m in db.query(JobMatch).all()}
    grade_counts = {g: 0 for g in GRADE_ORDER}
    for p in postings:
        m = pmatches.get(p.id)
        if m:
            grade_counts[m.grade] = grade_counts.get(m.grade, 0) + 1
    # 推荐岗位（A/B）按匹配分降序，取前 5 供看板"今日可投"
    recommended = []
    for p in postings:
        m = pmatches.get(p.id)
        if m and m.grade in ("A", "B"):
            recommended.append({
                "id": p.id,
                "company": p.company,
                "title": p.title,
                "track": p.track,
                "tier": p.tier,
                "match_score": m.match_score,
                "grade": m.grade,
            })
    recommended.sort(key=lambda r: r["match_score"], reverse=True)
    job_pool = {
        "total": len(postings),
        "by_grade": grade_counts,
        "recommended": grade_counts.get("A", 0) + grade_counts.get("B", 0),
        "top": recommended[:5],
    }

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
        "job_pool": job_pool,
        "job_project": {
            "id": project.id if project else None,
            "name": project.name if project else None,
            "current_version": project.current_version if project else None,
            "milestones": milestones,
            "milestone_total": len(milestones),
            "milestone_completed": sum(1 for m in milestones if m["status"] == "completed"),
        },
        "tasks": {
            # 统计口径与 items 同源（Milestone B）：total/done/doing/todo 全部
            # 基于 task_out，即"当前模式默认视图里的任务"，不含被排除的冻结任务。
            "total": len(task_out),
            "done": sum(1 for t in task_out if t["status"] == "done"),
            "doing": sum(1 for t in task_out if t["status"] == "doing"),
            "todo": sum(1 for t in task_out if t["status"] == "todo"),
            # 被口径排除的冻结赛道任务数（透明化：让"为什么总数变小了"可解释）
            "frozen_excluded": scoped.frozen_excluded,
            # 未归类（track_key 为空）任务数：始终计入默认视图，此处仅提示
            "unclassified": scoped.unclassified,
            "items": task_out,
            # 支持查看：被排除任务的识别信息（PRD §5 F5.3 隐藏不等于删除）
            "frozen_items": frozen_items,
            # 口径自描述：前端据此解释"为什么总数变化"，不在 React 侧重算
            "scope": to_task_scope_out(scoped).model_dump(),
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
