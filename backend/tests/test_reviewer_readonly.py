# backend/tests/test_reviewer_readonly.py
"""reviewer 铁律：只读 + fail-closed + 不写库（spec §4.3）。

两层钉子：
1. 契约层：validate_review_contract 缺字段/类型错/越界 → verdict=block，不吞异常。
2. 节点层：evaluate（含全图 invoke）拿到 db 也不写 SkillAssessment——
   写库唯一通道是 services/evidence_events.apply_review_proposal。
"""

from app.agents.reviewer.nodes import evaluate_evidence, validate_review_contract
from app.services.evidence_events import apply_review_proposal
from app.db.base import SessionLocal


GOOD = {
    "skill_name": "DPO",
    "proposed_level": 2,
    "evidence_score": 85,
    "reason": "完成 DPO 精读并通过 Teach-Back",
    "evidence_refs": ["unit_item:1"],
    "verdict": "pass",
}


def test_contract_accepts_good_payload():
    assert validate_review_contract(dict(GOOD)) == dict(GOOD)


def test_contract_fails_closed_on_missing_field():
    bad = dict(GOOD)
    del bad["evidence_refs"]
    out = validate_review_contract(bad)
    assert out["verdict"] == "block"
    assert "contract" in out.get("error", "")


def test_contract_fails_closed_on_bad_score_type():
    bad = dict(GOOD)
    bad["evidence_score"] = "high"  # 类型错
    assert validate_review_contract(bad)["verdict"] == "block"


def test_contract_fails_closed_on_range_violation():
    bad = dict(GOOD)
    bad["proposed_level"] = 9  # 越界（契约 0-5）
    out = validate_review_contract(bad)
    assert out["verdict"] == "block"
    assert "contract" in out.get("error", "")


def test_apply_is_only_write_path_and_checks_refs():
    db = SessionLocal()
    try:
        # 空 refs 拒绝（防虚构：没有证据的晋级进不来）
        r = apply_review_proposal(db, {**GOOD, "evidence_refs": []})
        assert r["applied"] is False and r["error"] == "evidence_refs_empty"
        # 分数不够拒绝
        r2 = apply_review_proposal(db, {**GOOD, "evidence_score": 60})
        assert r2["applied"] is False and r2["error"] == "score_below_threshold"
    finally:
        db.close()


# ============================================================
# 节点只读钉子（controller EXTRA）：evaluate 不写 SkillAssessment
# ============================================================


def _eval_state(**overrides) -> dict:
    """构造 evaluate 节点的最小入参（mock LLM → 必走规则评分路径）。"""
    state = {
        "task": {
            "id": 1,
            "title": "DPO 精读复盘",
            "skill_name": "DPO",
            "status": "done",
            "acceptance": ["完成 Teach-Back"],
        },
        "learning_log": {
            "content": "完成了 DPO 精读并通过 Teach-Back，总结了偏好数据构造的难点，下一步改进奖励模型。",
            "artifact_url": "https://github.com/o/r/commit/abc123",
        },
        "skill": {"id": 1, "name": "DPO", "level": 1, "target_level": 5, "evidence": []},
    }
    state.update(overrides)
    return state


def test_evaluate_node_writes_no_skill_assessment():
    """节点铁律：即使 state 里塞了 db，evaluate 也不落一行 SkillAssessment。"""
    from app.models.skill_assessment import SkillAssessment

    db = SessionLocal()
    try:
        state = _eval_state(db=db)
        before = db.query(SkillAssessment).count()
        out = evaluate_evidence(state)
        after = db.query(SkillAssessment).count()
        assert after == before, f"节点写了 SkillAssessment：{before} → {after}"
        assert isinstance(out.get("review"), dict)
        assert out["review"]["verdict"] == "pass"
        # 节点是提案者：绝不自称 applied
        assert out.get("applied") is None or out["applied"] is False
    finally:
        db.close()


