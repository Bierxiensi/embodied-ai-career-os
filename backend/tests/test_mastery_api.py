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


def _seed_quiz_unit(title: str, ref: str) -> tuple[int, int, str]:
    """自建已知参考答案的单元+测验题：闭卷实证必须由测试自己掌握答案，
    不依赖懒生成内容（否则「答对→实证」只能断言 200，钉不住语义）。"""
    from datetime import datetime, timezone

    from app.db.base import SessionLocal
    from app.models.mastery import MasteryUnit, UnitItem

    db = SessionLocal()
    try:
        u = MasteryUnit(
            source_type="resource", source_ref=ref, title=title,
            skill_ids='["DPO"]', day_seq=None, generation_mode="rule",
            content_hash=None, status="opened", created_at=datetime.now(timezone.utc),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        item = UnitItem(
            unit_id=u.id, kind="quiz_q",
            body="DPO 绕过什么显式组件？", answer="奖励模型", rationale="BT 隐式奖励",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return u.id, item.id, item.answer
    finally:
        db.close()


def _cleanup_unit(unit_id: int) -> None:
    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard, UnitItem

    db = SessionLocal()
    try:
        item_ids = [i.id for i in db.query(UnitItem).filter_by(unit_id=unit_id).all()]
        for iid in item_ids:
            db.query(ReviewCard).filter_by(source_item_id=iid).delete()
        db.query(UnitItem).filter_by(unit_id=unit_id).delete()
        from app.models.mastery import MasteryUnit

        db.query(MasteryUnit).filter_by(id=unit_id).delete()
        db.commit()
    finally:
        db.close()


def test_answer_correct_marks_verified_and_creates_card():
    # 真·闭卷实证：用自建题的已知参考答案走规则判定 → verified 置位 + 建卡 + 落库翻真
    uid, iid, reference = _seed_quiz_unit("实证语义单元", "unit_test:verified")
    opened = client.get(f"/api/mastery/units/{uid}").json()["data"]
    quiz = next(i for i in opened["items"] if i["id"] == iid)
    assert quiz["is_verified"] is False  # 起点：未实证

    r = client.post(
        f"/api/mastery/units/{uid}/answer",
        json={"item_id": iid, "answer": reference},  # 参考答案原文 → 规则判定必过
    ).json()["data"]
    assert r["correct"] is True
    assert r["verified"] is True
    assert r["card_id"] is not None  # 答对建卡：answer → review 链路可接

    # 重新 GET 单元：is_verified 必须已翻真（不是只在 answer 响应里说说）
    reopened = client.get(f"/api/mastery/units/{uid}").json()["data"]
    after = next(i for i in reopened["items"] if i["id"] == iid)
    assert after["is_verified"] is True

    # 答错不得实证（同一判定口径的反面）
    uid2, iid2, _ = _seed_quiz_unit("未实证单元", "unit_test:unverified")
    r_bad = client.post(
        f"/api/mastery/units/{uid2}/answer",
        json={"item_id": iid2, "answer": "完全不相关的答案"},
    ).json()["data"]
    assert r_bad["correct"] is False and r_bad["verified"] is False

    _cleanup_unit(uid)
    _cleanup_unit(uid2)


def test_wrong_answer_creates_mistake_card():
    # spec §4.1 三源之「mistake 错题」：答错建的卡不得再被标成 concept
    uid, iid, _ = _seed_quiz_unit("错题来源单元", "unit_test:mistake-source")
    r = client.post(
        f"/api/mastery/units/{uid}/answer",
        json={"item_id": iid, "answer": "完全不相关的答案"},
    ).json()["data"]
    assert r["correct"] is False and r["card_id"] is not None

    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard

    db = SessionLocal()
    try:
        card = db.query(ReviewCard).filter_by(source_item_id=iid).first()
        assert card is not None, "答错必须建卡"
        assert card.source == "mistake"
    finally:
        db.close()

    _cleanup_unit(uid)


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


def test_first_answer_returns_card_id():
    # 首答建卡时 card_id 不得为 None（契约：answer → review 链路可接）
    uid = _first_unit_id()
    opened = client.get(f"/api/mastery/units/{uid}").json()["data"]
    quiz = next(i for i in opened["items"] if i["kind"] == "quiz_q")
    # 清掉该题可能已有的卡，确保走"首次建卡"路径
    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard

    db = SessionLocal()
    try:
        db.query(ReviewCard).filter_by(source_item_id=quiz["id"]).delete()
        db.commit()
    finally:
        db.close()
    r = client.post(
        f"/api/mastery/units/{uid}/answer",
        json={"item_id": quiz["id"], "answer": "参考答案原文见 rationale"},
    ).json()["data"]
    assert r["card_id"] is not None


def test_vacuous_reference_never_judges_correct():
    from app.api.mastery import _rule_judge  # 若判定是内联逻辑，抽出同名纯函数再测

    assert _rule_judge("ab", "cd") is False  # 参考词表为空 → 永不判对
    # 真·空词表：首两词均 <2 字符被过滤 → all([]) 恒真漏洞不得复现
    assert _rule_judge("a b", "any answer at all") is False
    assert _rule_judge("", "anything") is False  # 无参考答案 → 永不判对
