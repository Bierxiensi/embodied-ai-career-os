"""Milestone API 测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_project(name="M Test Project"):
    resp = client.post("/api/projects", json={
        "name": name, "goal": "TG", "status": "active", "current_version": "V0",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def test_create_milestone():
    """POST /api/projects/{id}/milestones 创建里程碑。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 Control", "goal": "topic 通信",
        "status": "in_progress", "sort_order": 1,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["title"] == "ROS2 Control"


def test_patch_milestone():
    """PATCH /api/milestones/{id} 更新里程碑。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "M", "goal": "G", "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    resp = client.patch(f"/api/milestones/{mid}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


def test_delete_milestone():
    """DELETE /api/milestones/{id} 删除里程碑。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "M", "goal": "G", "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    resp = client.delete(f"/api/milestones/{mid}")
    assert resp.status_code == 200
    # 确认项目详情中不再包含该里程碑
    resp = client.get(f"/api/projects/{pid}")
    milestone_ids = [m["id"] for m in resp.json()["data"]["milestones"]]
    assert mid not in milestone_ids


def test_generate_tasks_from_milestone():
    """POST /api/milestones/{id}/tasks 从里程碑生成任务。"""
    pid = _create_project("Gen Test")
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 基础", "goal": "topic 通信 + publisher/subscriber",
        "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    resp = client.post(f"/api/milestones/{mid}/tasks", json={
        "available_minutes": 120,
        "skills": [
            {"name": "ROS2", "level": 1, "target": 4},
            {"name": "Python", "level": 4, "target": 5},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    # 生成的任务应关联 milestone
    for task in data["data"]:
        assert task["milestone_id"] == mid

    # 生成任务后，milestone 状态应变为 needs_baseline
    resp = client.get(f"/api/projects/{pid}")
    milestone = [m for m in resp.json()["data"]["milestones"] if m["id"] == mid][0]
    assert milestone["status"] == "needs_baseline"


def test_generate_tasks_idempotent():
    """第二次生成任务应返回已有任务，不重复创建（BUG 1 回归测试）。"""
    pid = _create_project("Idempotent Test")
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 基础", "goal": "topic 通信 + publisher/subscriber",
        "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    payload = {
        "available_minutes": 120,
        "skills": [{"name": "ROS2", "level": 1, "target": 4}],
    }
    r1 = client.post(f"/api/milestones/{mid}/tasks", json=payload)
    assert r1.status_code == 200
    ids1 = [t["id"] for t in r1.json()["data"]]

    r2 = client.post(f"/api/milestones/{mid}/tasks", json=payload)
    assert r2.status_code == 200
    ids2 = [t["id"] for t in r2.json()["data"]]

    # 幂等：返回的任务 id 完全一致，未新建
    assert len(ids1) > 0
    assert ids1 == ids2

    # 幂等：第二次调用不改变 milestone 状态（仍为 needs_baseline）
    resp = client.get(f"/api/projects/{pid}")
    milestone = [m for m in resp.json()["data"]["milestones"] if m["id"] == mid][0]
    assert milestone["status"] == "needs_baseline"
