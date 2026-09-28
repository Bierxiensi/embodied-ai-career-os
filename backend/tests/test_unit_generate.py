# backend/tests/test_unit_generate.py
"""懒生成：打开才生成、sha256 缓存、Mock 降级 rule 且标注可见。"""

from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.models.mastery import MasteryUnit, UnitItem
from app.services.mastery.generate import ensure_unit_content


def _make_unit(db, title="DPO 方法精读", ref="paper:999"):
    u = MasteryUnit(
        source_type="paper", source_ref=ref, title=title,
        skill_ids='["DPO"]', day_seq=None, generation_mode="rule",
        content_hash=None, status="locked",
        created_at=datetime.now(timezone.utc),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_lazy_generate_rule_mode_in_mock_env():
    # conftest 钉死 LLM_PROVIDER=mock → 必须降级 rule 且可见
    db = SessionLocal()
    try:
        u = _make_unit(db)
        items = ensure_unit_content(db, u)
        assert items, "rule 兜底也必须产出内容"
        assert u.generation_mode == "rule"
        assert u.status == "opened"
        assert u.content_hash
        kinds = {i.kind for i in items}
        assert "summary" in kinds and "quiz_q" in kinds
    finally:
        db.query(UnitItem).filter_by(unit_id=u.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.commit()
        db.close()


def test_second_open_hits_cache_no_new_items():
    db = SessionLocal()
    try:
        u = _make_unit(db, ref="paper:998")
        first = ensure_unit_content(db, u)
        second = ensure_unit_content(db, u)
        assert [i.id for i in first] == [i.id for i in second]
        assert db.query(UnitItem).filter_by(unit_id=u.id).count() == len(first)
    finally:
        db.query(UnitItem).filter_by(unit_id=u.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.commit()
        db.close()


def test_rule_content_makes_no_false_upgrade_promise():
    db = SessionLocal()
    try:
        u = _make_unit(db, ref="paper:996")
        items = ensure_unit_content(db, u)
        summary = next(i for i in items if i.kind == "summary")
        assert "自动升级" not in summary.body  # 承诺未兑现即谎言——禁止出现在用户可见文案
        assert "generation_mode=rule" in summary.body
    finally:
        db.query(UnitItem).filter_by(unit_id=u.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.commit()
        db.close()
