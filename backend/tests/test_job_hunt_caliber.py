"""求职看板（/api/job-hunt）任务口径回归测试 —— 冻结赛道不得计入待办。

================================================================================
背景（2026-09-11 数据卫生修复）
================================================================================
``/api/job-hunt`` 的任务段此前是：

    tasks = db.query(Task).order_by(Task.id).all()

**全库裸查**。后果：战略 v2.0 明令冻结的具身赛道（`target_roles.py` 中
``frozen=True``）下的任务（ROS2 / Isaac / Sim2Real / VLA 等）被当成"仍在推动
的待办"计入 /jobs 的待办总数。实测 /jobs 显示 23 条待办，其中 8 条属于冻结赛道。

这与 `target_roles.py` 的设计意图直接冲突 —— 注释明写冻结赛道
「不再进入技能缺口的推动列表，不再占用学习时间」。口径 bug 会让人误以为
还有 8 条具身任务要做，正是"在虚构数据上做决策"。

修复：按 ``frozen`` 标记排除对应 `track_key` 的任务（`track_key IS NULL` 的
历史任务保留），并把被排除的条数以 ``tasks.frozen_excluded`` 透明化返回，
让"为什么总数变小了"可解释。

隔离由 tests/conftest.py 提供（会话级临时库），本文件不自建数据库。
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.target_roles import TARGET_ROLES
from app.main import app

client = TestClient(app)

# 从配置派生，避免写死赛道名（改 target_roles.py 时测试自动跟随）
_MAIN = next((r for r in TARGET_ROLES if r.priority == "主攻"), TARGET_ROLES[0])
_FROZEN = next((r for r in TARGET_ROLES if r.frozen), None)


def _create_task(title: str, track_key: str) -> int:
    """建一条指定赛道的任务，返回 id。"""
    resp = client.post("/api/tasks", json={
        "title": title,
        "duration": 30,
        "status": "todo",
        "acceptance": ["a"],
        "track_key": track_key,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _board() -> dict:
    resp = client.get("/api/job-hunt")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ============================================================
# 1. 冻结赛道任务被排除（本次修复的核心断言）
# ============================================================

def test_job_hunt_excludes_frozen_track_tasks():
    """新建一条冻结赛道任务：不出现在 items 里，但计入 frozen_excluded。

    用**增量断言**（前后对比）而非绝对行数 —— 会话共享同一临时库，
    其他测试也会往里写任务。
    """
    if _FROZEN is None:
        return  # 无冻结赛道时该口径无意义

    before = _board()["tasks"]
    base_total = before["total"]
    base_frozen = before["frozen_excluded"]

    frozen_id = _create_task("口径回归 · 冻结赛道任务", _FROZEN.key)
    main_id = _create_task("口径回归 · 主攻赛道任务", _MAIN.key)

    after = _board()["tasks"]
    item_ids = {t["id"] for t in after["items"]}

    # 冻结任务必须被挡在推动列表外
    assert frozen_id not in item_ids, "冻结赛道任务不得出现在 /jobs 待办里"
    # 非冻结任务照常进入
    assert main_id in item_ids, "主攻赛道任务应出现在 /jobs 待办里"

    # 透明化计数正确：新增 1 条冻结任务 → 被排除数 +1
    assert after["frozen_excluded"] == base_frozen + 1, (
        f"frozen_excluded 应从 {base_frozen} 增到 {base_frozen + 1}，"
        f"实际 {after['frozen_excluded']}"
    )
    # 总数只 +1（只多了主攻那条；冻结那条被排除，不进 total）
    assert after["total"] == base_total + 1, (
        f"total 应只 +1（主攻任务），实际 {base_total} → {after['total']}"
    )


# ============================================================
# 2. 不变量：冻结任务池与看板推动列表零交集
# ============================================================

def test_job_hunt_items_disjoint_from_frozen_pool():
    """看板 items 里的任何 id，都不应出现在冻结赛道的任务池中。

    这是比"抽查一条"更强的**全量不变量**：无论库里原本就有多少冻结任务，
    看板都不许漏进来。
    """
    if _FROZEN is None:
        return

    frozen_pool = client.get(f"/api/tasks?track_key={_FROZEN.key}&include_test=true")
    assert frozen_pool.status_code == 200, frozen_pool.text
    frozen_ids = {t["id"] for t in frozen_pool.json()["data"]}

    board_ids = {t["id"] for t in _board()["tasks"]["items"]}

    overlap = frozen_ids & board_ids
    assert not overlap, f"看板混入了冻结赛道任务 id: {sorted(overlap)}"


# ============================================================
# 3. 自洽性：summary 与 items 同源（同类 bug 的历史高发点）
# ============================================================

def test_job_hunt_task_summary_consistent_with_items():
    """total / done / doing / todo 必须与 items 逐条吻合。

    对齐 P4 的教训：summary 与它描述的列表必须同源生成
    （曾出现 pending 截断到 12 却报 16）。这里把不变量钉死。
    """
    tasks = _board()["tasks"]
    items = tasks["items"]

    assert tasks["total"] == len(items), "total 必须等于 items 长度"
    assert tasks["done"] == sum(1 for t in items if t["status"] == "done")
    assert tasks["doing"] == sum(1 for t in items if t["status"] == "doing")
    assert tasks["todo"] == sum(1 for t in items if t["status"] == "todo")
    # 三态应恰好覆盖全部（没有第四种状态混入）
    assert tasks["done"] + tasks["doing"] + tasks["todo"] == tasks["total"]
    # frozen_excluded 是非负整数
    assert isinstance(tasks["frozen_excluded"], int)
    assert tasks["frozen_excluded"] >= 0
