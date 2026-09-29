"""作品集组装：每条能力主张背后有证据（spec §2.3 作品集说话）。"""

from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.services.evidence_events import record_evidence_event
from app.services.packaging.portfolio import build_portfolio

client = TestClient(app)


def test_build_portfolio_has_13_sections():
    db = SessionLocal()
    try:
        record_evidence_event(db, "DPO", "comparison_report", "experiment:1")  # L4 造一条硬证据
        out = build_portfolio(db)
        assert len(out["sections"]) == 13
        assert out["evidence_count"] >= 1
        assert "DPO" in out["ready_skills"]
        # 每节都有内容骨架（允许少量节暂无实例，但必须有结构文本）
        for sec in out["sections"]:
            assert sec["name"] and isinstance(sec["content"], str) and len(sec["content"]) > 0
    finally:
        db.close()


def test_assemble_endpoint():
    resp = client.get("/api/portfolio/assemble")
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["sections"]) == 13
