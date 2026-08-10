"""Dashboard 项目聚合 + Task 项目过滤测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_project(name="Dashboard Test"):
    resp = client.post("/api/projects", json={
        "name": name, "goal": "G", "status": "active", "current_version": "V0",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _create_milestone(pid, version="V0", title="M", goal="G"):
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": version, "title": title, "goal": goal,
        "status": "in_progress", "sort_order": 0,
    })
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def test_tasks_filter_by_project():
    """GET /api/tasks?project_id= 过滤项目关联任务。"""
    pid = _create_project("Filter Test")
    mid = _create_milestone(pid, "V0", "M", "python control")

    # 从里程碑生成任务
    resp = client.post(f"/api/milestones/{mid}/tasks", json={
        "available_minutes": 60,
        "skills": [{"name": "Python", "level": 4, "target": 5}],
    })
    assert resp.status_code == 200

    # 按 project_id 过滤
    resp = client.get(f"/api/tasks?project_id={pid}")
    assert resp.status_code == 200
    tasks = resp.json()["data"]
    assert len(tasks) > 0
    for t in tasks:
        assert t.get("project_id") == pid or t.get("project_id") is None


def test_tasks_without_project_filter():
    """GET /api/tasks 无过滤参数仍返回所有任务。"""
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_dashboard_includes_projects():
    """GET /api/dashboard 返回中包含 projects 字段。"""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "projects" in data["data"]
    projects = data["data"]["projects"]
    assert isinstance(projects, list)
    if projects:
        p = projects[0]
        assert "progress_pct" in p
        assert "milestone_total" in p
