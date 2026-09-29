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


def test_derived_writeback_never_lowers_gate():
    """派生回写只升不降：/skills/evidence 的推导值不得抹平已抬高的 gate。

    背景（controller EXTRA）：两处 `s.evidence_gate = ev["gate_level"]` 是无条件
    覆盖——事件/人工抬到 2 后，一次看板请求就会把 gate 打回推导值，破坏
    evidence_events 的只升不变量。
    """
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models.skill import Skill

    db = SessionLocal()
    original = None
    try:
        skill = db.query(Skill).filter_by(name="DPO").first()
        if skill is None:  # 无种子技能时跳过（与 _gate_of 同口径）
            return
        original = skill.evidence_gate
        skill.evidence_gate = 2
        db.commit()  # 结束写事务，放行下面 TestClient 事务的写入

        client = TestClient(app)
        resp = client.get("/api/skills/evidence")
        assert resp.status_code == 200

        db.refresh(skill)
        assert int(skill.evidence_gate or 0) >= 2, (
            f"派生回写把 evidence_gate 降到了 {skill.evidence_gate!r}（只升不变量被破坏）"
        )
    finally:
        try:
            sk = db.query(Skill).filter_by(name="DPO").first()
            if sk is not None:
                sk.evidence_gate = original
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


def test_event_promoted_gate_visible_in_evidence_responses():
    """事件晋级后的**有效门值**必须出现在两个 evidence 响应里（不只写库）。

    背景（review Critical）：/skills/evidence 与 /skills/{id}/evidence 在
    ``max(derived, stored)`` 写回后仍返回裸派生 ``ev["gate_level"]`` ——
    事件脊柱（quiz/teachback/commit → skills.evidence_gate）从不参与
    compute_skill_evidence，导致 EvidenceGateList 显示 未入门/L1 而 DB 已是 L2，
    与同页 PortfolioPanel 矛盾。本测试 pin：两条响应路径的 ``evidence_gate``
    都等于 DB 有效值。
    """
    from fastapi.testclient import TestClient

    from app.core.evidence import compute_skill_evidence
    from app.main import app
    from app.models.skill import Skill

    db = SessionLocal()
    original = None
    try:
        skill = db.query(Skill).filter_by(name="DPO").first()
        if skill is None:  # 无种子技能时跳过（与 _gate_of 同口径）
            return
        original = skill.evidence_gate

        # 派生值（事件脊柱不参与 compute_skill_evidence —— 与实现细节无关）
        derived = int(compute_skill_evidence(skill.name, db)["gate_level"])
        # 经事件通道晋级（写库唯一通道是 apply 层）：至少到 2，且能抬则
        # 严格高于派生值 —— 这样"返回裸派生值"的坏实现必然与 DB 值不同，
        # 本测试才真能 pin 住 Critical（否则 stored==derived 时两版实现同过）。
        target = max(2, derived + 1)
        kind = {1: "quiz_verified", 2: "commit", 3: "experiment", 4: "comparison_report"}[
            min(target, 4)
        ]
        r = record_evidence_event(db, skill.name, kind, f"pin-gate-resp:{kind}")
        # 同级幂等：门已在位时 applied=False 是合法 no-op（见 signal3 口径）
        assert r["applied"] or r["to_gate"] >= min(target, 4), f"事件未晋级：{r!r}"
        db.commit()  # 结束写事务，放行下面 TestClient 事务的读

        db.refresh(skill)
        db_gate = int(skill.evidence_gate or 0)
        assert db_gate >= 2, f"事件晋级后 DB 门值 {db_gate} < 2"

        client = TestClient(app)
        # 路径 1：GET /api/skills/evidence（列表）
        resp = client.get("/api/skills/evidence")
        assert resp.status_code == 200
        rows = resp.json()["data"]
        hit = next((row for row in rows if row["id"] == skill.id), None)
        assert hit is not None, f"列表响应缺技能 {skill.name!r}"
        assert int(hit["evidence_gate"]) == db_gate, (
            f"列表响应 evidence_gate={hit['evidence_gate']!r} ≠ DB {db_gate}"
            f"（派生 {derived} —— 响应须返回有效值 max(派生, 存储)）"
        )
        assert int(hit["evidence_gate"]) >= 2, "事件晋级后的门值在列表响应里不可见"

        # 路径 2：GET /api/skills/{id}/evidence（单条）
        resp2 = client.get(f"/api/skills/{skill.id}/evidence")
        assert resp2.status_code == 200
        single = resp2.json()["data"]
        assert int(single["evidence_gate"]) == db_gate, (
            f"单条响应 evidence_gate={single['evidence_gate']!r} ≠ DB {db_gate}"
            f"（派生 {derived} —— 响应须返回有效值 max(派生, 存储)）"
        )
        assert int(single["evidence_gate"]) >= 2, "事件晋级后的门值在单条响应里不可见"
    finally:
        try:
            sk = db.query(Skill).filter_by(name="DPO").first()
            if sk is not None:
                sk.evidence_gate = original
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
