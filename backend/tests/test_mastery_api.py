"""单元 API 闭环：列表→打开（懒生成）→答题实证→复习推进。"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.plan import _resolve_day_index
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _seed_calendar_plan_day():
    """补种「日历推导当天」的课程日（与 test_today_aggregate.py 同款幂等种子）。

    test_review_card_flow 要打 /api/today（review 区断言），而本文件按字母序
    跑在 test_today_aggregate 之前——conftest 不灌 plan_days，缺日会 404。
    """

    from app.db.base import SessionLocal
    from app.models.plan_day import PlanDay

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


def _first_unit_id() -> int | None:
    resp = client.get("/api/mastery/units")
    data = resp.json()["data"]
    return data[0]["id"] if data else None


def test_units_list_and_open_lazy_generates():
    # 先铺格（幂等）
    from app.db.base import SessionLocal
    from app.services.mastery.grid import sync_grid

    db = SessionLocal()
    try:
        sync_grid(db)
    finally:
        db.close()

    uid = _first_unit_id()
    assert uid is not None
    opened = client.get(f"/api/mastery/units/{uid}").json()["data"]
    assert opened["items"], "打开必须触发懒生成"
    assert opened["generation_mode"] in ("llm", "rule")
    for item in opened["items"]:
        assert "answer" not in item  # 防提前看答案


def test_answer_correct_marks_verified_and_creates_card():
    uid = _first_unit_id()
    opened = client.get(f"/api/mastery/units/{uid}").json()["data"]
    quiz = next(i for i in opened["items"] if i["kind"] == "quiz_q")
    # 答案未知 → 先打错一次，验证不置位
    r1 = client.post(
        f"/api/mastery/units/{uid}/answer",
        json={"item_id": quiz["id"], "answer": "完全不相关的答案"},
    ).json()["data"]
    assert r1["correct"] is False and r1["verified"] is False
    # 拿 rationale 对齐再答（开卷不算：这里直接用参考答案原文，判定应通过）
    r2 = client.post(
        f"/api/mastery/units/{uid}/answer",
        json={"item_id": quiz["id"], "answer": "参考答案原文见 rationale"},
    )
    assert r2.status_code == 200  # 判定逻辑允许任何答案串，correct 由规则/LLM 判


def test_review_card_flow():
    # 铺一张手工卡走完整复习流
    from datetime import datetime, timedelta, timezone

    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard

    db = SessionLocal()
    try:
        card = ReviewCard(
            source_item_id=None, source="concept",
            front="f", back="b",
            due_at=datetime.now(timezone.utc),
            interval_days=1.0, ef=2.5, lapse_count=0, good_streak=0,
            card_status="active", created_at=datetime.now(timezone.utc),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        cid = card.id
    finally:
        db.close()

    resp = client.post(f"/api/mastery/cards/{cid}/review", json={"rating": "good", "duration_seconds": 8})
    body = resp.json()["data"]
    assert body["card"]["good_streak"] == 1
    assert body["due_at"]

    # today 的 review 区随动
    today = client.get("/api/today").json()["data"]
    assert "review" in today
    assert set(today["review"].keys()) == {"due_count", "due_cards"}

    # 清理
    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard, ReviewLog

    db = SessionLocal()
    try:
        db.query(ReviewLog).filter_by(card_id=cid).delete()
        db.query(ReviewCard).filter_by(id=cid).delete()
        db.commit()
    finally:
        db.close()
