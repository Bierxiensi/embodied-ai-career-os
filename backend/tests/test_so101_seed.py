"""SO101 V0 种子数据验证。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_so101_project_exists():
    """种子数据中 SO101 项目存在。"""
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    projects = resp.json()["data"]
    so101 = [p for p in projects if "SO101" in p["name"]]
    assert len(so101) > 0


def test_so101_v0_milestone():
    """V0 里程碑目标应包含 Mujoco 仿真关键词。"""
    resp = client.get("/api/projects")
    so101 = [p for p in resp.json()["data"] if "SO101" in p["name"]][0]
    resp = client.get(f"/api/projects/{so101['id']}")
    milestones = resp.json()["data"]["milestones"]
    v0 = [m for m in milestones if m["version"] == "V0"][0]
    # V0 不应是空的 generic 任务
    assert len(v0["goal"]) > 5
    assert "mujoco" in v0["goal"].lower() or "仿真" in v0["goal"]


def test_decompose_mujoco_milestone():
    """Mujoco 关键词目标应拆解为有意义的子任务。"""
    from app.api.milestones import _decompose_milestone

    tasks = _decompose_milestone("mujoco 仿真机械臂控制", 120)
    assert len(tasks) >= 2
    # 任务应包含 Mujoco 相关关键词
    titles = " ".join(t["title"] for t in tasks)
    assert "模型" in titles or "mujoco" in titles.lower()


def test_mujoco_skill_in_seed():
    """种子数据应包含 Mujoco Simulation 技能。"""
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    skills = resp.json()["data"]
    skill_names = [s["name"].lower() for s in skills]
    assert any("mujoco" in name for name in skill_names), (
        f"Mujoco Simulation 技能缺失: {skill_names}"
    )
