"""GitHub API 测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_suggestions_empty():
    resp = client.get("/api/github/suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_confirm_not_found():
    resp = client.post("/api/github/suggestions/nonexistent/confirm", json={"skill": "Python"})
    assert resp.status_code == 404


def test_reject_not_found():
    resp = client.post("/api/github/suggestions/nonexistent/reject")
    assert resp.status_code == 404


def test_manual_sync_without_token():
    """无 GitHub token 时 sync 返回 0。"""
    resp = client.post("/api/github/sync")
    assert resp.status_code == 200
    assert resp.json()["data"]["new_suggestions"] == 0
