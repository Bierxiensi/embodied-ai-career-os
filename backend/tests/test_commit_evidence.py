# backend/tests/test_commit_evidence.py
"""commit 半确认 → L2 证据（capture-first：草稿 → 人确认 → append-only）。

字段口径对齐 `app/models/commit_suggestion.py`（不发明字段）：
- CommitSuggestion: id / commit_sha / commit_message / repo / files_changed /
  diff_summary / ai_suggestions / status(pending|confirmed|rejected) /
  confirmed_skill / confirmed_at / created_at
- 确认请求体为 ConfirmRequest {skill}（api/github.py），不是模型列。
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.models.commit_suggestion import CommitSuggestion
from app.models.skill import Skill
from app.models.skill_assessment import SkillAssessment

SHA = "deadbeef1234"
SKILL = "DPO"  # 种子技能（app/core/skill_profile.py）


def test_confirm_suggestion_upgrades_gate_to_l2():
    """POST /suggestions/{id}/confirm → 状态 confirmed + commit L2 证据事件。"""
    db = SessionLocal()
    original_gate = None
    sid = None
    try:
        skill = db.query(Skill).filter_by(name=SKILL).first()
        assert skill is not None, "种子技能 DPO 缺失（app/core/skill_profile.py）"
        original_gate = skill.evidence_gate
        # 从 L0 起步：升级必须由本次确认驱动，与测试执行顺序无关
        skill.evidence_gate = 0
        db.add(CommitSuggestion(
            id="test-commit-evidence-1",
            commit_sha=SHA,
            commit_message="实现 DPO trainer 骨架",
            repo="embodied-ai-career-os",
            status="pending",
        ))
        db.commit()  # 结束写事务，放行 TestClient 独立会话的写入
        sid = "test-commit-evidence-1"

        client = TestClient(app)
        resp = client.post(
            f"/api/github/suggestions/{sid}/confirm", json={"skill": SKILL}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        # 既有 key 只追加不改名
        assert data["id"] == sid
        assert data["skill"] == SKILL
        assert data["status"] == "confirmed"
        # 新增 evidence 字段：apply 层返回的 L2 晋级结果
        evidence = data["evidence"]
        assert evidence["skill"] == SKILL
        assert evidence["to_gate"] >= 2, evidence

        db.expire_all()
        row = db.query(CommitSuggestion).filter_by(id=sid).first()
        assert row is not None
        assert row.status == "confirmed"
        assert row.confirmed_skill == SKILL

        refreshed = db.query(Skill).filter_by(name=SKILL).first()
        assert int(refreshed.evidence_gate or 0) >= 2

        # 证据 ref 可追溯到具体 commit（防虚构）+ append-only 落 SkillAssessment
        ref = f"commit:{SHA}"
        assess = (
            db.query(SkillAssessment)
            .filter(SkillAssessment.reason.contains(ref))
            .first()
        )
        assert assess is not None, f"确认后未落 SkillAssessment 证据行（ref={ref}）"
    finally:
        if sid is not None:
            try:
                db.query(SkillAssessment).filter(
                    SkillAssessment.reason.contains(f"commit:{SHA}")
                ).delete(synchronize_session=False)
                row = db.query(CommitSuggestion).filter_by(id=sid).first()
                if row is not None:
                    db.delete(row)
                sk = db.query(Skill).filter_by(name=SKILL).first()
                if sk is not None:
                    # 还原共享状态：后续 test_evidence_events 要求 DPO gate 未被抬高
                    sk.evidence_gate = original_gate
                db.commit()
            except Exception:
                db.rollback()
        db.close()


def test_confirm_unknown_suggestion_returns_404():
    """不存在的建议不产生证据事件（先查状态，查不到即 404）。"""
    client = TestClient(app)
    resp = client.post(
        "/api/github/suggestions/nonexistent/confirm", json={"skill": SKILL}
    )
    assert resp.status_code == 404
