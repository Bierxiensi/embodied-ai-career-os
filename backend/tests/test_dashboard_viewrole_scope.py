"""Dashboard 展示视角（ViewRole）与任务请求范围的解耦 —— Milestone B 收尾验收。

================================================================================
这个文件要证明的一件事
================================================================================
「切换 Dashboard 的展示视角」**不能**改变任何任务请求范围、任务统计或推荐；
任务的默认范围只能由 **CareerMode** 改变。

为什么值得单独写一个测试文件：这类 bug 的形态是"没有报错、数字只是悄悄变了"。
2026-09-10 为了让任务跟随看板视角，``dashboardService`` 曾把 ViewRole 解析成
赛道 key 再 ``getTasks({ trackKey })`` 过滤任务，于是切到「具身智能」视角时
Dashboard 的任务统计变成了**冻结赛道**的进度 —— 违反 PRD §5 F5.2，且与
/jobs、/today 的数字对不上。改动撤销后，如果没有测试钉住，"顺手加回一个
trackKey 过滤"是极其自然的下一次改动。

================================================================================
四道防线（对应四个覆盖点）
================================================================================
1. 接口层：``/api/tasks`` 的 OpenAPI 参数里**不存在**任何 role/view_role 维度 ——
   服务端在结构上没有"按视角换范围"的能力
2. 服务层：唯一权威 ``resolve_task_scope`` / ``select_tasks`` 的签名里没有 role ——
   连误传的机会都没有（它们只认 CareerMode）
3. 行为层：
   a. 两种展示视角发出的请求**逐字相同**（同一份参数、零 role 维度），
      返回的任务 id 集合也相同；
   b. 该集合等于"全量减去冻结赛道"的独立推导结果（差分对照，不重复实现服务逻辑）；
   c. **只有** CareerMode 切换才改变这个集合（job_hunt → long_term_transition
      会把冻结任务放回范围内），且切换本身不改动任何任务记录
4. 前端层（源码护栏）：``dashboardService.ts`` 不得把 trackKey 传进 ``getTasks``，
   且必须用 ``scope: "current_mode"``；全前端不存在"用视角推赛道再查任务"的调用

隔离由 tests/conftest.py 提供（会话级临时库），本文件不自建数据库、不写开发库。
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.target_roles import TARGET_ROLES
from app.db.base import SessionLocal
from app.main import app
from app.models.task import Task
from app.services.action_planning import task_scope as task_scope_module

client = TestClient(app)

_FROZEN = next((r for r in TARGET_ROLES if r.frozen), None)

#: 展示视角的全部取值（与 frontend/src/lib/viewRole.ts 的 ViewRole 一致）
_VIEW_ROLES = ("jobhunt", "embodied")

#: 不允许出现在任务请求参数里的维度名（视角 / 角色）
_FORBIDDEN_PARAM_HINTS = ("role", "view_role", "viewrole", "perspective")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_SRC = _REPO_ROOT / "frontend" / "src"

#: `getTasks({ ... })` 调用形态（到第一个 `}` 为止）——用于源码级护栏
_GET_TASKS_CALL = re.compile(r"getTasks\(\s*\{[^}]*\}", re.DOTALL)
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
#: 行注释：排除 `://`（URL）以免把字符串里的链接当成注释
_LINE_COMMENT = re.compile(r"(?<!:)//[^\n]*")


def _strip_ts_comments(text: str) -> str:
    """去掉 TS/TSX 注释后再做源码扫描。

    必须去注释：我们刻意在 ``dashboardService.ts`` / ``TodayTasks.tsx`` 的文档注释里
    **引用**了被撤销的旧写法（``getTasks({ trackKey })``）来说明为什么不能那么写。
    如果护栏直接扫原始文本，就会把"记录事故的说明文字"当成事故本身 —— 这类
    假阳性会逼着后来人删掉有价值的历史注释。

    局限：这是正则近似，不处理字符串字面量里出现 ``/*`` 的极端情况；
    对本用例（查找一段调用形态）足够，且失败方向是"更宽松"，不会误报。
    """

    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


# ============================================================
# 夹具与工具
# ============================================================


@pytest.fixture
def mode():
    """临时切换当前阶段模式，用例结束后还原。

    必须还原：conftest 的临时库是**会话级**的，本文件切到 long_term_transition
    而不还原，会让同会话里所有断言 job_hunt 口径的用例莫名失败。
    409（当前已是该模式）按成功处理 —— 目标状态已达成。
    """

    original = _current_mode_key()

    def _switch(mode_key: str) -> None:
        resp = client.post(
            "/api/career-mode/switch",
            json={"mode_key": mode_key, "note": "视角解耦测试"},
        )
        assert resp.status_code in (200, 409), resp.text

    try:
        yield _switch
    finally:
        if _current_mode_key() != original:
            client.post(
                "/api/career-mode/switch",
                json={"mode_key": original, "note": "视角解耦测试还原"},
            )


def _current_mode_key() -> str:
    resp = client.get("/api/career-mode")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["current"]["key"]


def _task_ids(query: str = "") -> set[int]:
    """GET /api/tasks 的 id 集合。query 形如 "?scope=current_mode&include_test=true"。"""
    resp = client.get(f"/api/tasks{query}")
    assert resp.status_code == 200, resp.text
    return {t["id"] for t in resp.json()["data"]}


def _create_task(title: str, track_key: str | None) -> int:
    payload: dict = {"title": title, "duration": 30, "status": "todo", "acceptance": ["a"]}
    if track_key is not None:
        payload["track_key"] = track_key
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _delete_task(task_id: int) -> None:
    """仅测试清理：/api/tasks 刻意不提供 DELETE，但自造数据必须收回。"""
    db = SessionLocal()
    try:
        row = db.get(Task, task_id)
        if row is not None:
            db.delete(row)
            db.commit()
    finally:
        db.close()


def _openapi_params(path_suffix: str, method: str) -> set[str]:
    """取某个接口的参数名集合（路径参数 + 查询参数）。"""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, resp.text
    spec = resp.json()

    path_item = next(
        (v for k, v in spec["paths"].items() if k.endswith(path_suffix)), None
    )
    assert path_item is not None, f"OpenAPI 里找不到 {path_suffix}"
    operation = path_item[method]
    return {p["name"] for p in operation.get("parameters", [])}


# ============================================================
# 1. 接口层：任务接口没有"视角"这个维度
# ============================================================


def test_tasks_endpoint_has_no_view_role_dimension():
    """``/api/tasks`` 不得接受任何 role / 视角参数。

    这是最外层的护栏：只要服务端没有这个入参，无论前端怎么改，都不可能
    "按视角换任务范围"。反过来，如果哪天有人加了 ``role`` 参数并默认生效，
    这个用例会立刻失败，迫使改动者显式面对 Milestone B 契约。
    """

    params = _openapi_params("/tasks", "get")

    # 该有的轴必须都在（说明我们取到的是真实参数集合，不是空集）
    for axis in ("project_id", "track_key", "plan_day_id", "scope"):
        assert axis in params, f"/api/tasks 缺少正交轴参数 {axis}，实际：{sorted(params)}"

    offenders = sorted(
        p for p in params if any(hint in p.lower() for hint in _FORBIDDEN_PARAM_HINTS)
    )
    assert offenders == [], (
        f"/api/tasks 出现了视角维度参数 {offenders}：任务范围只能由 CareerMode 决定"
    )


# ============================================================
# 2. 服务层：唯一权威在结构上无法接收视角
# ============================================================


def test_scope_authority_signature_cannot_carry_a_view_role():
    """唯一权威的两个入口签名里只有 CareerMode 相关输入，没有 role。

    比"约定不要传"更强：**根本没有这个形参**，所以不存在"某个调用方忘了约定"
    这一种失效模式。若将来有人给 select_tasks 加 role 形参，这里会失败。
    """

    assert set(inspect.signature(task_scope_module.resolve_task_scope).parameters) == {"db"}
    assert set(inspect.signature(task_scope_module.select_tasks).parameters) == {
        "candidates",
        "scope",
    }

    # 值对象也不带视角信息
    assert set(task_scope_module.TaskScope.__dataclass_fields__) == {
        "mode_key",
        "mode_name",
        "active_track_keys",
        "frozen_track_keys",
        "is_track_scoped",
        "scope_reason",
    }


# ============================================================
# 3. 行为层：视角无关、模式有关
# ============================================================


def test_two_view_roles_yield_an_identical_task_request(mode):
    """两种展示视角发出的任务请求**逐字相同**，返回范围也相同。

    做法：把"某个视角会发出的请求"建模成一份参数表。因为 ViewRole 是纯前端
    概念，两个视角的参数表必须完全一致（唯一的差异只会是 URL 的 ``?role=``，
    那是页面状态，不是任务请求的一部分）。再实际发两次请求，断言 id 集合一致。

    这里刻意**不**断言"两个视角各自过滤到不同赛道" —— 那正是被撤销的旧行为。
    """

    mode("job_hunt")

    def _request_params_for(view_role: str) -> dict:
        assert view_role in _VIEW_ROLES
        # Dashboard 的任务请求：统一默认范围，不带任何赛道 / 视角条件。
        # 两个视角共用这一个构造，因此参数表必然相同 —— 这就是"逐字相同"的含义。
        return {"scope": "current_mode", "include_test": "true"}

    params_by_role = {r: _request_params_for(r) for r in _VIEW_ROLES}
    assert params_by_role["jobhunt"] == params_by_role["embodied"]
    assert not any(
        hint in k.lower()
        for k in params_by_role["jobhunt"]
        for hint in _FORBIDDEN_PARAM_HINTS
    )

    # 参数表相同 → 请求相同 → 服务端返回不可能不同
    role_ranges = {}
    for role, params in params_by_role.items():
        query = "?" + "&".join(f"{k}={v}" for k, v in params.items())
        role_ranges[role] = _task_ids(query)

    assert role_ranges["jobhunt"] == role_ranges["embodied"], (
        "两种展示视角拿到了不同的任务范围 —— 视角又变成任务策略开关了"
    )

    # 再确认真实请求里没有 role 维度（防止有人"顺手"加上）
    resp = client.get("/api/tasks?scope=current_mode&role=embodied&include_test=true")
    assert resp.status_code == 200, resp.text
    assert {t["id"] for t in resp.json()["data"]} == role_ranges["jobhunt"], (
        "传入 role 竟然改变了任务范围：说明服务端开始按视角过滤了"
    )


def test_current_mode_range_matches_independent_derivation(mode):
    """``scope=current_mode`` 的范围 = 全量减去冻结赛道（差分对照）。

    不重复实现服务内部逻辑：用 ``scope=all`` 拿全量，按 target_roles 的冻结集合
    手工分堆，再看 ``scope=current_mode`` 是否给出同一堆。这样既能验证口径正确，
    也顺带证明"冻结赛道被排除"这条规则没有在别处被改写成白名单制。
    """

    if _FROZEN is None:
        pytest.skip("当前配置没有冻结赛道，无法验证排除口径")

    mode("job_hunt")

    raw = client.get("/api/tasks?include_test=true").json()["data"]
    assert raw, "临时库里应当有任务种子"

    frozen_keys = {r.key for r in TARGET_ROLES if r.frozen}
    expected_included = {t["id"] for t in raw if t["track_key"] not in frozen_keys}

    assert _task_ids("?scope=current_mode&include_test=true") == expected_included

    # 哨兵任务：确认冻结赛道**确实**被排除（而不是恰好库里没有冻结任务）
    sentinel = _create_task("视角解耦 · 冻结赛道哨兵", _FROZEN.key)
    try:
        assert sentinel not in _task_ids("?scope=current_mode&include_test=true")
        assert sentinel in _task_ids("?include_test=true"), (
            "scope=all 必须是原始全量（冻结任务仍在），否则是默认范围被偷改"
        )
    finally:
        _delete_task(sentinel)


def test_only_career_mode_switch_changes_the_range(mode):
    """只有切换 CareerMode 才允许改变任务范围，且切换不触碰任务记录。

    长期转型模式当前没有冻结赛道 → 冻结任务回到范围内，范围**变大**。
    这证明"范围可变"这条通路是活的、且唯一入口是 CareerMode。
    """

    if _FROZEN is None:
        pytest.skip("当前配置没有冻结赛道，模式间不会产生范围差异")

    from app.services.career_mode.presets import LONG_TERM_TRANSITION_MODE_KEY

    mode("job_hunt")
    sentinel = _create_task("视角解耦 · 模式切换哨兵", _FROZEN.key)

    try:
        job_hunt_range = _task_ids("?scope=current_mode&include_test=true")
        assert sentinel not in job_hunt_range, "job_hunt 模式应排除冻结赛道任务"

        # 范围只读：全库指纹在切换前后必须一致
        fingerprint_before = {
            (t["id"], t["title"], t["track_key"], t["status"])
            for t in client.get("/api/tasks?include_test=true").json()["data"]
        }

        mode(LONG_TERM_TRANSITION_MODE_KEY)
        long_term_range = _task_ids("?scope=current_mode&include_test=true")

        assert sentinel in long_term_range, (
            "long_term_transition 未限制赛道，冻结任务必须回到默认范围"
        )
        assert job_hunt_range < long_term_range, (
            "范围差异只应来自冻结集合：job_hunt 范围必须是长期范围的真子集"
        )

        fingerprint_after = {
            (t["id"], t["title"], t["track_key"], t["status"])
            for t in client.get("/api/tasks?include_test=true").json()["data"]
        }
        assert fingerprint_after == fingerprint_before, (
            "切换 CareerMode 改动了任务记录（PRD F5.3：隐藏不等于删除）"
        )
    finally:
        _delete_task(sentinel)


# ============================================================
# 4. 前端层：源码护栏
# ============================================================


def test_dashboard_service_does_not_feed_view_role_into_task_query():
    """``dashboardService.ts`` 必须用统一默认范围取任务，且不传 trackKey。

    这是对本次修复的直接机器化检查。源码级的护栏比"跑一遍页面看数字"可靠：
    数字碰巧相等很容易被误判为通过，而这里检查的是**代码里有没有那条通路**。
    """

    src = (_FRONTEND_SRC / "services" / "dashboardService.ts").read_text(encoding="utf-8")

    # 必须走 CareerMode 口径
    assert 'scope: "current_mode"' in src, (
        "dashboardService 未使用统一默认范围（scope: current_mode）取任务"
    )

    # 注释里必须写明视角的边界（本轮要求 #4：命名/注释明确 ViewRole 是展示视角）
    for phrase in ("展示视角", "CareerMode"):
        assert phrase in src, f"dashboardService 文档注释缺少边界说明关键词：{phrase}"

    # 关键：**代码**（去注释后）里不得再把视角解析结果当查询条件
    code = _strip_ts_comments(src)
    get_tasks_calls = _GET_TASKS_CALL.findall(code)
    assert get_tasks_calls, "没有找到 getTasks 调用，检查方式需要更新"
    for call in get_tasks_calls:
        assert "trackKey" not in call, (
            f"dashboardService 又把 trackKey 传给了 getTasks：{call.strip()}"
        )

    # 展示口径的解析函数仍然存在（它只服务雷达 / 标题 / 就绪度）
    assert "function resolveTrack" in src


def test_no_view_role_driven_task_query_anywhere_in_frontend():
    """全前端搜不到"用视角赛道去查任务"的调用形态。

    覆盖未来新增页面的情况：只要有人**在代码里**写了 ``getTasks({ trackKey })``，
    说明又把展示视角接到了任务范围上，本用例立即失败。
    扫描前先去掉注释 —— 历史说明文字里会引用这个旧写法（见 _strip_ts_comments）。
    """

    offenders: list[str] = []
    for path in _FRONTEND_SRC.rglob("*.ts*"):
        code = _strip_ts_comments(path.read_text(encoding="utf-8", errors="ignore"))
        for call in _GET_TASKS_CALL.findall(code):
            if "trackKey" in call:
                offenders.append(f"{path.relative_to(_REPO_ROOT)}: {call.strip()}")

    assert offenders == [], (
        "存在用赛道过滤任务列表的调用（视角/赛道不得决定任务范围）：\n  "
        + "\n  ".join(offenders)
    )
