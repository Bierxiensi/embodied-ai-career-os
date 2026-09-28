"""单元网格：30 天脊梁 + 论文 → 单元骨架（确定性，打开才生成内容）。"""

from app.services.mastery.grid import build_unit_specs, sync_grid
from app.db.base import SessionLocal


def test_specs_cover_spine_and_papers():
    specs = build_unit_specs(papers=[(1, "Direct Preference Optimization"), (2, "LoRA: Low-Rank Adaptation")])
    day_seqs = [s["day_seq"] for s in specs if s["day_seq"] is not None]
    assert len(day_seqs) == 30 and sorted(day_seqs) == list(range(1, 31))
    paper_units = [s for s in specs if s["source_type"] == "paper"]
    assert len(paper_units) == 2
    assert paper_units[0]["skill_ids"] == ["DPO"]
    assert paper_units[1]["skill_ids"] == ["LoRA"]


def test_sync_grid_idempotent():
    db = SessionLocal()
    try:
        r1 = sync_grid(db)
        r2 = sync_grid(db)
        assert r2["created"] == 0
        assert r2["total"] == r1["total"]
    finally:
        db.close()
