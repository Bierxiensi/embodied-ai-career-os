"""GET /api/today 聚合端点 + 容量预检（spec §2.4/§4.4）。"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.plan import _resolve_day_index
from app.core.capacity import assert_plan_capacity, daily_study_minutes
from app.db.base import SessionLocal
from app.main import app
from app.models.plan_day import PlanDay

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _seed_calendar_plan_day():
    """补种「日历推导当天」的课程日。

    conftest 的 init_db() 不灌 plan_days（那是 seed_plan_30d.py 的职责），
    单跑本文件时 /api/today 会因课程日缺失 404。与 test_plan_api.py 同款
    幂等种子，只建本文件需要的那一天。
    """

    seq = _resolve_day_index(date.today())[0]
    db = SessionLocal()
    try:
        if db.query(PlanDay).filter(PlanDay.seq == seq).first() is None:
            db.add(
                PlanDay(
                    seq=seq,
                    phase=1,
                    phase_name="第一周 · 打穿 Transformer",
                    title=f"测试课程日 {seq}",
                    theme="Transformer",
                    objectives=[f"目标 {seq}-1"],
                    acceptance=[f"验收 {seq}-1"],
                    interview_topics=[f"面试题 {seq}-1"],
                    resources=["Hugging Face LLM Course"],
                    est_minutes=360,
                    track_key="llm",
                )
            )
            db.commit()
    finally:
        db.close()
    yield


def test_capacity_rejects_over_plan():
    c = assert_plan_capacity(planned_minutes=200, available_minutes=90)
    assert c["ok"] is False
    assert c["shortfall_minutes"] == 110
    assert "最短" in c["suggestion"]


def test_capacity_ok_under_limit():
    c = assert_plan_capacity(planned_minutes=60, available_minutes=90)
    assert c["ok"] is True
    assert c["suggestion"] == ""


def test_daily_minutes_clamped():
    import os

    try:
        os.environ["DAILY_STUDY_MINUTES"] = "999"
        assert daily_study_minutes() == 120
        os.environ["DAILY_STUDY_MINUTES"] = "10"
        assert daily_study_minutes() == 60
    finally:
        # 断言失败也不许把 env 泄漏给后续用例（否则容量断言会拿到脏预算）
        os.environ.pop("DAILY_STUDY_MINUTES", None)


def test_today_endpoint_shape():
    resp = client.get("/api/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    for key in ("today", "learning_logs_today", "capacity"):
        assert key in data
    assert set(data["capacity"].keys()) == {
        "ok", "available_minutes", "planned_minutes", "shortfall_minutes", "suggestion",
    }


def test_learning_logs_today_is_24h_window():
    from datetime import datetime, timedelta

    from app.db.base import SessionLocal
    from app.models.learning_log import LearningLog

    db = SessionLocal()
    try:
        fresh = LearningLog(content="fresh", created_at=datetime.utcnow())
        stale = LearningLog(content="stale", created_at=datetime.utcnow() - timedelta(hours=48))
        db.add_all([fresh, stale])
        db.commit()
    finally:
        db.close()
    client = TestClient(app)
    data = client.get("/api/today").json()["data"]
    contents = [x["content"] for x in data["learning_logs_today"]]
    assert "fresh" in contents and "stale" not in contents
    db = SessionLocal()
    try:
        db.query(LearningLog).filter(LearningLog.content.in_(["fresh", "stale"])).delete()
        db.commit()
    finally:
        db.close()


def test_capacity_uses_task_duration_not_course_estimate():
    # 有任务时按任务时长求和；不再被 plan_30d 的 est_minutes(180-420) 刷成永久红徽章。
    # 单元式断言而非 HTTP：本文件夹具只种 plan_day 不种 tasks，走 HTTP 时
    # 「无任务 → 回退 est_minutes」是合法分支，钉不住「有任务」的主口径。
    from app.api.today import _planned_minutes

    assert _planned_minutes(
        {"day": {"est_minutes": 360}, "tasks": [{"duration": 30}, {"duration": 25}]}
    ) == 55
    # 无任务才回退课程日估计
    assert _planned_minutes({"day": {"est_minutes": 360}, "tasks": []}) == 360
    # 字段全缺回退 0（且绝不抛错）
    assert _planned_minutes({}) == 0


def test_capacity_non_positive_available_falls_back():
    # available <= 0 时不得进向上取整除法（曾经会 ZeroDivisionError）
    c = assert_plan_capacity(planned_minutes=200, available_minutes=0)
    assert c["available_minutes"] >= 60
    assert c["ok"] is False
    assert "最短" in c["suggestion"]
