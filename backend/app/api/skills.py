"""Skill API 路由。

Day6 范围：GET 全部 + PATCH 单条（仅 level/evidence，禁止改架构）。
Phase 3 新增：GET /domains（六域聚合，R2 雷达数据源）+ GET /graph（依赖图）。

本文件只做三件事：接参 → 调 service → 返回统一 ``{ data }`` 包裹。
域归属与依赖边的真源在 core/skill_profile.py / core/skill_graph.py，
路由不复制任何判定（docs/CODEX_MODULAR_DESIGN_STANDARD.md §2）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.evidence import compute_skill_evidence
from app.core.response import ApiResponse, ok
from app.core.skill_profile import DOMAIN_LABELS, domain_of
from app.db.base import get_db
from app.models.skill import Skill
from app.schemas.skill import (
    SkillDomainOverview,
    SkillGraphOut,
    SkillOut,
    SkillPatch,
)
from app.services.skill_graph import service as skill_graph_service

router = APIRouter(prefix="/skills", tags=["skills"])


def _to_out(skill: Skill) -> SkillOut:
    """ORM 行 → SkillOut，并补上非数据库列的 ``domain`` / ``domain_label``。

    域归属的真源是 core/skill_profile.py，因此**不在** SkillOut 上挂 ORM 属性，
    而是在这里按技能名回查 —— 这样 skills 表不需要 domain 列
    （有列就有第二份可漂移的真相）。
    """

    out = SkillOut.model_validate(skill)
    key = domain_of(skill.name)
    out.domain = key
    out.domain_label = DOMAIN_LABELS.get(key) if key else None
    return out


@router.get("")
def list_skills(db: Session = Depends(get_db)) -> ApiResponse[list[SkillOut]]:
    """获取全部技能。按 id 排序保证前端展示稳定。"""

    skills = db.query(Skill).order_by(Skill.id).all()
    return ok([_to_out(s) for s in skills])


@router.get("/domains")
def list_skill_domains(
    db: Session = Depends(get_db),
) -> ApiResponse[SkillDomainOverview]:
    """六域聚合（Phase 3 / R2 域聚合雷达的数据源）。

    供 long_term_transition 模式下的技能雷达使用：轴 = 六个域，
    轴长 = 域内技能等级均值 / 目标均值。

    为什么聚合放后端而不是前端 groupBy：
        前端要按域分组就得先知道"哪项技能属于哪个域"，
        那等于把六域划分复制到 TypeScript —— 又是一份真相。
    """

    payload = skill_graph_service.build_domain_overview(db)
    return ok(SkillDomainOverview(**payload))


@router.get("/graph")
def get_skill_graph(db: Session = Depends(get_db)) -> ApiResponse[SkillGraphOut]:
    """技能依赖图（节点 + 先修边）。

    边的真源是 core/skill_graph.py，库里的 skill_dependency 表是它的投影
    （由 scripts/seed_skill_graph.py 同步）。本端点直接读真源，
    保证"图上有什么"永远等于"代码里声明了什么"，不受种子是否跑过影响。
    """

    payload = skill_graph_service.build_graph(db)
    return ok(SkillGraphOut(**payload))


@router.patch("/{skill_id}")
def patch_skill(
    skill_id: int, payload: SkillPatch, db: Session = Depends(get_db)
) -> ApiResponse[SkillOut]:
    """更新技能等级或能力证明。

    仅开放 level / evidence，避免误改 name/category/target_level（目标架构稳定）。
    未来 Reviewer Agent 通过此接口回写等级。
    """

    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)

    db.commit()
    db.refresh(skill)
    return ok(_to_out(skill), message="Skill updated")


@router.get("/evidence")
def list_evidence(db: Session = Depends(get_db)) -> ApiResponse[list[dict]]:
    """全部技能的 evidence-gated 证据链（P2 · 决策 3）。

    每条含 {id, name, level, target_level, evidence_gate, evidence}，
    evidence 的 ref 即「技能升级因为这份代码 / 这条实验」的文案来源。
    用于 /evidence 页一次性展示全部技能的可信等级推导。
    """

    skills = db.query(Skill).order_by(Skill.id).all()
    out: list[dict] = []
    for s in skills:
        ev = compute_skill_evidence(s.name, db)
        # 顺带把推导结果写回 evidence_gate，供看板直接读取（幂等）
        if s.evidence_gate != ev["gate_level"]:
            s.evidence_gate = ev["gate_level"]
        out.append(
            {
                "id": s.id,
                "name": s.name,
                "level": s.level,
                "target_level": s.target_level,
                "evidence_gate": ev["gate_level"],
                "evidence": ev["evidence"],
            }
        )
    db.commit()
    return ok(out)


@router.get("/{skill_id}/evidence")
def skill_evidence(skill_id: int, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """单个技能的 evidence-gated 证据链（P2）。

    推导后把 evidence_gate 写回 skills 表（幂等），便于看板消费。
    """

    skill = db.get(Skill, skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    ev = compute_skill_evidence(skill.name, db)
    if skill.evidence_gate != ev["gate_level"]:
        skill.evidence_gate = ev["gate_level"]
        db.commit()
    return ok(
        {
            "id": skill.id,
            "name": skill.name,
            "level": skill.level,
            "target_level": skill.target_level,
            "evidence_gate": ev["gate_level"],
            "evidence": ev["evidence"],
        }
    )
