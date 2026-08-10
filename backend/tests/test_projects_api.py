"""Project API 测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_project(name="Test Project"):
    resp = client.post("/api/projects", json={
        "name": name,
        "goal": "Test goal",
        "status": "active",
        "current_version": "V0",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def test_list_projects():
    """GET /api/projects 返回项目列表。"""
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_create_project():
    """POST /api/projects 创建项目。"""
    resp = client.post("/api/projects", json={
        "name": "Test Project",
        "goal": "Test goal",
        "status": "active",
        "current_version": "V0",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Test Project"


def test_get_project():
    """GET /api/projects/{id} 返回项目详情含 milestones。"""
    pid = _create_project("Detail Test")
    resp = client.get(f"/api/projects/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["id"] == pid
    assert "milestones" in data["data"]


def test_patch_project():
    """PATCH /api/projects/{id} 更新项目。"""
    pid = _create_project("Patch Test")
    resp = client.patch(f"/api/projects/{pid}", json={"status": "paused"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "paused"


def test_delete_project():
    """DELETE /api/projects/{id} 删除项目。"""
    pid = _create_project("Delete Test")
    resp = client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 200
    resp = client.get(f"/api/projects/{pid}")
    assert resp.status_code == 404
