"""Milestone 脚手架字段测试：workspace + required_modifications。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_project(name="Scaffold Test"):
    resp = client.post("/api/projects", json={
        "name": name, "goal": "TG", "status": "active", "current_version": "V0",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def test_patch_and_read_scaffolding_fields():
    """PATCH 写 workspace + required_modifications，GET 能读回。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "ROS2 基础", "goal": "topic 通信",
        "status": "in_progress", "sort_order": 1,
    })
    mid = resp.json()["data"]["id"]

    mods = [
        {"title": "加 launch 文件", "goal": "理解 node 编排",
         "files": ["launch.py"], "verification": "ros2 launch ..."},
    ]

    resp = client.patch(f"/api/milestones/{mid}", json={
        "workspace": "so101/v1_ros2/",
        "required_modifications": mods,
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["workspace"] == "so101/v1_ros2/"
    assert data["required_modifications"] == mods

    # GET 项目详情能读回
    resp = client.get(f"/api/projects/{pid}")
    m = [x for x in resp.json()["data"]["milestones"] if x["id"] == mid][0]
    assert m["workspace"] == "so101/v1_ros2/"
    assert m["required_modifications"][0]["title"] == "加 launch 文件"


def test_scaffolding_fields_default_none():
    """未设置时，workspace/required_modifications 默认为 None。"""
    pid = _create_project()
    resp = client.post(f"/api/projects/{pid}/milestones", json={
        "version": "V1", "title": "M", "goal": "G",
        "status": "in_progress", "sort_order": 1,
    })
    data = resp.json()["data"]
    assert data["workspace"] is None
    assert data["required_modifications"] is None
