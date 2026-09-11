"""Skill API 路由。

Day6 范围：GET 全部 + PATCH 单条（仅 level/evidence，禁止改架构）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.evidence import compute_skill_evidence
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.skill import Skill
from app.schemas.skill import SkillOut, SkillPatch

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
def list_skills(db: Session = Depends(get_db)) -> ApiResponse[list[SkillOut]]:
    """获取全部技能。按 id 排序保证前端展示稳定。"""

    skills = db.query(Skill).order_by(Skill.id).all()
    return ok([SkillOut.model_validate(s) for s in skills])


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
    return ok(SkillOut.model_validate(skill), message="Skill updated")


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
