"""任务赛道口径（Milestone B）测试 —— 阶段驱动的默认视图。

================================================================================
被验收的东西
================================================================================
一个服务模块、两个消费方：

    services/action_planning/task_scope.py   ← 唯一权威实现（resolve / select）
        ↑                    ↑
    /api/job-hunt       /api/plan/today

验收的核心命题不是"某个数字对不对"，而是**口径只能有一份**：
任何一处复制 ``track_key`` 判断，两处就会在改 target_roles.py 或改模式策略后
各说各话。因此本文件既测行为，也测"同源"。

================================================================================
本文件对应的 7 个覆盖点
================================================================================
1. 纯服务层分类是全函数（None / 空串 / 冻结 / 其他），且生效赛道派生自
   target_roles.py —— 不硬编码清单
2. job_hunt 模式：冻结赛道任务被排除，计数与列表同源，每项带 active/frozen/unclassified
3. 未归类（track_key IS NULL）历史任务**保留**在默认视图并标记（PRD F5.4）
4. 口径只读：切换模式前后任务表内容指纹完全一致（PRD F5.3 隐藏不等于删除）
5. long_term_transition：冻结集为空 → 不排除任何任务，且给出 scope_reason 说明
6. 两个路由同源：/api/plan/today 与 /api/job-hunt 用同一个 scope；课程日任务
   同样遵守赛道口径（当前 30 天课程恒为 llm/vlm，故实际是恒等变换，已显式钉住）
7. 向后兼容契约：原有顶层字段与 items 字段一个没少，只新增字段，仍是 {data} 包裹

隔离由 tests/conftest.py 提供（会话级临时库），本文件不自建数据库、不写开发库。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.plan_30d import PLAN_30D
from app.core.target_roles import TARGET_ROLES
from app.db.base import SessionLocal
from app.main import app
from app.models.plan_day import PlanDay
from app.models.task import Task
from app.services.action_planning.task_scope import (
    TaskScope,
    TaskTrackScope,
    resolve_task_scope,
)

client = TestClient(app)

# 从配置派生，避免写死赛道名 —— 改 target_roles.py 时测试自动跟随
_ACTIVE = next((r for r in TARGET_ROLES if not r.frozen), None)
_FROZEN = next((r for r in TARGET_ROLES if r.frozen), None)

# 对照用样例口径：与库无关，纯值对象（覆盖点 1 用）
_SAMPLE_SCOPE = TaskScope(
    mode_key="sample",
    mode_name="样例阶段",
    active_track_keys=("llm",),
    frozen_track_keys=("embodied",),
    is_track_scoped=True,
    scope_reason="样例口径",
)

_ORIGINAL_TOP_LEVEL = {
    "career",
    "offer_deadline",
    "days_left",
    "target_roles",
    "skill_gaps",
    "job_pool",
    "job_project",
    "tasks",
    "applications",
}
_ORIGINAL_TASK_ITEM = {
    "id",
    "title",
    "skill_name",
    "status",
    "duration",
    "objective",
}


# ============================================================
# 夹具与工具
# ============================================================


@pytest.fixture(scope="module", autouse=True)
def _seed_plan_days():
    """建本文件需要的课程日（幂等：按 seq 存在即跳过）。

    conftest 的 init_db() **不灌 plan_days**（那是 scripts/seed_plan_30d.py 的
    职责），所以凡是碰 /api/plan/today 的测试文件都得自备少量课程日 ——
    沿用 test_plan_api.py / test_p2_evidence_loop.py 既有范式，只建不删，
    避免污染同会话的其他模块。
    """

    db = SessionLocal()
    try:
        existing = {d.seq for d in db.query(PlanDay).all()}
        for seq in (1, 2):
            if seq in existing:
                continue
            db.add(
                PlanDay(
                    seq=seq,
                    phase=1,
                    phase_name="口径测试周",
                    title=f"口径测试课程日 {seq}",
                    theme="Transformer",
                    objectives=["目标"],
                    acceptance=["验收"],
                    interview_topics=["面试题"],
                    resources=["Hugging Face LLM Course"],
                    est_minutes=360,
                    track_key="llm",
                )
            )
        db.commit()
    finally:
        db.close()

    yield


@pytest.fixture
def mode():
    """临时切换当前阶段模式，用例结束后还原。

    为什么必须还原：conftest 的临时库是**会话级**的。一个文件把当前模式改成
    ``long_term_transition`` 而不还原，后面所有断言 job_hunt 口径的测试都会
    莫名其妙失败 —— 这类"测试互相污染"比断言写错更难排查。

    409（当前已是该模式）按"切换成功"处理：语义上目标状态已达成，
    报错只说明我们不需要写历史记录，不该让用例失败。
    """

    original = _current_mode_key()

    def _switch(mode_key: str) -> dict:
        resp = client.post(
            "/api/career-mode/switch",
            json={"mode_key": mode_key, "note": "口径测试"},
        )
        assert resp.status_code in (200, 409), resp.text
        return _board()

    try:
        yield _switch
    finally:
        if _current_mode_key() != original:
            client.post(
                "/api/career-mode/switch",
                json={"mode_key": original, "note": "口径测试还原"},
            )


def _current_mode_key() -> str:
    resp = client.get("/api/career-mode")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["current"]["key"]


def _board() -> dict:
    """GET /api/job-hunt 的 data。"""
    resp = client.get("/api/job-hunt")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _today(day: int) -> dict:
    """GET /api/plan/today?day=N 的 data。"""
    resp = client.get(f"/api/plan/today?day={day}")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _day_id(seq: int) -> int:
    resp = client.get("/api/plan")
    assert resp.status_code == 200, resp.text
    day = next((d for d in resp.json()["data"] if d["seq"] == seq), None)
    assert day is not None, f"课程日 Day {seq} 不存在（种子未播？）"
    return day["id"]


def _create_task(title: str, track_key: str | None, plan_day_id: int | None = None) -> int:
    """建一条任务并返回 id。source 走默认 "user"（不是 test），
    这样 /api/plan/today 的 source != 'test' 过滤不会把它挡掉。"""
    payload: dict = {
        "title": title,
        "duration": 30,
        "status": "todo",
        "acceptance": ["a"],
    }
    if track_key is not None:
        payload["track_key"] = track_key
    if plan_day_id is not None:
        payload["plan_day_id"] = plan_day_id

    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _delete_task(task_id: int) -> None:
    """按 id 物理删除一条任务（仅测试清理用）。

    走 ORM 而不是接口：``/api/tasks`` 刻意不提供 DELETE（历史任务要留给 Reviewer），
    但测试自己造的数据必须能收回 —— 否则同会话的其他模块会看到一条凭空多出来的
    "冻结赛道 · Day1"任务，排查起来毫无线索。
    """

    db = SessionLocal()
    try:
        row = db.get(Task, task_id)
        if row is not None:
            db.delete(row)
            db.commit()
    finally:
        db.close()


def _task_fingerprint() -> set[tuple]:
    """全库任务内容指纹（含 source=test）。

    用指纹而不是"条数"：口径 bug 最阴的形态是**删掉/改掉了某个字段**而已
    总数不变。指纹把 id / 标题 / 赛道 / 来源一起纳入比对。
    """
    resp = client.get("/api/tasks?include_test=true")
    assert resp.status_code == 200, resp.text
    return {
        (t["id"], t["title"], t["track_key"], t["status"], t["source"])
        for t in resp.json()["data"]
    }


# ============================================================
# 1. 服务层分类：全函数 + 生效赛道派生自配置
# ============================================================


def test_classify_covers_every_case():
    """classify 必须是全函数：三种取值覆盖全部输入，调用方无需再兜底分支。"""

    # 冻结赛道 → frozen（唯一被排除的一类）
    assert _SAMPLE_SCOPE.classify("embodied") is TaskTrackScope.FROZEN

    # 已归类且未冻结 → active
    assert _SAMPLE_SCOPE.classify("llm") is TaskTrackScope.ACTIVE
    # 不在声明集合里、也没被冻结的赛道 → 仍算 active（排除制，不是白名单）
    assert _SAMPLE_SCOPE.classify("ai-algo") is TaskTrackScope.ACTIVE

    # 空赛道 → unclassified（历史 / 手写任务，见覆盖点 3）
    assert _SAMPLE_SCOPE.classify(None) is TaskTrackScope.UNCLASSIFIED
    assert _SAMPLE_SCOPE.classify("") is TaskTrackScope.UNCLASSIFIED
    # 只有空白的赛道视为未归类，而不是一个真的叫 " " 的赛道
    assert _SAMPLE_SCOPE.classify("   ") is TaskTrackScope.UNCLASSIFIED

    # includes 与 classify 必须同源（一个是列表口径，一个是标注口径）
    for track in ("embodied", "llm", "ai-algo", None, ""):
        assert _SAMPLE_SCOPE.includes(track) is (
            _SAMPLE_SCOPE.classify(track) is not TaskTrackScope.FROZEN
        ), track


def test_unfrozen_track_is_never_hidden_even_if_undeclared():
    """排除制（而非白名单制）的护栏：未在 active_track_keys 里声明的赛道
    不得被静默隐藏 —— 否则新增赛道 / 配置漂移时会有任务凭空消失。"""

    scope = TaskScope(
        mode_key="m",
        mode_name="m",
        active_track_keys=("llm",),
        frozen_track_keys=("embodied",),
        is_track_scoped=True,
        scope_reason="x",
    )
    # 不在 active 声明里，但也没冻结 → 必须保留
    assert scope.includes("vlm") is True
    assert scope.includes("brand-new-track") is True


def test_resolve_task_scope_derives_policy_from_target_roles(mode):
    """生效/冻结赛道必须派生自 target_roles.py，不得在模式配置里再抄一份清单。"""

    mode("job_hunt")
    db = SessionLocal()
    try:
        scope = resolve_task_scope(db)
    finally:
        db.close()

    assert set(scope.active_track_keys) == {r.key for r in TARGET_ROLES if not r.frozen}
    assert set(scope.frozen_track_keys) == {r.key for r in TARGET_ROLES if r.frozen}
    assert scope.mode_key == "job_hunt"
    # is_track_scoped 与冻结集合同源，不可能出现"标记已限缩但排除集为空"
    assert scope.is_track_scoped == bool(scope.frozen_track_keys)


# ============================================================
# 2. job_hunt 模式：冻结排除 + 三分类标注 + 计数同源
# ============================================================


def test_job_hunt_scope_marks_each_item(mode):
    """每项都带 scope，取值只能是三个之一；冻结任务既不在 items 也不在标注里。"""

    if _FROZEN is None or _ACTIVE is None:
        pytest.skip("当前配置没有『已冻结 + 未冻结』的赛道组合，无法验证排除口径")

    mode("job_hunt")
    frozen_id = _create_task("口径 · 冻结赛道任务", _FROZEN.key)
    active_id = _create_task("口径 · 生效赛道任务", _ACTIVE.key)

    tasks = _board()["tasks"]
    by_id = {t["id"]: t for t in tasks["items"]}

    assert frozen_id not in by_id, "冻结赛道任务不得出现在默认视图 items 里"
    assert active_id in by_id
    assert by_id[active_id]["scope"] == TaskTrackScope.ACTIVE.value
    # 前端要判断"这条属于哪个赛道"，必须拿到 track_key 本身
    assert by_id[active_id]["track_key"] == _ACTIVE.key

    # 三分类是全函数，落到 items 上不得出现第四个值
    assert {t["scope"] for t in tasks["items"]} <= {
        TaskTrackScope.ACTIVE.value,
        TaskTrackScope.UNCLASSIFIED.value,
    }

    # 被排除任务可查看（PRD F5.3），且它的 scope 恒为 frozen
    excluded_ids = {t["id"] for t in tasks["frozen_items"]}
    assert frozen_id in excluded_ids, "被排除的任务必须仍能看见，而不是消失"
    assert all(t["scope"] == TaskTrackScope.FROZEN.value for t in tasks["frozen_items"])


def test_job_hunt_counts_are_same_source_as_list(mode):
    """计数与列表必须同源 —— 项目里出现过的截断 bug（报 16 却只有 12）
    在同类改造中极易复现，这里把不变量钉死。"""

    mode("job_hunt")
    tasks = _board()["tasks"]
    items = tasks["items"]
    scope = tasks["scope"]

    assert tasks["total"] == len(items)
    assert tasks["done"] == sum(1 for t in items if t["status"] == "done")
    assert tasks["doing"] == sum(1 for t in items if t["status"] == "doing")
    assert tasks["todo"] == sum(1 for t in items if t["status"] == "todo")

    # 视图级口径与条目级列表同源
    assert scope["included"] == tasks["total"]
    assert scope["frozen_excluded"] == len(tasks["frozen_items"])
    assert tasks["frozen_excluded"] == len(tasks["frozen_items"])
    assert scope["unclassified"] == tasks["unclassified"]
    assert scope["unclassified"] == sum(
        1 for t in items if t["scope"] == TaskTrackScope.UNCLASSIFIED.value
    )


# ============================================================
# 3. 未归类历史任务：保留 + 标记（PRD F5.4）
# ============================================================


def test_unclassified_task_stays_visible_and_is_marked(mode):
    """track_key 为空的是一条历史 / 手写任务。它必须继续显示，只被标记
    「未归类」—— 静默隐藏等于篡改历史。"""

    mode("job_hunt")
    before = _board()["tasks"]["unclassified"]
    unclassified_id = _create_task("口径 · 未归类历史任务", None)

    tasks = _board()["tasks"]
    by_id = {t["id"]: t for t in tasks["items"]}

    assert unclassified_id in by_id, "未归类任务必须保留在默认视图（PRD F5.4）"
    assert by_id[unclassified_id]["scope"] == TaskTrackScope.UNCLASSIFIED.value
    assert by_id[unclassified_id]["track_key"] is None
    # 增量断言：新增 1 条未归类 → 计数 +1（不用绝对行数，会话库里有其他测试的数据）
    assert tasks["unclassified"] == before + 1


# ============================================================
# 4. 口径只读：切换模式不触碰任何任务（PRD F5.3）
# ============================================================


def test_switching_mode_does_not_touch_tasks(mode):
    """来回切模式，全库任务指纹必须一模一样：不删、不改、不动。

    这是对用户承诺「切换阶段不会删除/修改/隐藏任何任务记录」的机器化验证 ——
    只看响应字段是不够的，因为最坏的情况是"响应少了几条、库里也没了"。
    用 4 个字段一起比对，能抓住"只改了 track_key 把任务挪出视图"这类隐蔽改法。
    """

    if _FROZEN is None:
        pytest.skip("当前配置没有冻结赛道，切换模式不产生口径差异")

    mode("job_hunt")
    _create_task("口径 · 指纹哨兵", _FROZEN.key)
    baseline = _task_fingerprint()
    assert baseline, "临时库里应当已有任务（init_db 播种）"

    from app.services.career_mode.presets import LONG_TERM_TRANSITION_MODE_KEY

    mode(LONG_TERM_TRANSITION_MODE_KEY)
    assert _task_fingerprint() == baseline, "切到长期模式后任务被改动了"

    mode("job_hunt")
    assert _task_fingerprint() == baseline, "切回求职模式后任务被改动了"


# ============================================================
# 5. long_term_transition：空冻结集 = 不排除，且有说明
# ============================================================


def test_long_term_mode_shows_everything_with_reason(mode):
    """长期模式尚未定义赛道策略 → 不排除任何任务，并说明"暂未限制赛道"。

    这里刻意**不**断言"长期模式应当显示具身任务"：具身赛道当前在
    target_roles.py 里是冻结的，那是求职模式的策略。本用例只钉住
    "空冻结集 ⇒ 零排除"这条结构性结论。
    """

    from app.services.career_mode.presets import LONG_TERM_TRANSITION_MODE_KEY

    mode("job_hunt")
    all_task_count = len(client.get("/api/tasks?include_test=true").json()["data"])

    tasks = mode(LONG_TERM_TRANSITION_MODE_KEY)["tasks"]

    assert tasks["frozen_excluded"] == 0, "长期模式不得排除任何任务"
    assert tasks["frozen_items"] == []
    # total 应当等于全库任务数（长期模式 = 全量视图）
    assert tasks["total"] == all_task_count

    scope = tasks["scope"]
    assert scope["mode_key"] == LONG_TERM_TRANSITION_MODE_KEY
    assert scope["is_track_scoped"] is False
    assert scope["frozen_track_keys"] == []
    # "展示全部"必须给出原因，否则看起来像口径失效
    assert "暂未限制赛道" in scope["scope_reason"], scope["scope_reason"]

    # 每项仍被分类（active / unclassified），不是"分类字段消失"
    assert {t["scope"] for t in tasks["items"]} <= {
        TaskTrackScope.ACTIVE.value,
        TaskTrackScope.UNCLASSIFIED.value,
    }


# ============================================================
# 6. 两个消费方同源 + 课程日口径
# ============================================================


def test_today_and_board_share_the_same_scope(mode):
    """/api/plan/today 与 /api/job-hunt 必须报出同一个口径 —— 这是"只实现一次"
    在接口层的可观测证据。两个页面数字打架时，用户无从判断谁可信。"""

    mode("job_hunt")
    board_scope = _board()["tasks"]["scope"]
    today_scope = _today(1)["task_scope"]

    assert today_scope is not None, "/today 必须返回口径，否则无法解释总数变化"
    assert today_scope["mode_key"] == board_scope["mode_key"]
    assert today_scope["is_track_scoped"] == board_scope["is_track_scoped"]
    assert today_scope["frozen_track_keys"] == board_scope["frozen_track_keys"]
    assert today_scope["active_track_keys"] == board_scope["active_track_keys"]


def test_plan_today_excludes_frozen_track_tasks(mode):
    """课程日任务同样遵守赛道口径（本文件在源码注释里的承诺在此被执行）。

    为什么课程日也要过滤：今日施工单回答的是"今天该干什么"。若看板排除了冻结
    赛道、今日页却把它列成待办，冻结赛道就还在占用学习时间 —— 正是要消灭的现象。
    """

    if _FROZEN is None:
        pytest.skip("当前配置没有冻结赛道，无法验证排除口径")

    mode("job_hunt")
    day_id = _day_id(1)
    frozen_id = _create_task("口径 · Day1 冻结赛道", _FROZEN.key, plan_day_id=day_id)

    try:
        today = _today(1)
        task_ids = {t["id"] for t in today["tasks"]}
        excluded_ids = {t["id"] for t in today["excluded_tasks"]}

        assert frozen_id not in task_ids, "冻结赛道任务不得进入今日施工单"
        assert frozen_id in excluded_ids, "被排除的任务必须可查看（PRD F5.3）"

        # /today 的口径计数是**当天范围**的（候选集只含本课程日任务），
        # 与 /job-hunt 的"全库范围"不同 —— 这里把这个差异显式钉住，
        # 免得日后有人拿两个页面的 frozen_excluded 直接比大小。
        scope = today["task_scope"]
        assert scope["included"] == len(task_ids)
        assert scope["frozen_excluded"] == len(excluded_ids)
        assert scope["frozen_excluded"] >= 1
    finally:
        _delete_task(frozen_id)


def test_plan_today_scope_is_identity_on_current_plan(mode):
    """当前 30 天课程的赛道口径是**恒等变换**，且这一点是显式钉住的。

    课程计划的 track_key 只有 llm / vlm（见 core/plan_30d.py），二者都未冻结，
    所以赛道口径不会排除任何课程日任务。把这个事实写成断言有两个作用：
      1. 说明 /today 的改造在当前配置下是安全的（不改变任何既有可见结果）
      2. 一旦有人给课程日挂了冻结赛道，这个用例会失败 —— 迫使改的人**明确**
         决定"这天还该不该出现在今日页"，而不是让行为悄悄变化

    判据用**差分对照**：把"当天非 test 任务"按冻结集合手工分两堆，再看接口是否
    给出同样的两堆。这样既不重复实现服务内部逻辑，也不受同会话其他测试写入影响。
    """

    mode("job_hunt")
    plan_tracks = {d.track_key for d in PLAN_30D if d.track_key}
    frozen = {r.key for r in TARGET_ROLES if r.frozen}
    assert plan_tracks & frozen == set(), (
        f"课程计划出现了冻结赛道 {plan_tracks & frozen}："
        "今日页会因此开始排除任务，请显式更新本用例与相关说明"
    )

    # 用 Day 2，避免与本文件其他用例在 Day 1 造的数据互相干扰
    day_id = _day_id(2)
    sentinel_active = _create_task("口径 · Day2 生效赛道", _ACTIVE.key, plan_day_id=day_id)
    sentinel_plain = _create_task("口径 · Day2 未归类", None, plan_day_id=day_id)

    raw = client.get(f"/api/tasks?plan_day_id={day_id}&include_test=true").json()["data"]
    not_test = [t for t in raw if t["source"] != "test"]
    expected_visible = {t["id"] for t in not_test if t["track_key"] not in frozen}
    expected_hidden = {t["id"] for t in not_test if t["track_key"] in frozen}

    today = _today(2)

    assert {t["id"] for t in today["tasks"]} == expected_visible
    assert {t["id"] for t in today["excluded_tasks"]} == expected_hidden

    # 两个哨兵各自落在正确的一侧
    assert sentinel_active in {t["id"] for t in today["tasks"]}
    assert sentinel_plain in {t["id"] for t in today["tasks"]}, (
        "未归类任务不得被赛道口径排除（PRD F5.4）"
    )


# ============================================================
# 7. 向后兼容契约
# ============================================================


def test_job_hunt_keeps_backward_compatible_contract(mode):
    """原有字段一个不少、items 字段不缩水、仍走 { data } 包裹；新增字段只做追加。

    前端已经（且将来仍会）按老字段渲染，Milestone B 不允许以"口径升级"为由
    改契约形状。
    """

    mode("job_hunt")
    resp = client.get("/api/job-hunt")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert set(body) == {"success", "data", "message"}, "必须保持统一 {data} 包裹"
    assert body["success"] is True

    data = body["data"]
    assert _ORIGINAL_TOP_LEVEL <= set(data), (
        f"顶层字段缺失：{_ORIGINAL_TOP_LEVEL - set(data)}"
    )

    tasks = data["tasks"]
    for item in tasks["items"]:
        assert _ORIGINAL_TASK_ITEM <= set(item), f"item 字段缺失：{item}"

    # Milestone B 的追加字段必须存在，且类型稳定
    for key in ("frozen_excluded", "unclassified", "frozen_items", "scope"):
        assert key in tasks, f"缺少 Milestone B 追加字段 tasks.{key}"
    assert isinstance(tasks["frozen_excluded"], int)
    assert isinstance(tasks["unclassified"], int)
    assert isinstance(tasks["frozen_items"], list)
    assert isinstance(tasks["scope"], dict)


def test_plan_today_adds_optional_scope_fields(mode):
    """/api/plan/today 的新字段是**附加**的：原有字段不变，新字段可缺省。"""

    mode("job_hunt")
    data = _today(1)

    for key in (
        "day",
        "day_index",
        "total_days",
        "calendar_days_elapsed",
        "sprint_start",
        "tasks",
        "completed_tasks",
        "ledger",
    ):
        assert key in data, f"/api/plan/today 原有字段缺失：{key}"

    assert "task_scope" in data
    assert "excluded_tasks" in data
    assert isinstance(data["excluded_tasks"], list)


def test_unknown_mode_switch_is_rejected_without_touching_scope(mode):
    """切到不存在的模式必须 400，且**不改变**当前口径 —— 失败不得留下半成品状态。"""

    mode("job_hunt")
    before_scope = _board()["tasks"]["scope"]

    resp = client.post(
        "/api/career-mode/switch",
        json={"mode_key": "no_such_mode_2026", "note": "口径测试 · 非法切换"},
    )
    assert resp.status_code == 400, resp.text

    assert _board()["tasks"]["scope"] == before_scope
