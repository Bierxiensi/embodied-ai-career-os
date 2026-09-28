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

    os.environ["DAILY_STUDY_MINUTES"] = "999"
    assert daily_study_minutes() == 120
    os.environ["DAILY_STUDY_MINUTES"] = "10"
    assert daily_study_minutes() == 60
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
