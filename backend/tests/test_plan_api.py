"""30 天施工执行台（/api/plan）测试。

覆盖 2026-09-10 的 P0：
  1. 课程脊梁 /api/plan 按 seq 升序返回
  2. 今日施工单 /api/plan/today 回答三个问题
     —— 今天第几天（day_index）、今天干什么（day 内容）、今天做完没有（四件套）
  3. 四件套勾选 / 取消（POST / DELETE /api/plan/artifacts）
  4. 总账口径（30 段代码 / 30 篇笔记 / 30 个 commit / 面试题累计目标〔派生自 engine〕/ 30 个齐全日）
  5. 任务按 plan_day_id 归属到课程日
  6. 边界：day 越界 422、课程日不存在 404、kind 非法 422

测试隔离由 tests/conftest.py 提供（会话级临时库），本文件不自建数据库。
注意：conftest 的 init_db() **不会**灌 plan_days（那是 scripts/seed_plan_30d.py 的职责），
所以本文件自带 autouse 夹具，只建测试需要的少量课程日。
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.plan import _resolve_day_index
from app.core.target_roles import SPRINT_START
from app.db.base import SessionLocal
from app.main import app
from app.models.day_artifact import ARTIFACT_KINDS
from app.models.plan_day import PlanDay

client = TestClient(app)

# 固定种下的课程日（日历当天由 fixture 动态补种，见下）。
_SEEDED_SEQS = (1, 2)


def _calendar_seq() -> int:
    """与 API 同源的日历推导口径（`_resolve_day_index`），即「今天是 Day N」。"""

    return _resolve_day_index(date.today())[0]


def _seeded_seqs() -> set[int]:
    """当前临时库里已存在的课程日 seq。"""

    db = SessionLocal()
    try:
        return {d.seq for d in db.query(PlanDay).all()}
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def _seed_plan_days():
    """建少量课程日供本文件使用（幂等：按 seq 存在即跳过）。

    除固定的 1 / 2 外，还要补种**日历推导当天**：`_today()` 不带参数时走日历口径，
    而日历随墙钟推进（Day 12 → Day 13 → ……）。不补种的话本文件会随日期推移稳定变红
    —— 2026-09-22 修：此前 4 个用例长期因「课程日 Day 13 不存在」失败。
    """

    targets = set(_SEEDED_SEQS) | {_calendar_seq()}

    db = SessionLocal()
    try:
        existing = {d.seq for d in db.query(PlanDay).all()}
        for seq in sorted(targets):
            if seq in existing:
                continue
            db.add(
                PlanDay(
                    seq=seq,
                    phase=1,
                    phase_name="第一周 · 打穿 Transformer",
                    title=f"测试课程日 {seq}",
                    theme="Transformer",
                    objectives=[f"目标 {seq}-1", f"目标 {seq}-2"],
                    acceptance=[f"验收 {seq}-1", f"验收 {seq}-2"],
                    interview_topics=[f"面试题 {seq}-1"],
                    resources=["Hugging Face LLM Course"],
                    est_minutes=360,
                    track_key="llm",
                )
            )
        db.commit()
    finally:
        db.close()

    yield


def _day_id(seq: int) -> int:
    """取课程日的数据库 id。"""

    db = SessionLocal()
    try:
        row = db.query(PlanDay).filter(PlanDay.seq == seq).first()
        assert row is not None, f"Day {seq} 未初始化"
        return row.id
    finally:
        db.close()


def _today(day: int | None = None) -> dict:
    """取今日施工单 data 段。"""

    url = "/api/plan/today" + (f"?day={day}" if day is not None else "")
    resp = client.get(url)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _clear_artifacts(seq: int) -> None:
    """清空**指定课程日**的产出，避免模块内测试互相污染（共享临时库）。

    ⚠️ 必须显式传 seq：`/api/plan/today` 只返回**当天**的 artifacts（按 plan_day_id 过滤），
    不带参数取到的是"日历当天"，拿它去清理别的 day 会**静默变成空操作**。
    —— 2026-09-22 修：此前该 helper 实为 no-op，导致用例间残留 artifact，
    `test_overview_reports_behind_when_incomplete` 被 Day2 的残留四件套算成"已完成"而误报。
    """

    data = _today(day=seq)
    for a in data["artifacts"]:
        client.delete(f"/api/plan/artifacts/{a['id']}")


# ============================================================
# 1. 课程脊梁列表
# ============================================================


def test_plan_list_returns_days_in_seq_order():
    """GET /api/plan 按 seq 升序返回。"""

    resp = client.get("/api/plan")
    assert resp.status_code == 200
    days = resp.json()["data"]

    seqs = [d["seq"] for d in days]
    assert seqs == sorted(seqs), seqs
    assert set(_SEEDED_SEQS).issubset(set(seqs)), seqs

    # 字段契约：前端 PlanDay 依赖这些 key
    sample = next(d for d in days if d["seq"] == 1)
    for key in (
        "id",
        "seq",
        "phase",
        "phase_name",
        "title",
        "theme",
        "objectives",
        "acceptance",
        "interview_topics",
        "resources",
        "est_minutes",
        "track_key",
    ):
        assert key in sample, f"缺少字段 {key}"


# ============================================================
# 2. 今日施工单
# ============================================================


def test_today_resolves_calendar_day():
    """不带参数时按日历推导当天，并回传完整回答三问所需的字段。"""

    data = _today()

    assert data["total_days"] == 30
    # 日历推导：day_index 始终落在 1..30
    assert 1 <= data["day_index"] <= 30
    assert data["sprint_start"] == SPRINT_START

    # 「今天第几天」
    assert data["day"]["seq"] >= 1
    # 「今天干什么」
    assert data["day"]["title"]
    assert isinstance(data["day"]["acceptance"], list) and data["day"]["acceptance"]
    # 「今天做完没有」
    assert set(data["artifact_status"].keys()) == set(ARTIFACT_KINDS)
    assert isinstance(data["missing_kinds"], list)
    assert isinstance(data["all_done"], bool)
    # 总账
    assert len(data["ledger"]) == 5


def test_today_day_override_keeps_calendar_index():
    """?day= 只换课程日，不篡改日历口径 —— 这是 P1 滑期机制的接口前提。"""

    data = _today(day=2)

    assert data["day"]["seq"] == 2
    assert data["day"]["title"] == "测试课程日 2"
    # day_index 仍是日历推导值，与 seq 解耦
    assert data["day_index"] == _today()["day_index"]


def test_today_invalid_day_is_422():
    """day 越界应 422，而不是静默回落到某一天。"""

    for bad in (0, 31, -1):
        resp = client.get(f"/api/plan/today?day={bad}")
        assert resp.status_code == 422, f"day={bad} 期望 422，实际 {resp.status_code}"


def test_today_missing_day_is_404():
    """课程日不存在时 404，并在 detail 里提示跑种子脚本。"""

    # 动态挑一个库中确实缺失的 seq —— 写死 29 会与 fixture 补种的"日历当天"撞车。
    present = _seeded_seqs()
    missing = next((s for s in range(1, 31) if s not in present), None)
    assert missing is not None, "临时库已含全部 30 天，无法构造 404 用例"

    resp = client.get(f"/api/plan/today?day={missing}")
    assert resp.status_code == 404
    assert "seed_plan_30d" in resp.json()["detail"]


# ============================================================
# 3. 四件套勾选
# ============================================================


def test_artifact_toggle_updates_status_and_ledger():
    """勾选 → 该槽位变已交、missing 减少、总账 +1；取消 → 全部还原。"""

    day_id = _day_id(1)
    _clear_artifacts(1)

    before = _today(day=1)
    assert "code" in before["missing_kinds"]

    # 勾选 code
    resp = client.post(
        "/api/plan/artifacts",
        json={
            "plan_day_id": day_id,
            "kind": "code",
            "title": "01_transformer/model.py",
            "url": "https://github.com/x/y",
        },
    )
    assert resp.status_code == 200, resp.text
    artifact = resp.json()["data"]
    assert artifact["kind"] == "code"
    # P0 手工记账，auto_verified 必须为 False（P2 才由 GitHub 自动核验）
    assert artifact["auto_verified"] is False

    after = _today(day=1)
    assert after["artifact_status"]["code"] == 1
    assert "code" not in after["missing_kinds"]

    def _ledger(data: dict, key: str) -> int:
        return next(i["done"] for i in data["ledger"] if i["key"] == key)

    assert _ledger(after, "code") == _ledger(before, "code") + 1

    # 取消
    resp = client.delete(f"/api/plan/artifacts/{artifact['id']}")
    assert resp.status_code == 200, resp.text

    restored = _today(day=1)
    assert restored["artifact_status"]["code"] == 0
    assert "code" in restored["missing_kinds"]
    assert _ledger(restored, "code") == _ledger(before, "code")


def test_all_four_kinds_makes_day_complete():
    """四类齐全 → all_done=True、missing 为空、总账「齐全日」+1。"""

    day_id = _day_id(2)
    _clear_artifacts(2)

    before = _today(day=2)
    assert before["all_done"] is False

    for kind in ARTIFACT_KINDS:
        resp = client.post(
            "/api/plan/artifacts",
            json={"plan_day_id": day_id, "kind": kind, "title": f"Day2 {kind}"},
        )
        assert resp.status_code == 200, resp.text

    after = _today(day=2)
    assert after["missing_kinds"] == []
    assert after["all_done"] is True

    def _days(data: dict) -> int:
        return next(i["done"] for i in data["ledger"] if i["key"] == "days")

    assert _days(after) == _days(before) + 1

    # 传 seq 不是 plan_day.id（helper 口径见其 docstring）：日历课程日被更早的
    # 模块先种下时 id≠seq，传 id 会清错天/404 并残留四件套污染后续总账断言。
    _clear_artifacts(2)


def test_artifact_invalid_kind_is_422():
    """kind 只允许四件套，其他一律 422。"""

    resp = client.post(
        "/api/plan/artifacts",
        json={"plan_day_id": _day_id(1), "kind": "video"},
    )
    assert resp.status_code == 422


def test_artifact_unknown_plan_day_is_404():
    """指向不存在的课程日应 404。"""

    resp = client.post(
        "/api/plan/artifacts",
        json={"plan_day_id": 999999, "kind": "code"},
    )
    assert resp.status_code == 404


# ============================================================
# 4. 任务归属课程日
# ============================================================


def test_task_bound_to_plan_day_shows_in_today():
    """plan_day_id 绑定的任务应出现在当天施工单里，且不影响其他天。"""

    day_id = _day_id(1)
    resp = client.post(
        "/api/tasks",
        json={
            "title": "P0 测试 · Day1 任务",
            "duration": 40,
            "status": "todo",
            "acceptance": ["a"],
            "track_key": "llm",
            "plan_day_id": day_id,
        },
    )
    assert resp.status_code == 200, resp.text
    task = resp.json()["data"]
    assert task["plan_day_id"] == day_id

    day1 = _today(day=1)
    day2 = _today(day=2)

    assert any(t["id"] == task["id"] for t in day1["tasks"]), day1["tasks"]
    assert all(t["id"] != task["id"] for t in day2["tasks"]), day2["tasks"]

    # tasks 列表接口的 plan_day_id 过滤同样生效
    filtered = client.get(f"/api/tasks?plan_day_id={day_id}").json()["data"]
    assert all(t["plan_day_id"] == day_id for t in filtered)


# ============================================================
# 5. P1：总览 + 滑期决策
# ============================================================


def _post_progress(plan_day_id: int, status: str, note: str | None = None):
    """记录一天的执行决策（POST /api/plan/progress）。"""

    return client.post(
        "/api/plan/progress",
        json={"plan_day_id": plan_day_id, "status": status, "deviation_note": note},
    )


def _overview(day: int | None = None) -> dict:
    """取施工总览 data 段。"""

    url = "/api/plan/overview" + (f"?day={day}" if day is not None else "")
    resp = client.get(url)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_overview_reports_behind_when_incomplete():
    """Day1 完成、Day2 未完成、as-if 今天 Day3 → 落后 2 天，Day2 标红待决策。"""

    _post_progress(_day_id(1), "done")
    data = _overview(day=3)

    assert data["total_days"] == 30
    assert data["completed_days"] == 1
    assert data["behind"] == 2

    by_seq = {d["seq"]: d for d in data["days"]}
    assert by_seq[1]["status"] == "done"
    assert by_seq[1]["is_missed"] is False
    # Day2 未完成且 seq<=3 → 标红
    assert by_seq[2]["status"] == "pending"
    assert by_seq[2]["is_missed"] is True


def test_overview_compressed_counts_as_passed():
    """压缩（compressed）算通过、计入课程进度、不标红，且偏离说明被记录。"""

    _post_progress(_day_id(1), "done")
    _post_progress(_day_id(2), "compressed", note="压缩：本日验收降级速通")

    data = _overview(day=3)
    assert data["completed_days"] == 2
    assert data["behind"] == 1  # 只落后 Day3

    by_seq = {d["seq"]: d for d in data["days"]}
    assert by_seq[2]["status"] == "compressed"
    assert by_seq[2]["is_missed"] is False
    assert by_seq[2]["deviation_note"] == "压缩：本日验收降级速通"


def test_progress_invalid_status_is_422():
    """status 不在枚举内应 422。"""

    resp = _post_progress(_day_id(1), "banana")
    assert resp.status_code == 422


def test_progress_unknown_plan_day_is_404():
    """指向不存在的课程日应 404。"""

    resp = _post_progress(999999, "done")
    assert resp.status_code == 404
