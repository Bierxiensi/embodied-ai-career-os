"""任务赛道归属（track_key）+ Planner 视角收敛 测试。

覆盖用户 2026-09-10 反馈的两个问题：
  1. 「任务没有跟随不同的角色看板走」
     → GET /api/tasks?track_key= 过滤；看板按 activeTrack.key 拉任务
  2. 「Agent 生成今日任务不是很明确，没看明白」
     → Planner 请求带 track_key，候选技能收敛到该赛道，响应带回决策细节

测试隔离由 tests/conftest.py 提供（会话级临时库），本文件不自建数据库。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.target_roles import TARGET_ROLES
from app.main import app

client = TestClient(app)

# 从配置派生，避免测试里写死赛道名（改 target_roles.py 即改测试跟随）
_MAIN = next((r for r in TARGET_ROLES if r.priority == "主攻"), TARGET_ROLES[0])
_FROZEN = next((r for r in TARGET_ROLES if r.frozen), None)


def _create_task(title: str, track_key: str | None) -> int:
    payload: dict = {
        "title": title,
        "duration": 30,
        "status": "todo",
        "acceptance": ["a"],
    }
    if track_key is not None:
        payload["track_key"] = track_key
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


# ============================================================
# 1. /api/tasks 赛道过滤
# ============================================================

def test_tasks_filter_by_track_key():
    """track_key 过滤只返回该赛道的任务。"""
    _create_task("赛道过滤 · 主攻任务", _MAIN.key)
    _create_task("赛道过滤 · 冻结任务", _FROZEN.key if _FROZEN else "embodied")

    resp = client.get(f"/api/tasks?track_key={_MAIN.key}")
    assert resp.status_code == 200
    tasks = resp.json()["data"]

    assert tasks, "主攻赛道应有任务"
    assert all(t["track_key"] == _MAIN.key for t in tasks), tasks


def test_tasks_filter_excludes_other_tracks():
    """过滤结果里不应混入其他赛道的任务。"""
    other = next((r for r in TARGET_ROLES if r.key != _MAIN.key), None)
    if other is None:  # 只有一条赛道时该断言无意义
        return

    _create_task("赛道过滤 · 另一条赛道", other.key)

    resp = client.get(f"/api/tasks?track_key={_MAIN.key}")
    tasks = resp.json()["data"]
    assert all(t["track_key"] != other.key for t in tasks)


def test_tasks_include_untracked_flag():
    """include_untracked=true 时未归类（track_key=NULL）的任务也会返回。"""
    _create_task("赛道过滤 · 未归类任务", None)

    without = client.get(f"/api/tasks?track_key={_MAIN.key}").json()["data"]
    with_all = client.get(
        f"/api/tasks?track_key={_MAIN.key}&include_untracked=true"
    ).json()["data"]

    assert any(t["track_key"] is None for t in with_all)
    assert not any(t["track_key"] is None for t in without)
    assert len(with_all) > len(without)


def test_tasks_without_track_key_returns_all():
    """不传 track_key 即全量口径（"全量任务池"计数依赖它）。"""
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    tasks = resp.json()["data"]
    assert len(tasks) > 0


# ============================================================
# 2. Planner 视角收敛 + 决策细节
# ============================================================

def test_planner_scopes_skills_to_frozen_track():
    """带 track_key 时，Planner 只在该赛道的 required_skills 里挑技能。

    这是本次修复的核心：旧实现把全部技能丢给 Planner，它会挑出**全局**最大缺口
    （例如冲刺 LLM 岗位时挑 Sim2Real gap=4），产出的任务与当前视角无关。
    """
    if _FROZEN is None:
        return

    resp = client.post("/api/planner/generate", json={
        "available_minutes": 120,
        "track_key": _FROZEN.key,
        "skills": [],
        "generator": "rule",
        "persist": True,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["track_key"] == _FROZEN.key
    assert data["track_frozen"] is True
    # 选中的技能必须属于该赛道的硬性要求
    assert data["skill"] in _FROZEN.required_skills, (
        f"选中的 {data['skill']} 不在 {_FROZEN.key} 的 required_skills 里"
    )
    # 冻结赛道限时（低强度巩固通道）
    assert data["duration"] <= 45

    # 决策细节齐备，前端结果卡才能解释"为什么是这条"
    assert data["skill_level"] is not None
    assert data["skill_target"] == _FROZEN.required_level
    assert data["gap"] is not None and data["gap"] > 0
    assert data["reason"]
    assert _FROZEN.name in data["reason"]


def test_planner_does_not_leak_cross_track_skill():
    """主攻视角不应产出仅在冻结赛道里的技能任务。"""
    if _FROZEN is None:
        return

    resp = client.post("/api/planner/generate", json={
        "available_minutes": 60,
        "track_key": _MAIN.key,
        "skills": [],
        "generator": "rule",
        "persist": False,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["track_key"] == _MAIN.key
    assert data["skill"] in _MAIN.required_skills
    # 冻结赛道独有的技能绝不能出现在主攻视角的任务里
    frozen_only = set(_FROZEN.required_skills) - set(_MAIN.required_skills)
    assert data["skill"] not in frozen_only


def test_planner_defaults_to_main_track():
    """不传 track_key 时回退「主攻」赛道。"""
    resp = client.post("/api/planner/generate", json={
        "available_minutes": 60,
        "skills": [],
        "generator": "rule",
        "persist": False,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["track_key"] == _MAIN.key
    assert data["track_frozen"] is False


def test_planner_idempotent_reports_reused():
    """同一天同题任务复用而非新建，且响应里能区分（reused 标记）。

    注意：不断言"首次一定是新建" —— 全量套件里其他 Planner 测试可能已经
    在同一条赛道上落过同题任务（会话共享同一临时库），此时首次调用合法地
    就是复用。因此这里只断言**幂等不变量**：两次调用指向同一条记录、
    第二次必为复用、库里不出现第二条同题任务。
    """
    body = {
        "available_minutes": 45,
        "track_key": _MAIN.key,
        "skills": [],
        "generator": "rule",
        "persist": True,
    }

    first = client.post("/api/planner/generate", json=body).json()["data"]
    second = client.post("/api/planner/generate", json=body).json()["data"]

    assert first["task_id"] is not None, "persist=True 应入库"
    assert first["task_id"] == second["task_id"], "同题任务应复用同一条记录"
    assert second["reused"] is True, "第二次必须是复用"
    assert "复用" in second["reason"]

    # 幂等：第二次调用不应新增记录（用增量断言，避免依赖"库里原本有几条"）
    def _same_count() -> int:
        rows = client.get(f"/api/tasks?track_key={_MAIN.key}").json()["data"]
        return sum(
            1 for t in rows
            if t["title"] == first["title"] and t["skill_name"] == first["skill"]
        )

    after_second = _same_count()
    third = client.post("/api/planner/generate", json=body).json()["data"]
    assert third["task_id"] == first["task_id"]
    assert _same_count() == after_second, "重复调用不应新增同题任务"


def test_planner_same_task_title_differs_across_tracks():
    """同名技能跨赛道不误判为重复（track_key 进了幂等键）。

    如 PyTorch 同时属于主攻与冻结赛道 —— 不加赛道维度会把两边误判为同一条。
    """
    if _FROZEN is None:
        return
    shared = set(_MAIN.required_skills) & set(_FROZEN.required_skills)
    if not shared:
        return  # 无交集技能时该场景不存在

    # 直接构造两条同名同技能、仅赛道不同的任务，验证二者共存
    a = _create_task("跨赛道同名任务", _MAIN.key)
    b = _create_task("跨赛道同名任务", _FROZEN.key)
    assert a != b

    main_tasks = client.get(f"/api/tasks?track_key={_MAIN.key}").json()["data"]
    frozen_tasks = client.get(f"/api/tasks?track_key={_FROZEN.key}").json()["data"]

    assert any(t["id"] == a for t in main_tasks)
    assert any(t["id"] == b for t in frozen_tasks)
