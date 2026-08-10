"""Project README 自动生成测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_readme_generated_on_completion():
    """项目标记 completed 时自动生成 README。"""
    # 创建项目
    resp = client.post("/api/projects", json={
        "name": "README Test", "goal": "Test README gen",
        "status": "active", "current_version": "V0",
    })
    pid = resp.json()["data"]["id"]

    # 创建并完成一个里程碑
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V0", "title": "唯一里程碑",
        "goal": "完成测试", "status": "in_progress", "sort_order": 0,
    })
    mid = resp.json()["data"]["id"]

    # 从里程碑生成任务并完成
    resp = client.post(f"/api/milestones/{mid}/tasks", json={
        "available_minutes": 60,
        "skills": [{"name": "Python", "level": 4, "target": 5}],
    })
    # 完成里程碑
    client.patch(f"/api/milestones/{mid}", json={"status": "completed"})

    # 标记项目完成
    resp = client.patch(f"/api/projects/{pid}", json={"status": "completed"})
    assert resp.status_code == 200
    data = resp.json()["data"]

    # 应自动生成 README
    assert data["readme"] is not None
    assert len(data["readme"]) > 0
    assert "README Test" in data["readme"]
