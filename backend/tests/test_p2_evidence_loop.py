"""P2 证据闭环测试。

覆盖 docs/platform-direction-30day.md §七 的 P2 五项机制：

  A. experiments 表 + CRUD（实验对比表数据源，决策 4）
  B. 四件套 questions 由题库当日条数自动判定（>= QUESTIONS_MIN_PER_DAY）
  C. GitHub commit 按日期自动归集为 commit artifact（auto_verified、按 sha 去重）
  D. 技能晋级 evidence-gated（Experiment → gate>=3，决策 3）
  E. TECH_BLACKLIST 接 Planner 硬拒绝（决策 6）

隔离：由 tests/conftest.py 提供会话级临时库；本文件自带 autouse 夹具只建所需课程日，
并在断言后清理自己造的数据，避免污染同会话的其他测试模块。绝不碰开发库。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.target_roles import SPRINT_START, TargetRole
from app.db.base import SessionLocal
from app.main import app
from app.models.day_artifact import ARTIFACT_KIND_COMMIT
from app.models.interview_question import InterviewQuestion
from app.models.plan_day import PlanDay
from app.models.skill import Skill

client = TestClient(app)

# 只建 Day 1（commit 按日期归集 / 题库当日判定都落在这一天）
_SEEDED_SEQS = (1,)


@pytest.fixture(scope="module", autouse=True)
def _seed_plan_days():
    """建少量课程日供本文件使用（幂等：按 seq 存在即跳过）。"""

    db = SessionLocal()
    try:
        existing = {d.seq for d in db.query(PlanDay).all()}
        for seq in _SEEDED_SEQS:
            if seq in existing:
                continue
            db.add(
                PlanDay(
                    seq=seq,
                    phase=1,
                    phase_name="P2 测试周",
                    title=f"P2 课程日 {seq}",
                    theme="Transformer",
                    objectives=["目标"],
                    acceptance=["验收"],
                    interview_topics=["面试题"],
                    resources=["Hugging Face LLM Course"],
                    est_minutes=360,
                    track_key="llm",
                )
            )
        db.commit()
    finally:
        db.close()

    yield


def _today(day: int) -> dict:
    resp = client.get(f"/api/plan/today?day={day}")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ============================================================
# A. experiments CRUD（实验对比表数据源）
# ============================================================


def _lora_variants() -> list[dict]:
    """P2 验收场景：一次 LoRA vs QLoRA 实验的三个变体。"""

    return [
        {"name": "Full SFT", "trainable_params": "7B", "gpu_mem": "80G", "result": "最好"},
        {"name": "LoRA r=16", "trainable_params": "4M", "gpu_mem": "24G", "result": "接近"},
        {"name": "QLoRA r=16", "trainable_params": "4M", "gpu_mem": "10G", "result": "略降"},
    ]


def test_experiment_create_list_patch_delete():
    """录入→列表→更新结论→删除，variants 原样存回供前端渲染对比表。"""

    resp = client.post(
        "/api/experiments",
        json={
            "day_seq": 11,
            "name": "P2 · LoRA vs QLoRA",
            "kind": "finetune",
            "skill_name": "LoRA/QLoRA",
            "variants": _lora_variants(),
            "metrics": [{"name": "win_rate", "value": 0.51}],
            "conclusion": "初测",
        },
    )
    assert resp.status_code == 200, resp.text
    exp = resp.json()["data"]
    exp_id = exp["id"]

    assert exp["day_seq"] == 11
    assert exp["kind"] == "finetune"
    # 对比表列 = variants 字段并集；3 个变体必须原样保留
    assert len(exp["variants"]) == 3
    assert {v["name"] for v in exp["variants"]} == {"Full SFT", "LoRA r=16", "QLoRA r=16"}

    listed = client.get("/api/experiments?skill_name=LoRA/QLoRA").json()["data"]
    assert any(e["id"] == exp_id for e in listed), listed

    patched = client.patch(
        f"/api/experiments/{exp_id}", json={"conclusion": "QLoRA 性价比最高"}
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["conclusion"] == "QLoRA 性价比最高"

    assert client.delete(f"/api/experiments/{exp_id}").status_code == 200
    assert client.get(f"/api/experiments/{exp_id}").status_code == 404


def test_experiment_filters_by_day_seq():
    """?day_seq= 过滤生效（实验按课程日归档）。"""

    exp = client.post(
        "/api/experiments",
        json={"day_seq": 11, "name": "P2 · 过滤测试", "kind": "benchmark"},
    ).json()["data"]
    try:
        rows = client.get("/api/experiments?day_seq=11").json()["data"]
        assert all(r["day_seq"] == 11 for r in rows)
        assert any(r["id"] == exp["id"] for r in rows)
    finally:
        client.delete(f"/api/experiments/{exp['id']}")


def test_experiment_invalid_kind_and_day_seq_are_422():
    """kind 只允许 finetune/benchmark/ablation；day_seq 必须 1..30。"""

    assert (
        client.post(
            "/api/experiments", json={"day_seq": 1, "name": "x", "kind": "magic"}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/experiments", json={"day_seq": 31, "name": "x"}).status_code
        == 422
    )


# ============================================================
# B. 题库条数自动判定 questions（四件套不再靠手工勾）
# ============================================================


def test_questions_axis_auto_satisfied_by_bank_count():
    """题库当天攒够 5 题 → questions 轴自动判定为已交，不再出现在 missing。"""

    db = SessionLocal()
    try:
        for i in range(5):
            db.add(
                InterviewQuestion(
                    category="LLM",
                    question=f"P2 自动判定题 {i}",
                    difficulty="intermediate",
                    source_day_seq=1,
                    skill_name="LoRA/QLoRA",
                )
            )
        db.commit()
        created_ids = [
            r.id
            for r in db.query(InterviewQuestion)
            .filter(InterviewQuestion.question.like("P2 自动判定题%"))
            .all()
        ]
        assert len(created_ids) >= 5
    finally:
        db.close()

    try:
        data = _today(1)
        assert data["questions_from_bank"] >= 5
        assert data["artifact_status"]["questions"] >= 5
        # 关键断言：题库够数时，questions 槽位不再算「缺」
        assert "questions" not in data["missing_kinds"], data["missing_kinds"]
    finally:
        db = SessionLocal()
        try:
            db.query(InterviewQuestion).filter(
                InterviewQuestion.id.in_(created_ids)
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


# ============================================================
# C. commit 按日期自动归集
# ============================================================


def test_commit_sync_inline_maps_and_dedups():
    """inline commit：SPRINT_START 当天 → Day1，auto_verified=True，同 sha 不重复写。"""

    before_ids = {a["id"] for a in _today(1)["artifacts"]}
    sha = "p2test" + uuid.uuid4().hex[:12]
    body = {"commits": [{"sha": sha, "date": SPRINT_START, "message": "P2 归集测试"}]}

    first = client.post("/api/plan/commits/sync", json=body)
    assert first.status_code == 200, first.text
    d1 = first.json()["data"]
    assert d1["synced"] == 1 and d1["source"] == "inline"

    # 再同步一次：同 (plan_day, sha) 去重 → synced 0
    second = client.post("/api/plan/commits/sync", json=body).json()["data"]
    assert second["synced"] == 0

    after = _today(1)["artifacts"]
    new = [a for a in after if a["id"] not in before_ids]
    commits = [a for a in new if a["kind"] == ARTIFACT_KIND_COMMIT]
    assert commits, new
    assert all(a["auto_verified"] is True for a in commits), commits

    # 清理，避免污染同会话其他模块
    for a in new:
        client.delete(f"/api/plan/artifacts/{a['id']}")


def test_commit_sync_skips_without_token(monkeypatch):
    """未配置 token 时优雅跳过（skipped=True），不 500。"""

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("PLAN_REPO", raising=False)
    resp = client.post("/api/plan/commits/sync", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["synced"] == 0
    assert data.get("skipped") is True


# ============================================================
# D. 技能晋级 evidence-gated
# ============================================================


def test_skill_evidence_gate_reaches_l3_from_experiment():
    """一条 skill_name 命中的 Experiment → 该技能证据可信达到 L3。"""

    db = SessionLocal()
    try:
        skill = db.query(Skill).filter(Skill.name == "LoRA/QLoRA").first()
        if skill is None:
            skill = Skill(name="LoRA/QLoRA", category="LLM", level=1, target_level=4)
            db.add(skill)
            db.commit()
            db.refresh(skill)
        skill_id = skill.id
    finally:
        db.close()

    exp = client.post(
        "/api/experiments",
        json={
            "day_seq": 11,
            "name": "P2 · 证据实验",
            "kind": "finetune",
            "skill_name": "LoRA/QLoRA",
        },
    ).json()["data"]

    try:
        ev = client.get(f"/api/skills/{skill_id}/evidence").json()["data"]
        assert ev["evidence_gate"] >= 3, ev
        assert any(e["level"] == 3 for e in ev["evidence"]), ev["evidence"]

        # 推导结果写回 skills.evidence_gate（幂等，供看板直接读）
        db = SessionLocal()
        try:
            assert db.get(Skill, skill_id).evidence_gate >= 3
        finally:
            db.close()
    finally:
        client.delete(f"/api/experiments/{exp['id']}")


# ============================================================
# E. TECH_BLACKLIST 接 Planner 硬拒绝
# ============================================================


def test_planner_hard_rejects_all_blacklisted_track(monkeypatch):
    """赛道硬性要求全是 D 级技术 → 不生成任务，返回 blocked + 拒绝文案。"""

    from app.api import planner as planner_mod

    fake = TargetRole(
        key="p2test",
        name="P2 测试赛道",
        priority="暂缓",
        salary_range="0",
        note="",
        required_skills=["ROS2", "VLA"],
        required_level=4,
        frozen=True,
    )
    # 直接命中「候选全被拦截」分支，绕过 LangGraph（该分支在 invoke 之前返回）
    monkeypatch.setattr(planner_mod, "_resolve_track", lambda _key: fake)

    resp = client.post(
        "/api/planner/generate",
        json={"available_minutes": 30, "skills": [], "persist": False},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["title"] == ""
    assert set(data["blocked"]) == {"ROS2", "VLA"}
    assert "⛔" in data["reason"]
    assert "D 级技术" in data["reason"]
