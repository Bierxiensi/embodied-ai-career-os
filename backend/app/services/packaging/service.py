"""求职包装的取数层（P4）。

``engine.py`` 只负责「长什么样」，本模块负责「从哪取数」：
读项目 / 里程碑 / 任务技能 / 实验，调 ``core/evidence.py`` 推导每个技能的证据等级，
再交给纯函数生成 README 骨架与简历技能行。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.evidence import compute_skill_evidence
from app.models.experiment import Experiment
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.skill import Skill
from app.models.task import Task
from app.services.packaging.engine import build_readme_skeleton, build_skill_lines


def project_skill_names(project_id: int, db: Session) -> list[str]:
    """项目涉及技能 = 该项目里程碑下所有任务的 ``skill_name`` 去重（排序稳定）。"""

    rows = (
        db.query(Task.skill_name)
        .join(Milestone, Task.milestone_id == Milestone.id)
        .filter(Milestone.project_id == project_id, Task.skill_name.isnot(None))
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


def evidence_map(skill_names: list[str], db: Session) -> dict[str, dict]:
    """批量推导技能证据。返回 ``{技能名: {gate_level, evidence}}``。"""

    return {name: compute_skill_evidence(name, db) for name in skill_names}


def _milestone_dicts(project_id: int, db: Session) -> list[dict]:
    rows = (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.sort_order)
        .all()
    )
    return [
        {
            "version": m.version,
            "title": m.title,
            "goal": m.goal,
            "status": m.status,
        }
        for m in rows
    ]


def _experiment_dicts(skill_names: list[str], db: Session) -> list[dict]:
    """项目相关实验 = ``skill_name`` 命中项目技能集的实验（无技能集则返回空）。"""

    if not skill_names:
        return []
    rows = (
        db.query(Experiment)
        .filter(Experiment.skill_name.in_(skill_names))
        .order_by(Experiment.day_seq)
        .all()
    )
    return [
        {
            "name": e.name,
            "kind": e.kind,
            "variant_count": len(e.variants or []),
            "conclusion": e.conclusion,
        }
        for e in rows
    ]


def collect_readme_context(project: Project, db: Session) -> dict:
    """聚合生成 README 所需的全部输入。"""

    skills = project_skill_names(project.id, db)
    return {
        "name": project.name,
        "goal": project.goal,
        "description": project.description,
        "github_url": project.github_url,
        "status": project.status,
        "current_version": project.current_version,
        "milestones": _milestone_dicts(project.id, db),
        "skills": skills,
        "evidence_by_skill": evidence_map(skills, db),
        "experiments": _experiment_dicts(skills, db),
    }


def build_project_readme(project_id: int, db: Session) -> dict | None:
    """读取项目并生成 README 骨架。

    Returns:
        ``{project_id, name, saved_readme, draft, counts}``；项目不存在返回 ``None``。
    """

    project = db.get(Project, project_id)
    if project is None:
        return None

    ctx = collect_readme_context(project, db)
    draft = build_readme_skeleton(**ctx)

    return {
        "project_id": project.id,
        "name": project.name,
        "saved_readme": project.readme,
        "draft": draft,
        "counts": {
            "milestones": len(ctx["milestones"]),
            "skills": len(ctx["skills"]),
            "skills_with_evidence": sum(
                1
                for v in ctx["evidence_by_skill"].values()
                if (v or {}).get("gate_level", 0) >= 1
            ),
            "experiments": len(ctx["experiments"]),
            "chars": len(draft),
        },
    }


def collect_skill_lines(db: Session, *, pending_min_level: int = 3) -> dict:
    """简历技能行：全量技能 + 逐技能证据推导。"""

    rows = db.query(Skill).order_by(Skill.level.desc(), Skill.name).all()
    skills = [
        {"name": s.name, "level": s.level, "category": s.category} for s in rows
    ]
    ev = evidence_map([s["name"] for s in skills], db)
    result = build_skill_lines(
        skills=skills, evidence_by_skill=ev, pending_min_level=pending_min_level
    )
    result["note"] = (
        "简历行只收录有真实证据（L1 起）的技能；pending 区的技能一旦写进简历即构成"
        "虚构风险，请先在对应课程日产出笔记 / 代码 / 实验。"
    )
    return result
