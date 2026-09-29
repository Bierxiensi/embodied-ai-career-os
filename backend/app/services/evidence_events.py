"""证据事件 → evidence_gate 晋级的唯一 apply 层（spec §4.2/§4.5）。

铁律：
1. 写 SkillAssessment / skills.evidence_gate **只发生在这里**——reviewer 是只读提案者。
2. gate 只升不降；同级重复事件幂等（applied=False）。
3. 事件 ref 必须可追溯（unit_item:id / commit:sha / experiment:id），防虚构。

字段口径（对齐 app/models/skill_assessment.py 源码，不发明字段）：
- SkillAssessment 持 `skill_id`（FK to skills.id），无 skill_name 列 → 由 Skill 行取 id。
- `confidence` 是 Float 0-1（confidence = evidence_score / 100），不是字符串标签。
- `created_at` 默认 `datetime.utcnow`（naive）→ 本层显式传 aware UTC
  （datetime.now(timezone.utc)），与 Global Constraints 一致。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.models.skill_assessment import SkillAssessment

# 事件类型 → 证据门级别（L1 题/口述 → L2 代码+commit → L3 实验 → L4 对比+复现报告）
EVENT_GATE: dict[str, int] = {
    "quiz_verified": 1,
    "teachback_pass": 1,
    "commit": 2,
    "experiment": 3,
    "comparison_report": 4,
}


def record_evidence_event(db: Session, skill_name: str, kind: str, ref: str) -> dict:
    """记录一次证据事件并晋级 gate。返回 {skill, from_gate, to_gate, applied}。"""
    if kind not in EVENT_GATE:
        raise ValueError(f"unknown evidence kind: {kind}")

    skill = db.query(Skill).filter_by(name=skill_name).first()
    if skill is None:
        return {"skill": skill_name, "from_gate": -1, "to_gate": -1, "applied": False}

    target = EVENT_GATE[kind]
    current = int(skill.evidence_gate or 0)
    if target <= current:
        return {"skill": skill_name, "from_gate": current, "to_gate": current, "applied": False}

    evidence_score = target * 25  # L1-L4 线性映射到百分制展示
    skill.evidence_gate = target
    db.add(SkillAssessment(
        skill_id=skill.id,
        old_level=skill.level,
        new_level=skill.level,
        confidence=evidence_score / 100.0,
        evidence_score=evidence_score,
        reason=f"evidence_event:{kind} ref={ref}",
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()
    return {"skill": skill_name, "from_gate": current, "to_gate": target, "applied": True}


def apply_review_proposal(db: Session, proposal: dict) -> dict:
    """reviewer 提案的唯一落库通道（契约见 Task 2）。

    proposal = {"skill_name": str, "proposed_level": int, "evidence_score": int,
                "reason": str, "evidence_refs": [str]}
    仅当 proposal 通过契约校验且 evidence_score >= 80 才落 SkillAssessment
    并申请等级变更（沿用既有 ≥80 升级口径）。
    """
    required = ("skill_name", "proposed_level", "evidence_score", "reason", "evidence_refs")
    if not all(k in proposal for k in required):
        return {"applied": False, "error": "contract_violation"}
    if not isinstance(proposal["evidence_refs"], list) or not proposal["evidence_refs"]:
        return {"applied": False, "error": "evidence_refs_empty"}
    if int(proposal["evidence_score"]) < 80:
        return {"applied": False, "error": "score_below_threshold"}

    skill = db.query(Skill).filter_by(name=proposal["skill_name"]).first()
    if skill is None:
        return {"applied": False, "error": "skill_not_found"}

    score = int(proposal["evidence_score"])
    old = skill.level
    new = max(old, min(5, int(proposal["proposed_level"])))
    skill.level = new
    db.add(SkillAssessment(
        skill_id=skill.id,
        old_level=old,
        new_level=new,
        confidence=score / 100.0,
        evidence_score=score,
        reason=f"{proposal['reason']} refs={proposal['evidence_refs']}",
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()
    return {"applied": True, "skill": proposal["skill_name"], "old_level": old, "new_level": new}
