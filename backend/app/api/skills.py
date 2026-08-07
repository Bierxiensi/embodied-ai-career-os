"""Skill API 路由。

Day6 范围：GET 全部 + PATCH 单条（仅 level/evidence，禁止改架构）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
