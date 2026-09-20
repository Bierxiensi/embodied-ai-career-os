"""职业阶段模式骨架（Milestone A）测试。

覆盖 PRD 的完成定义与三条不变量：
  1. 默认进入 job_hunt，且"当前模式"全局唯一（PRD §5 F1.1）
  2. 切换后仍保持 —— 重新发起请求 / 重启同步都不会把选择抹掉（PRD §9.1）
  3. 切换不删除、不修改、不隐藏任何既有职业 / 岗位 / 任务 / 投递 / 面试数据（PRD §5 F1.3）

测试隔离由 tests/conftest.py 提供（会话级临时库），本文件不自建开发库连接；
需要"全新空库"语义的两个用例在本文件内自建 SQLite 内存库，与开发库无关。

注意：本文件会切换全局当前模式，因此每个用例都先把前置条件设成自己要的样子
（_ensure_current_mode），不断言"库里原本是哪种模式"，避免依赖执行顺序。
"""

from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.target_roles import TARGET_ROLES
from app.db.base import Base, SessionLocal
from app.main import app
from app.models import (
    CareerMode,
    InterviewLog,
    JobApplication,
    JobPosting,
    Milestone,
    ModeTransition,
    PlanDay,
    Project,
    Skill,
    Task,
)
from app.services.career_mode.presets import (
    DEFAULT_MODE_KEY,
    JOB_HUNT_MODE_KEY,
    LONG_TERM_TRANSITION_MODE_KEY,
    preset_keys,
)
from app.services.career_mode.service import sync_career_modes

client = TestClient(app)

# 切换模式必须原样保留的既有业务数据（PRD §5 F1.3 列举的"职业 / 岗位 / 任务 / 投递 / 面试"）
_PRESERVED_TABLES = (
    Task,
    JobApplication,
    JobPosting,
    InterviewLog,
    Skill,
    Project,
    Milestone,
    PlanDay,
)


# ============================================================
# 辅助
# ============================================================


def _overview() -> dict:
    resp = client.get("/api/career-mode")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _switch(mode_key: str, note: str | None = None):
    body: dict = {"mode_key": mode_key}
    if note is not None:
        body["note"] = note
    return client.post("/api/career-mode/switch", json=body)


def _ensure_current_mode(mode_key: str) -> None:
    """把当前模式设成 mode_key；已是则接受 409（前置条件，与执行顺序无关）。"""

    resp = _switch(mode_key)
    assert resp.status_code in (200, 409), resp.text


