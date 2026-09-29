# backend/tests/test_evidence_events.py
"""证据晋级 apply 层：事件→gate 只升不降、幂等、写库唯一通道。"""

from app.db.base import SessionLocal
from app.services.evidence_events import EVENT_GATE, record_evidence_event


def _gate_of(db, name: str) -> int:
    from app.models.skill import Skill

    s = db.query(Skill).filter_by(name=name).first()
    # 种子技能 evidence_gate 为 NULL（尚未计算）→ 与 apply 层 `or 0` 同口径按 0 计，
    # 否则 fresh DB 上 max(None, 1) 直接 TypeError。
    return int(s.evidence_gate or 0) if s else -1


def test_event_gate_mapping_covers_four_levels():
    assert EVENT_GATE["quiz_verified"] == 1
    assert EVENT_GATE["commit"] == 2
    assert EVENT_GATE["experiment"] == 3
    assert EVENT_GATE["comparison_report"] == 4


def test_quiz_event_upgrades_gate_once():
    db = SessionLocal()
    try:
        skill = "DPO"
        before = _gate_of(db, skill)
        r1 = record_evidence_event(db, skill, "quiz_verified", "unit_item:1")
        assert r1["applied"] is True
        assert r1["to_gate"] >= 1
        mid = _gate_of(db, skill)
        assert mid >= max(before, 1)
        # 同级事件幂等：不重复升级
        r2 = record_evidence_event(db, skill, "quiz_verified", "unit_item:2")
        assert r2["applied"] is False or r2["to_gate"] == mid
        # 高级事件可再升
        r3 = record_evidence_event(db, skill, "commit", "commit:abc123")
        assert r3["to_gate"] >= 2
        assert _gate_of(db, skill) == r3["to_gate"]
        # 低级事件不得降级
        r4 = record_evidence_event(db, skill, "quiz_verified", "unit_item:3")
        assert _gate_of(db, skill) == r3["to_gate"]
    finally:
        db.close()


def test_unknown_skill_is_noop():
    db = SessionLocal()
    try:
        r = record_evidence_event(db, "不存在的技能XYZ", "commit", "commit:x")
        assert r == {"skill": "不存在的技能XYZ", "from_gate": -1, "to_gate": -1, "applied": False}
    finally:
        db.close()
