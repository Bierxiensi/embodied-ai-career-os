"""掌握单元 4 表建模（spec §4.1）。字段名是后续任务的契约，不得漂移。"""

from datetime import datetime, timezone

from app.db.base import Base, engine
from app.models.mastery import MasteryUnit, ReviewCard, ReviewLog, UnitItem


def test_tables_exist():
    for table in ("mastery_units", "unit_items", "review_cards", "review_logs"):
        assert table in Base.metadata.tables


def test_unit_roundtrip():
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        u = MasteryUnit(
            source_type="paper",
            source_ref="paper:1",
            title="DPO 方法精读",
            skill_ids='["DPO"]',
            day_seq=23,
            generation_mode="rule",
            content_hash="abc123",
            status="ready",
            created_at=datetime.now(timezone.utc),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        item = UnitItem(
            unit_id=u.id,
            kind="quiz_q",
            body="DPO 绕过了什么？",
            answer="显式奖励模型",
            rationale="Bradley-Terry 隐式奖励",
        )
        card = ReviewCard(
            source_item_id=None,
            source="concept",
            front="DPO 核心思想",
            back="单目标函数替代 RM+RL",
            due_at=datetime.now(timezone.utc),
            interval_days=1.0,
            ef=2.5,
            lapse_count=0,
            good_streak=0,
            card_status="active",
            created_at=datetime.now(timezone.utc),
        )
        db.add_all([item, card])
        db.commit()
        log = ReviewLog(
            card_id=card.id,
            rating="good",
            reviewed_at=datetime.now(timezone.utc),
            duration_seconds=12,
        )
        db.add(log)
        db.commit()
        assert item.id and card.id and log.id
        assert item.is_verified is False
        db.delete(log); db.delete(card); db.delete(item); db.delete(u)
        db.commit()