def _transitions() -> list[dict]:
    resp = client.get("/api/career-mode/transitions")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _business_data_digest() -> str:
    """既有业务数据的**内容级**指纹（只读）。

    只比行数不足以证明"没被改动"—— 原地 UPDATE 同样保持行数不变。因此这里对
    全部行内容做摘要，任何字段变化都会改变指纹。
    """

    snapshot: dict[str, list[str]] = {}
    with SessionLocal() as db:
        for model in _PRESERVED_TABLES:
            rows = db.execute(select(model.__table__)).mappings().all()
            snapshot[model.__tablename__] = sorted(
                json.dumps(dict(row), sort_keys=True, default=str) for row in rows
            )
    return hashlib.sha256(
        json.dumps(snapshot, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _fresh_engine():
    """全新的 SQLite 内存库（与开发库、与会话级临时库都无关）。"""

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine


# ============================================================
# 1. 默认模式与模式目录
# ============================================================


def test_fresh_database_defaults_current_mode_to_job_hunt():
    """空库首次同步后，当前模式必须是 job_hunt，且有且仅有一行（PRD F1.1）。"""

    engine = _fresh_engine()

    with Session(engine) as db:
        modes = sync_career_modes(db)
        current = [m for m in modes if m.is_current]

        assert len(current) == 1, "当前模式必须唯一"
        assert current[0].key == JOB_HUNT_MODE_KEY == DEFAULT_MODE_KEY
        assert {m.key for m in modes} == set(preset_keys()), "预置模式应全部物化"

        # 首次激活同样留痕，否则历史里会出现"从无到有"的断点
        initial = db.query(ModeTransition).all()
        assert len(initial) == 1
        assert initial[0].from_mode is None
        assert initial[0].to_mode == JOB_HUNT_MODE_KEY


def test_overview_lists_all_presets_with_exactly_one_current():
    """GET /api/career-mode 返回全部可选模式，且其中只有一个是当前模式。"""

    data = _overview()

    assert [m["key"] for m in data["available"]] == preset_keys(), "按预置顺序展示"
    current_flags = [m["is_current"] for m in data["available"]]
    assert current_flags.count(True) == 1
    assert data["current"]["key"] == next(
        m["key"] for m in data["available"] if m["is_current"]
    )


def test_track_strategy_is_derived_from_target_roles():
    """求职模式的生效/冻结赛道必须与 target_roles.py 的 frozen 标记一致。

    防止有人在模式预置里抄一份赛道清单 —— 那样 target_roles.py 一改（例如解冻
    具身赛道），模式策略就与实际赛道配置脱节，同一件事出现两个说法。
    """

    _ensure_current_mode(JOB_HUNT_MODE_KEY)
    job_hunt = next(
        m for m in _overview()["available"] if m["key"] == JOB_HUNT_MODE_KEY
    )

    expected_active = [r.key for r in TARGET_ROLES if not r.frozen]
    expected_frozen = [r.key for r in TARGET_ROLES if r.frozen]

    assert job_hunt["active_track_keys"] == expected_active
    assert job_hunt["frozen_track_keys"] == expected_frozen
    assert job_hunt["frozen_track_keys"], "本次没有冻结赛道，测试失去意义（见 target_roles.py）"


def test_deadline_days_left_matches_deadline():
    """days_left 由后端按 deadline 推导；长期模式无硬截止时为 null。

    断言的是**两者自洽**，不写死"还有 45 天"这类会随时间变红的数字。
    """

    _ensure_current_mode(JOB_HUNT_MODE_KEY)
    job_hunt = _overview()["current"]
    assert job_hunt["deadline"] is not None
    assert isinstance(job_hunt["days_left"], int)

    long_term = next(
        m for m in _overview()["available"] if m["key"] == LONG_TERM_TRANSITION_MODE_KEY
    )
    assert long_term["deadline"] is None
    assert long_term["days_left"] is None


# ============================================================
# 2. 切换与持久化
# ============================================================


def test_switch_persists_current_mode_across_requests():
    """切换后重新请求（等价于刷新页面）仍是新模式，再切回也能保持。"""

    _ensure_current_mode(LONG_TERM_TRANSITION_MODE_KEY)
    assert _overview()["current"]["key"] == LONG_TERM_TRANSITION_MODE_KEY

    assert _switch(JOB_HUNT_MODE_KEY).status_code == 200
    assert _overview()["current"]["key"] == JOB_HUNT_MODE_KEY


def test_switch_appends_history_with_note():
    """每次成功切换追加一条记录：来源模式、目标模式、时间、用户备注（PRD F1.4）。"""

    _ensure_current_mode(JOB_HUNT_MODE_KEY)
    before = len(_transitions())

    resp = _switch(LONG_TERM_TRANSITION_MODE_KEY, note="已接受 offer，转入长期建设")
    assert resp.status_code == 200, resp.text

    history = _transitions()
    assert len(history) == before + 1, "成功切换必须恰好追加一条历史"

    latest = history[0]  # 最近的在最前
    assert latest["from_mode"] == JOB_HUNT_MODE_KEY
    assert latest["to_mode"] == LONG_TERM_TRANSITION_MODE_KEY
    assert latest["note"] == "已接受 offer，转入长期建设"
    assert latest["transitioned_at"]

    # 切换的返回体同时给出"切换后的模式"与"本次记录"，前端无需再查一次
    body = resp.json()["data"]
    assert body["current"]["key"] == LONG_TERM_TRANSITION_MODE_KEY
    assert body["transition"]["id"] == latest["id"]


def test_switch_to_current_mode_returns_409_and_writes_no_history():
    """切到当前已是的模式：409，且不产生任何历史（否则反复点会刷出空记录）。"""

    _ensure_current_mode(JOB_HUNT_MODE_KEY)
    before = len(_transitions())

    resp = _switch(JOB_HUNT_MODE_KEY)

    assert resp.status_code == 409
    assert "当前已经是该模式" in resp.json()["detail"]
    assert len(_transitions()) == before


def test_switch_to_unknown_mode_returns_400_listing_available_keys():
    """未知模式：400，错误信息必须给出可选的 key（用户能直接照着改）。"""

    resp = _switch("not_a_real_mode")

    assert resp.status_code == 400
    detail = resp.json()["detail"]
    for key in preset_keys():
        assert key in detail


def test_switch_rejects_invalid_payload():
    """写接口必须有入参校验：空 key / 缺字段都应被 Pydantic 拦下（422）。"""

    assert client.post("/api/career-mode/switch", json={"mode_key": ""}).status_code == 422
    assert client.post("/api/career-mode/switch", json={}).status_code == 422


# ============================================================
# 3. 切换不得触碰既有业务数据（PRD §5 F1.3 / §9.1）
# ============================================================


def test_switch_preserves_existing_business_data():
    """切换模式前后，职业 / 岗位 / 任务 / 投递 / 面试 / 技能 / 项目数据内容完全一致。"""

    _ensure_current_mode(JOB_HUNT_MODE_KEY)
    before = _business_data_digest()

    assert _switch(LONG_TERM_TRANSITION_MODE_KEY, note="数据保全断言").status_code == 200

    assert _business_data_digest() == before, (
        "切换模式改动或隐藏了既有业务数据 —— 这是 PRD F1.3 明确禁止的"
    )

    _ensure_current_mode(JOB_HUNT_MODE_KEY)  # 复原，减少对后续用例的影响


# ============================================================
# 4. 不变量：唯一当前模式 / 重新同步不覆盖用户选择
# ============================================================


def test_database_rejects_second_current_mode():
    """至多一个当前模式由数据库唯一索引保证，而不是靠调用方自觉。

    没有这条索引时，读取侧 `.first()` 会在两个候选中静默取舍 —— 页面显示的
    模式与库里真实状态不一致却毫无提示。
    """

    engine = _fresh_engine()

    with Session(engine) as db:
        db.add(
            CareerMode(
                key="mode_a", name="A", objective="x",
                active_track_keys=[], frozen_track_keys=[], is_current=True,
            )
        )
        db.flush()

        db.add(
            CareerMode(
                key="mode_b", name="B", objective="y",
                active_track_keys=[], frozen_track_keys=[], is_current=True,
            )
        )

        with pytest.raises(IntegrityError):
            db.commit()


def test_sync_realigns_definition_but_keeps_user_chosen_current_mode():
    """重新同步会校正模式定义，但绝不把用户选定的当前模式改回默认。

    这是"切换后刷新页面仍保持"的关键：后端每次启动都会跑一次同步
    （init_db → sync_career_modes），若同步顺手重置了 is_current，
    用户的切换会在下一次重启时被悄悄抹掉。
    """

    engine = _fresh_engine()

    with Session(engine) as db:
        sync_career_modes(db)

        # 模拟"配置改了 + 用户切到了长期模式"这两个同时发生的变化
        job_hunt = (
            db.query(CareerMode).filter(CareerMode.key == JOB_HUNT_MODE_KEY).one()
        )
        job_hunt.name = "被人手工改坏的旧名字"
        job_hunt.frozen_track_keys = []
        db.commit()

        current = (
            db.query(CareerMode)
            .filter(CareerMode.key == LONG_TERM_TRANSITION_MODE_KEY)
            .one()
        )
        current.is_current = True
        job_hunt.is_current = False
        db.commit()

        sync_career_modes(db)

        db.refresh(job_hunt)
        db.refresh(current)

        assert job_hunt.name != "被人手工改坏的旧名字", "定义字段应被预置校正"
        expected_frozen = [r.key for r in TARGET_ROLES if r.frozen]
        assert job_hunt.frozen_track_keys == expected_frozen
        assert current.is_current is True, "用户选定的当前模式不得被同步重置"
        assert job_hunt.is_current is False


def test_sync_is_idempotent():
    """重复同步不新增模式行、不新增历史（每次启动都会跑，必须幂等）。"""

    engine = _fresh_engine()

    with Session(engine) as db:
        sync_career_modes(db)
        mode_count = db.query(CareerMode).count()
        transition_count = db.query(ModeTransition).count()

        sync_career_modes(db)
        sync_career_modes(db)

        assert db.query(CareerMode).count() == mode_count
        assert db.query(ModeTransition).count() == transition_count
