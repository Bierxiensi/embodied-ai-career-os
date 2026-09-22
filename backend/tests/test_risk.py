"""七维风险雷达测试（Phase 2）。

覆盖：
1. compute_risk 各维度阈值（纯函数，today 注入固定值，不依赖真实日历）
2. track_strict_pct：与 /api/job-hunt 同源的达标率计算（llm 67%/23%/3/13 回归锚点）
3. GET /api/risk 结构（7 维 + overall_level）
4. GET /api/plan/today 附加 risk 与 roi_ranked_tasks

隔离由 tests/conftest.py 提供（会话级临时库），本文件不自建数据库。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.risk import compute_risk, track_strict_pct
from app.core.target_roles import TARGET_ROLES
from app.db.base import SessionLocal
from app.main import app
from app.models.plan_day import PlanDay
from app.models.task import Task

client = TestClient(app)


def _base() -> dict:
    """compute_risk 默认入参（全绿基线），测试按需覆盖某一项。"""

    return {
        "days_since_last_experiment": 0,
        "days_since_last_code_artifact": 0,
        "defense_deadline_days": 200,
        "has_defense_task": False,
        "contacted_advisors": 5,
        "phd_window_days": 200,
        "main_track_strict_pct": 80,
        "main_track_gap_ratio": 0.1,
    }


def _level(result, key: str) -> str:
    return next(d.level for d in result.dimensions if d.key == key)


# ============================================================
# 1. 各维度阈值（纯函数）
# ============================================================


def test_execution_red_when_both_stale():
    r = compute_risk(**{**_base(), "days_since_last_experiment": 10, "days_since_last_code_artifact": 10})
    assert _level(r, "execution") == "red"


def test_execution_red_when_none():
    r = compute_risk(**{**_base(), "days_since_last_experiment": None, "days_since_last_code_artifact": None})
    assert _level(r, "execution") == "red"


def test_execution_amber_when_one_stale():
    # 仅实验 >3 天，代码新鲜 → amber
    r = compute_risk(**{**_base(), "days_since_last_experiment": 5, "days_since_last_code_artifact": 1})
    assert _level(r, "execution") == "amber"
    # 仅代码 >3 天，实验新鲜 → amber
    r2 = compute_risk(**{**_base(), "days_since_last_experiment": 1, "days_since_last_code_artifact": 5})
    assert _level(r2, "execution") == "amber"


def test_execution_green_when_fresh():
    r = compute_risk(**{**_base(), "days_since_last_experiment": 1, "days_since_last_code_artifact": 1})
    assert _level(r, "execution") == "green"


def test_academic_red_without_defense_task():
    r = compute_risk(**{**_base(), "defense_deadline_days": 50, "has_defense_task": False})
    assert _level(r, "academic") == "red"


def test_academic_amber_with_defense_task():
    r = compute_risk(**{**_base(), "defense_deadline_days": 50, "has_defense_task": True})
    assert _level(r, "academic") == "amber"


def test_academic_green_when_far():
    r = compute_risk(**{**_base(), "defense_deadline_days": 100, "has_defense_task": False})
    assert _level(r, "academic") == "green"


def test_phd_red_zero_contacted():
    r = compute_risk(**{**_base(), "phd_window_days": 30, "contacted_advisors": 0})
    assert _level(r, "phd") == "red"


def test_phd_amber_one_or_two_contacted():
    r1 = compute_risk(**{**_base(), "phd_window_days": 30, "contacted_advisors": 1})
    r2 = compute_risk(**{**_base(), "phd_window_days": 30, "contacted_advisors": 2})
    assert _level(r1, "phd") == "amber"
    assert _level(r2, "phd") == "amber"


def test_phd_green_three_or_more():
    r = compute_risk(**{**_base(), "phd_window_days": 30, "contacted_advisors": 3})
    assert _level(r, "phd") == "green"


def test_phd_green_window_far():
    # 窗口充裕时即便 0 联系也 green（其余分支）
    r = compute_risk(**{**_base(), "phd_window_days": 100, "contacted_advisors": 0})
    assert _level(r, "phd") == "green"


def test_skill_thresholds():
    assert _level(compute_risk(**{**_base(), "main_track_strict_pct": 10}), "skill") == "red"
    assert _level(compute_risk(**{**_base(), "main_track_strict_pct": 30}), "skill") == "amber"
    assert _level(compute_risk(**{**_base(), "main_track_strict_pct": 50}), "skill") == "green"


def test_career_threshold():
    assert _level(compute_risk(**{**_base(), "main_track_gap_ratio": 0.7}), "career") == "amber"
    assert _level(compute_risk(**{**_base(), "main_track_gap_ratio": 0.5}), "career") == "green"


def test_company_and_financial_always_green():
    # 即便其他维度全红，公司/财务仍恒 green
    r = compute_risk(**{**_base(), "main_track_strict_pct": 10, "main_track_gap_ratio": 0.9,
                        "defense_deadline_days": 10, "phd_window_days": 10,
                        "contacted_advisors": 0, "days_since_last_experiment": 99,
                        "days_since_last_code_artifact": 99})
    assert _level(r, "company") == "green"
    assert _level(r, "financial") == "green"


def test_overall_level_is_worst():
    r = compute_risk(**{**_base(), "main_track_strict_pct": 10})  # skill red
    assert r.overall_level == "red"
    r2 = compute_risk(**{**_base(), "main_track_strict_pct": 30})  # skill amber, rest green
    assert r2.overall_level == "amber"
    r3 = compute_risk(**_base())  # all green
    assert r3.overall_level == "green"


# ============================================================
# 2. track_strict_pct（与 job_hunt 同源）
# ============================================================


def test_track_strict_pct_llm_anchor():
    """llm 13 项技能中恰好 3 项达标 → 23/3/13（job_hunt 口径回归锚点）。"""

    role = next(r for r in TARGET_ROLES if r.key == "llm")
    assert len(role.required_skills) == 13, "llm 主攻赛道应有 13 项 required_skills"

    skill_levels = {}
    for i, name in enumerate(role.required_skills):
        # 前 3 项达标（level>=4），其余 2
        skill_levels[name.lower()] = 5 if i < 3 else 2

    pct, qualified, required = track_strict_pct(
        role.required_skills, role.required_level, skill_levels
    )
    assert pct == 23, pct
    assert qualified == 3, qualified
    assert required == 13, required


def test_track_strict_pct_empty():
    assert track_strict_pct([], 4, {}) == (0, 0, 0)


# ============================================================
# 3. API 结构
# ============================================================


def test_risk_api_returns_seven_dimensions():
    resp = client.get("/api/risk")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert len(data["dimensions"]) == 7, data["dimensions"]
    assert data["overall_level"] in {"green", "amber", "red"}
    keys = {d["key"] for d in data["dimensions"]}
    assert keys == {
        "execution", "academic", "phd", "skill", "career", "company", "financial"
    }
    for d in data["dimensions"]:
        assert set(d.keys()) == {"key", "label", "level", "reason"}
        assert d["level"] in {"green", "amber", "red"}


# ============================================================
# 4. /api/plan/today 附加 risk + roi_ranked_tasks
# ============================================================


_SEQ = 3  # 避开 test_plan_api 的 1/2，且落在 1..30 范围内


@pytest.fixture(scope="module", autouse=True)
def _seed_day_and_task():
    db = SessionLocal()
    try:
        if db.query(PlanDay).filter(PlanDay.seq == _SEQ).first() is None:
            db.add(PlanDay(
                seq=_SEQ, phase=1, phase_name="Phase2 测试周",
                title="Phase2 测试课程日", theme="risk",
                objectives=["o1"], acceptance=["a1"],
                interview_topics=["t1"], resources=["r1"],
                est_minutes=360, track_key="llm",
            ))
            db.flush()
            day_id = db.query(PlanDay).filter(PlanDay.seq == _SEQ).first().id
            db.add(Task(
                title="Phase2 测试 · Python 强项任务",
                objective="验证 ROI 计入",
                duration=30, status="todo",
                skill_name="Python", source="seed",
                track_key="llm", plan_day_id=day_id,
            ))
        db.commit()
    finally:
        db.close()
    yield


def test_today_includes_risk_and_roi():
    resp = client.get(f"/api/plan/today?day={_SEQ}")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    # risk 非空且结构正确
    assert data["risk"] is not None
    assert len(data["risk"]["dimensions"]) == 7
    assert data["risk"]["overall_level"] in {"green", "amber", "red"}

    # roi_ranked_tasks 为列表且长度 <=5，每项结构正确，roi 不超过上限
    roi = data["roi_ranked_tasks"]
    assert isinstance(roi, list)
    assert len(roi) <= 5
    for item in roi:
        assert set(item.keys()) == {"task_id", "title", "skill_name", "roi", "reasons"}
        assert item["roi"] <= 1.5
        assert isinstance(item["reasons"], list) and item["reasons"]

    # 当日任务应进入 ROI 视图（Python ∈ 主攻 required → goal_relevance 1.0）
    assert any(t["skill_name"] == "Python" for t in roi), roi
