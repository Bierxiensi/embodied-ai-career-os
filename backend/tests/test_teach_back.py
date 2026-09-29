"""Teach-Back：教练发起口述回收 → 判定 → 自动写学习日志 + 错项入 SM-2。"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.models.learning_log import LearningLog
from app.models.mastery import MasteryUnit, ReviewCard, UnitItem
from app.services.mastery.teachback import judge_answer

client = TestClient(app)


def test_judge_rule_fallback():
    # conftest 钉死 mock → 走规则兜底；返回 dict：判定结果 + 降级可见的 mode
    ok = judge_answer("DPO 绕过什么？", "奖励模型", "DPO 不再需要显式奖励模型")
    assert ok["passed"] is True and ok["mode"] == "rule"
    bad = judge_answer("DPO 绕过什么？", "奖励模型", "今天天气不错")
    assert bad["passed"] is False and bad["mode"] == "rule"


def test_judge_mode_rule_pin_on_pass():
    # 降级可见性钉：Mock 从不判分 → passed=True 的判定也必须如实上报 mode="rule"
    result = judge_answer("DPO 绕过什么？", "奖励模型", "DPO 不再需要显式奖励模型")
    assert result["passed"] is True
    assert result["mode"] == "rule"


def test_complete_writes_learning_log_auto():
    db = SessionLocal()
    try:
        u = MasteryUnit(
            source_type="paper", source_ref="paper:777", title="TeachBack 测验单元",
            skill_ids='["DPO"]', day_seq=None, generation_mode="rule",
            content_hash=None, status="opened", created_at=datetime.now(timezone.utc),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        item = UnitItem(
            unit_id=u.id, kind="quiz_q",
            body="DPO 绕过什么？", answer="奖励模型", rationale="BT 隐式奖励",
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        before = db.query(LearningLog).count()
        resp = client.post("/api/teach-back/complete", json={
            "unit_id": u.id,
            "duration_minutes": 15,
            "answers": [
                {"item_id": item.id, "spoken": "DPO 不再需要显式奖励模型"},
                # 第二题答错（故意）：应生成复习卡
                {"item_id": item.id, "spoken": "不知道"},
            ],
        })
        body = resp.json()["data"]
        assert body["log_id"]
        assert body["cards_created"] >= 1
        # 降级可见：每条裁决都带 judge_mode（pinned mock 下恒为 rule）
        assert all(v.get("judge_mode") == "rule" for v in body["verdicts"])
        log = db.get(LearningLog, body["log_id"])
        assert log is not None
        assert "DPO 不再需要显式奖励模型" in log.content  # 口述原文，不改写
        assert log.content.startswith("Teach-Back · ")  # 前缀是前端完成徽章的跨栈契约
        assert log.duration_minutes == 15
        assert db.query(LearningLog).count() == before + 1

        # 口述过判 → 实证（与 answer 路径统一语义，is_verified 必须落库）
        db.refresh(item)
        assert item.is_verified is True

        db.query(ReviewCard).filter_by(source_item_id=item.id).delete()
        db.query(UnitItem).filter_by(id=item.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.query(LearningLog).filter_by(id=log.id).delete()
        db.commit()
    finally:
        db.close()


def test_wrong_item_twice_creates_only_one_card():
    # 一题一卡不变量：同 item 反复答错不刷 SM-2 队列
    db = SessionLocal()
    try:
        u = MasteryUnit(
            source_type="paper", source_ref="paper:775", title="Dedup 单元",
            skill_ids='["DPO"]', day_seq=None, generation_mode="rule",
            content_hash=None, status="opened", created_at=datetime.now(timezone.utc),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        item = UnitItem(unit_id=u.id, kind="quiz_q", body="Q", answer="奖励模型", rationale="r")
        db.add(item)
        db.commit()
        db.refresh(item)

        def submit():
            return client.post("/api/teach-back/complete", json={
                "unit_id": u.id,
                "duration_minutes": 5,
                "answers": [{"item_id": item.id, "spoken": "完全不对"}],
            }).json()["data"]

        r1 = submit()
        r2 = submit()
        assert r1["cards_created"] == 1
        assert r2["cards_created"] == 0  # 已有卡不重复建
        n = db.query(ReviewCard).filter_by(source_item_id=item.id).count()
        assert n == 1

        db.query(ReviewCard).filter_by(source_item_id=item.id).delete()
        db.query(UnitItem).filter_by(id=item.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.query(LearningLog).filter(LearningLog.content.like("Teach-Back · Dedup 单元%")).delete()
        db.commit()
    finally:
        db.close()
