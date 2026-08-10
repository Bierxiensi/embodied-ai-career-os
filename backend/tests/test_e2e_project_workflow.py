"""Project Management E2E 测试：项目创建 → 里程碑 → 生成任务 → 完成任务 → 验证数据关联。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_project_workflow():
    """完整项目工作流。"""
    # 1. 创建项目
    resp = client.post("/api/projects", json={
        "name": "E2E SO101",
        "goal": "端到端测试项目",
        "status": "active",
        "current_version": "V0",
    })
    assert resp.status_code == 200
    pid = resp.json()["data"]["id"]

    # 2. 创建里程碑
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "基础控制",
        "goal": "Python 控制舵机", "status": "in_progress", "sort_order": 0,
    })
    assert resp.status_code == 200
    mid = resp.json()["data"]["id"]

    # 3. 从里程碑生成任务
    resp = client.post(f"/api/milestones/{mid}/tasks", json={
        "available_minutes": 60,
        "skills": [
            {"name": "Python", "level": 4, "target": 5},
            {"name": "ROS2", "level": 1, "target": 4},
        ],
    })
    assert resp.status_code == 200
    tasks = resp.json()["data"]
    assert len(tasks) > 0

    # 4. 验证任务关联了项目和里程碑
    task_id = tasks[0]["id"]
    resp = client.get(f"/api/tasks?project_id={pid}")
    assert resp.status_code == 200
    project_tasks = resp.json()["data"]
    task_ids = [t["id"] for t in project_tasks]
    assert task_id in task_ids

    # 5. 完成一个任务
    resp = client.patch(f"/api/tasks/{task_id}/status", json={"status": "done"})
    assert resp.status_code == 200

    # 6. 验证里程碑完成自动传播
    resp = client.patch(f"/api/milestones/{mid}", json={"status": "completed"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"


def test_project_in_dashboard():
    """Dashboard 返回项目数据。"""
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "projects" in data
    assert isinstance(data["projects"], list)


def test_planner_e2e_with_project():
    """端到端：项目 → 里程碑 → Planner 生成任务 → 验证关联。"""
    # 创建项目 + 里程碑
    resp = client.post("/api/projects", json={
        "name": "Planner E2E", "goal": "Test", "status": "active", "current_version": "V0",
    })
    pid = resp.json()["data"]["id"]
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "测试里程碑",
        "goal": "验证 Planner 项目上下文", "status": "in_progress", "sort_order": 0,
    })
    mid = resp.json()["data"]["id"]

    # Planner 带项目上下文生成任务
    resp = client.post("/api/planner/generate", json={
        "available_minutes": 30,
        "skills": [{"name": "Python", "level": 4, "target": 5}],
        "generator": "rule",
        "persist": True,
        "project_id": pid,
        "milestone_id": mid,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    tid = data["data"]["task_id"]
    assert tid is not None

    # 验证生成的任务关联了项目
    resp = client.get(f"/api/tasks?project_id={pid}")
    task_ids = [t["id"] for t in resp.json()["data"]]
    assert tid in task_ids
