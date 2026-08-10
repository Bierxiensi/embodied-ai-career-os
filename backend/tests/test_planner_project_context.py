"""Planner 项目上下文注入测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_project_and_milestone():
    resp = client.post("/api/projects", json={
        "name": "Planner Test", "goal": "Test", "status": "active", "current_version": "V0",
    })
    pid = resp.json()["data"]["id"]
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "ROS2", "goal": "topic 通信",
        "status": "in_progress", "sort_order": 0,
    })
    mid = resp.json()["data"]["id"]
    return pid, mid


def test_planner_with_project_context():
    """Planner 接收 project_id + milestone_id 生成任务。"""
    pid, mid = _create_project_and_milestone()

    resp = client.post("/api/planner/generate", json={
        "available_minutes": 40,
        "skills": [{"name": "ROS2", "level": 1, "target": 4}],
        "generator": "rule",
        "persist": True,
        "project_id": pid,
        "milestone_id": mid,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    task = data["data"]
    assert task["title"]


def test_planner_without_project_context():
    """Planner 无 project 上下文仍正常工作（兼容旧调用）。"""
    resp = client.post("/api/planner/generate", json={
        "available_minutes": 30,
        "skills": [{"name": "Python", "level": 4, "target": 5}],
        "generator": "rule",
        "persist": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["title"]


def test_planner_persist_with_project():
    """Persist=True 时生成的任务关联 project_id 和 milestone_id。"""
    pid, mid = _create_project_and_milestone()

    resp = client.post("/api/planner/generate", json={
        "available_minutes": 40,
        "skills": [{"name": "ROS2", "level": 1, "target": 4}],
        "generator": "rule",
        "persist": True,
        "project_id": pid,
        "milestone_id": mid,
    })
    assert resp.status_code == 200
    task = resp.json()["data"]
    tid = task["task_id"]
    assert tid is not None

    # 验证任务关联了项目
    resp = client.get(f"/api/tasks?project_id={pid}")
    task_ids = [t["id"] for t in resp.json()["data"]]
    assert tid in task_ids
