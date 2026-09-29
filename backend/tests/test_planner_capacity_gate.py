"""spec §2.4：任务生成前容量预检——超限显式拒绝 + 最短周期建议。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _payload(minutes: int) -> dict:
    return {
        "available_minutes": minutes,
        "skills": [{"name": "DPO", "level": 1, "target": 3}],
        "generator": "rule",
    }


def test_over_budget_request_rejected_explicitly():
    resp = client.post("/api/planner/generate", json=_payload(400))
    body = resp.json()
    assert body["success"] is False
    assert "最短" in (body.get("message") or "")


def test_within_budget_generates_normally():
    resp = client.post("/api/planner/generate", json=_payload(45))
    body = resp.json()
    assert body["success"] is True