def test_evaluate_node_fails_closed_without_write():
    """skill_name 类型错 → 节点输出 contract block + applied=False，且零写库。"""
    from app.models.skill_assessment import SkillAssessment

    db = SessionLocal()
    try:
        state = _eval_state(db=db)
        state["task"]["skill_name"] = 123  # 契约要求 str，类型错必须 block
        before = db.query(SkillAssessment).count()
        out = evaluate_evidence(state)
        after = db.query(SkillAssessment).count()
        assert after == before, f"block 路径写了库：{before} → {after}"
        assert out["review"]["verdict"] == "block"
        assert "contract" in out["review"].get("error", "")
        assert out["applied"] is False
    finally:
        db.close()


def test_graph_invoke_writes_no_skill_assessment():
    """全图 invoke（collect→evaluate→create→apply_skill_update→record）零 SkillAssessment 写入。"""
    from app.agents.reviewer.graph import build_reviewer_graph
    from app.models.skill_assessment import SkillAssessment

    db = SessionLocal()
    try:
        before = db.query(SkillAssessment).count()
        out = build_reviewer_graph().invoke(_eval_state(db=db))
        after = db.query(SkillAssessment).count()
        assert after == before, f"图内写了 SkillAssessment：{before} → {after}"
        assert isinstance(out.get("review"), dict)
    finally:
        db.close()


def test_route_applies_only_through_apply_layer():
    """API 层契约：pass → 经 apply_review_proposal 落库（SkillAssessment +1、等级只升）。"""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models.learning_log import LearningLog
    from app.models.skill import Skill
    from app.models.skill_assessment import SkillAssessment
    from app.models.task import Task

    db = SessionLocal()
    task_id = None
    old_level = None
    ids_before: set = set()
    try:
        skill = db.query(Skill).filter_by(name="DPO").first()
        old_level = skill.level if skill is not None else None
        ids_before = {r[0] for r in db.query(SkillAssessment.id).all()}
        # 结束本 session 的读事务：否则持有 SQLite SHARED 锁会挡住
        # TestClient 事务里的写入（回滚日志模式下 writer commit 需 EXCLUSIVE）。
        db.commit()

        task = Task(
            title="Task2 只读契约化测试任务",
            skill_name="DPO",
            status="doing",
            acceptance=["完成 Teach-Back"],
        )
        db.add(task)
        db.commit()
        task_id = task.id

        client = TestClient(app)
        resp = client.post(
            "/api/reviewer/review",
            json={
                "task_id": task_id,
                "content": "完成了 DPO 精读并通过 Teach-Back，总结了偏好数据构造的难点，下一步改进奖励模型。",
                "duration_minutes": 40,
                "artifact_url": "https://github.com/o/r/commit/abc123",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        # 响应契约：review + applied（写不写由 apply 层裁决，不是节点）
        assert isinstance(data.get("review"), dict)
        assert data["review"]["verdict"] == "pass"
        assert data["applied"] is True, data

        db.expire_all()
        ids_after = {r[0] for r in db.query(SkillAssessment.id).all()}
        assert len(ids_after - ids_before) == 1, "应恰有 1 行 SkillAssessment 经 apply 层落库"
        if skill is not None and old_level is not None:
            db.refresh(skill)
            assert skill.level >= old_level, "等级只升不降"
    finally:
        # 共享测试库自清理：还原等级、删除本测试造的行
        try:
            new_ids = {r[0] for r in db.query(SkillAssessment.id).all()} - ids_before
            if new_ids:
                db.query(SkillAssessment).filter(
                    SkillAssessment.id.in_(new_ids)
                ).delete(synchronize_session=False)
            if task_id is not None:
                db.query(LearningLog).filter(LearningLog.task_id == task_id).delete()
                db.query(Task).filter(Task.id == task_id).delete()
            if old_level is not None:
                sk = db.query(Skill).filter_by(name="DPO").first()
                if sk is not None:
                    sk.level = old_level
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
