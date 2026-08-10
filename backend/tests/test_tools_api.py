"""工具桥接 API 测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_context_endpoint():
    resp = client.get("/api/tools/context")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_prompt_endpoint_task_not_found():
    resp = client.post("/api/tools/prompt", json={"task_id": 99999, "tool": "trae"})
    assert resp.status_code == 404
