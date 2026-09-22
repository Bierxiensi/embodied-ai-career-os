"""Phase 3 统一落地页（Career Transition Dashboard）测试。

最重要的一条是 ``test_readiness_is_identical_to_job_hunt``：
    落地页与求职看板对"离目标岗位差多少"必须给出**完全相同的数字**。
    这两处此前各自算一遍，Phase 3 把它收进 services/readiness ——
    本文件就是那次收口的护栏：任何人再把计算抄回去，测试会红。

其余覆盖：
 - 五区字段齐全（空库不 500）
 - 答辩倒计时与七维风险雷达**同源**（同一个 DEFENSE_DEADLINE 驱动）
 - 倒计时分档阈值（overdue/urgent/soon/ok）
 - 博士区：空表零值安全、计数反映真实表、最近截止日的取向、Top 导师排序

两套库的用法（刻意区分）：
 - **共享测试库**（conftest 的临时库，见 SessionLocal）：只用来看"当前状态"，
   断言不写死条数 —— 同会话其他模块可能改过它。
 - **自建临时库**（``isolated_db`` fixture）：博士区的条数 / 排序 / 空态断言
   全部在这里做。前提由用例自己保证，不与别的模块耦合
   （这正是"共享库只做增量断言"那条经验的可执行版本）。
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.risk import DEFENSE_DEADLINE
from app.core.transition_context import (
    EMPLOYMENT,
    TRANSITION_WINDOW_END,
    TRANSITION_WINDOW_START,
)
from app.main import app
from app.models.phd import PhDAdvisor, PhDTarget
from app.services.transition import service as transition_service
from app.services.transition.service import (
    STATUS_SOON_DAYS,
    STATUS_URGENT_DAYS,
    _status_for,
)

# 回归锚点（v3.2 双轨口径）：主攻赛道 llm 的推进度 / 严格达标率
ANCHOR_MAIN_TRACK_KEY = "llm"
ANCHOR_MATCH_PCT = 67
ANCHOR_STRICT_PCT = 23
ANCHOR_QUALIFIED = 3
ANCHOR_REQUIRED = 13


def _dashboard(client: TestClient) -> dict:
    body = client.get("/api/transition/dashboard").json()
    assert body["success"] is True, body
    return body["data"]


@pytest.fixture()
def isolated_db(tmp_path):
    """自建临时库（含全部表结构），供需要精确控制表内容的用例使用。

    不用 ``sqlite://`` 内存库：TestClient 会把同步端点丢进线程池，
    内存库连接不共享，表会"消失"（项目里踩过）。文件库最稳。
    """

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models  # noqa: F401  注册全部模型到 Base.metadata
    from app.db.base import Base

    engine = create_engine(f"sqlite:///{(tmp_path / 'isolated.db').as_posix()}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ==============================================================================
# 1. 五区齐全
# ==============================================================================


def test_dashboard_payload_has_all_sections():
    """五区对应的字段必须齐全（ROI / Risk 在 /api/plan/today，不在此契约）。"""

    with TestClient(app) as client:
        data = _dashboard(client)

    assert set(data) >= {"as_of", "mode", "career_progress", "position", "academic"}

    # 第 1 区：职业进度
    cp = data["career_progress"]
    assert set(cp) >= {"primary_track_key", "tracks", "milestones"}
    assert len(cp["tracks"]) == 4                     # llm / vlm / ai-algo / embodied
    assert cp["primary_track_key"] == ANCHOR_MAIN_TRACK_KEY
    assert len(cp["milestones"]) >= 2                 # 导师联系窗口 + 答辩

    # 第 2 区：当前工作
    assert data["position"]["company"]

    # 第 3 区：学术与博士
    academic = data["academic"]
    assert set(academic) == {"degree", "phd"}
    assert academic["degree"]["status"] in {"overdue", "urgent", "soon", "ok"}


def test_dashboard_mode_matches_career_mode_endpoint():
    """模式块与 /api/career-mode 同源（前端据此决定雷达走 R1 还是 R2）。"""

    with TestClient(app) as client:
        data = _dashboard(client)
        mode = client.get("/api/career-mode").json()["data"]["current"]

    assert data["mode"]["key"] == mode["key"]
    assert data["mode"]["name"] == mode["name"]
    assert set(data["mode"]) >= {
        "key",
        "name",
        "objective",
        "deadline",
        "days_left",
        "active_track_keys",
        "frozen_track_keys",
        "is_current",
    }


# ==============================================================================
# 2. ★ 就绪度与求职看板同源（本文件的核心护栏）
# ==============================================================================


def test_readiness_is_identical_to_job_hunt():
    """★ /api/transition/dashboard 的赛道就绪度必须与 /api/job-hunt 逐字相同。

    两页显示的"离岗位差多少"若不一致，用户无从判断哪个数字可信 ——
    这正是把匹配计算收进 services/readiness 的原因。此断言是那次收口的
    回归护栏：任何人把计算抄回任一路由，这里立刻失败。
    """

    with TestClient(app) as client:
        board = client.get("/api/job-hunt").json()["data"]
        dashboard = _dashboard(client)

    roles = board["target_roles"]
    tracks = dashboard["career_progress"]["tracks"]
    assert len(roles) == len(tracks)

    for role, track in zip(roles, tracks):
        assert role["key"] == track["key"]
        for field in (
            "match_pct",
            "strict_pct",
            "qualified_count",
            "required_count",
        ):
            assert role[field] == track[field], (
                f"{role['key']} 的 {field} 两处不一致："
                f"job-hunt={role[field]} dashboard={track[field]}"
            )
        # 明细派生量也要一致
        assert len(role["skills"]) == track["skill_count"]
        assert sum(1 for s in role["skills"] if s["gap"] > 0) == track["gap_count"]


def test_main_track_readiness_anchor():
    """回归锚点：llm 推进度 67% / 严格达标 23%（3/13）。

    这组数字是 v3.2 双轨口径的验收值（docs/项目梳理与迭代指导-2026-09-21.md 裁决②），
    也是"67-89 的推进度会被误读成已达标"那个结论的证据来源。
    """

    with TestClient(app) as client:
        track = next(
            t
            for t in _dashboard(client)["career_progress"]["tracks"]
            if t["key"] == ANCHOR_MAIN_TRACK_KEY
        )

    got = (
        track["match_pct"],
        track["strict_pct"],
        track["qualified_count"],
        track["required_count"],
        track["skill_count"],
    )
    want = (
        ANCHOR_MATCH_PCT,
        ANCHOR_STRICT_PCT,
        ANCHOR_QUALIFIED,
        ANCHOR_REQUIRED,
        ANCHOR_REQUIRED,
    )
    assert got == want, (
        f"llm 就绪度锚点漂移：实得 (match%, strict%, 达标数, 需求数, 轴数)={got}，"
        f"期望 {want}。\n"
        "先排除「共享测试库被别的用例改过」——conftest 的临时库是全量会话共用的，"
        "若某用例提升了主攻赛道所需技能的等级且没还原，推进度就会虚高。\n"
        f"当前赛道明细：{track['skills']}"
    )


# ==============================================================================
# 3. 学术：与风险雷达同源 + 倒计时分档
# ==============================================================================


def test_defense_deadline_is_shared_with_risk_radar():
    """答辩截止日只能有一个定义：落地页与七维风险雷达的 academic 维度同源。

    断言的是**行为一致性**而不是字符串相等：风险雷达的 academic 等级由
    "距答辩天数 < 90" 这个阈值驱动（core/risk.py），因此 90 天两侧的等级
    必须与落地页算出的 days_left 对得上。若哪天有人把 DEFENSE_DEADLINE
    在别处再写一遍且日期不同，这条会红。
    """

    with TestClient(app) as client:
        degree = _dashboard(client)["academic"]["degree"]
        risk = client.get("/api/risk").json()["data"]

    assert degree["deadline"] == DEFENSE_DEADLINE.isoformat()
    assert degree["days_left"] == (DEFENSE_DEADLINE - date.today()).days

    academic = next(d for d in risk["dimensions"] if d["key"] == "academic")
    if degree["days_left"] >= 90:
        assert academic["level"] == "green", academic
    else:
        assert academic["level"] in {"red", "amber"}, academic


def test_milestone_days_left_matches_service():
    """落地页的关键节点与 core/transition_context 的节点集合/日期一致。"""

    from app.core.transition_context import key_milestones

    with TestClient(app) as client:
        milestones = _dashboard(client)["career_progress"]["milestones"]

    expected = {m.key: m for m in key_milestones()}
    assert {m["key"] for m in milestones} == set(expected)
    for m in milestones:
        src = expected[m["key"]]
        assert m["deadline"] == src.deadline.isoformat()
        assert m["days_left"] == (src.deadline - date.today()).days
        assert m["status"] == _status_for(m["days_left"])


@pytest.mark.parametrize(
    "days,expected",
    [
        (-1, "overdue"),
        (-30, "overdue"),
        (0, "urgent"),
        (STATUS_URGENT_DAYS, "urgent"),
        (STATUS_URGENT_DAYS + 1, "soon"),
        (STATUS_SOON_DAYS, "soon"),
        (STATUS_SOON_DAYS + 1, "ok"),
        (400, "ok"),
    ],
)
def test_status_buckets(days: int, expected: str):
    """倒计时分档阈值（唯一权威在 services/transition/service.py）。"""

    assert _status_for(days) == expected


# ==============================================================================
# 4. 当前工作
# ==============================================================================


def test_position_reflects_transition_context():
    """在职事实与在职转型窗口来自 core/transition_context，不在路由里硬编码。"""

    with TestClient(app) as client:
        pos = _dashboard(client)["position"]

    assert pos["company"] == EMPLOYMENT.company
    assert pos["role"] == EMPLOYMENT.role
    assert pos["focus"] == EMPLOYMENT.focus
    assert pos["since_label"] == EMPLOYMENT.since_label
    assert pos["end_label"] is None              # 已确认留任 → 无离职月份
    assert pos["status_label"] == EMPLOYMENT.status_label
    assert pos["transition_window_start"] == TRANSITION_WINDOW_START
    assert pos["transition_window_end"] == TRANSITION_WINDOW_END
    assert TRANSITION_WINDOW_START in pos["transition_window_label"]


# ==============================================================================
# 5. 博士区（全部在自建临时库上做，前提由用例自己保证）
# ==============================================================================


def test_phd_section_is_safe_on_empty_tables(isolated_db):
    """空表（新装环境）必须给出零值而不是 500。"""

    assert isolated_db.query(PhDTarget).count() == 0
    assert isolated_db.query(PhDAdvisor).count() == 0

    academic = transition_service.build_academic(isolated_db, date.today())
    phd = academic["phd"]

    assert phd["target_count"] == 0
    assert phd["advisor_count"] == 0
    assert phd["contacted_count"] == 0
    assert phd["matched_count"] == 0
    assert phd["nearest_deadline"] is None
    assert phd["top_advisors"] == []
    # 窗口本身与表无关，仍必须有值
    assert phd["window_deadline"]
    assert academic["degree"]["deadline"] == DEFENSE_DEADLINE


def test_phd_counts_reflect_tables_and_nearest_deadline_prefers_upcoming(isolated_db):
    """计数反映真实表；最近截止日优先取「未过期里最早的那个」。"""

    today = date.today()
    near = PhDTarget(
        institution="TEST_UNIV_近",
        city="北京",
        tier="211",
        application_deadline=today + timedelta(days=20),
        source="test",
    )
    far = PhDTarget(
        institution="TEST_UNIV_远",
        tier="985",
        application_deadline=today + timedelta(days=120),
        source="test",
    )
    past = PhDTarget(
        institution="TEST_UNIV_已过",
        tier="985",
        application_deadline=today - timedelta(days=5),
        source="test",
    )
    isolated_db.add_all([near, far, past])
    isolated_db.commit()

    advisor = PhDAdvisor(
        target_id=near.id,
        name="TEST_ADVISOR",
        contacted=True,
        match_json={"overall": 88, "grade": "A", "dimensions": {}, "gaps": []},
        source="test",
    )
    isolated_db.add(advisor)
    isolated_db.commit()

    phd = transition_service.build_academic(isolated_db, today)["phd"]

    assert phd["target_count"] == 3
    assert phd["advisor_count"] == 1
    assert phd["contacted_count"] == 1
    assert phd["matched_count"] == 1

    nearest = phd["nearest_deadline"]
    assert nearest is not None
    assert nearest["institution"] == "TEST_UNIV_近"
    assert nearest["days_left"] == 20

    top = phd["top_advisors"]
    assert len(top) == 1
    assert top[0]["name"] == "TEST_ADVISOR"
    assert top[0]["institution"] == "TEST_UNIV_近"
    assert top[0]["tier"] == "211"
    assert top[0]["contacted"] is True
    assert top[0]["match_overall"] == 88
    assert top[0]["match_grade"] == "A"


def test_nearest_deadline_falls_back_to_latest_past_when_all_expired(isolated_db):
    """全部过期时退回「最晚的那个已过截止日」，并如实报负数天数。

    不返回 None：当前种子数据的截止日多为历史值，
    "有截止日但全都过期了"本身是必须被看见的状态。
    """

    today = date.today()
    isolated_db.add_all(
        [
            PhDTarget(
                institution="TEST_UNIV_更早",
                application_deadline=today - timedelta(days=300),
                source="test",
            ),
            PhDTarget(
                institution="TEST_UNIV_较晚",
                application_deadline=today - timedelta(days=10),
                source="test",
            ),
        ]
    )
    isolated_db.commit()

    nearest = transition_service.build_academic(isolated_db, today)["phd"][
        "nearest_deadline"
    ]
    assert nearest["institution"] == "TEST_UNIV_较晚"
    assert nearest["days_left"] == -10


def test_top_advisors_are_ordered_by_match_overall(isolated_db):
    """Top 导师按六维匹配置信度降序；没有匹配结果的排最后而不是被丢掉。

    行为依据：刚录入还没算过匹配的导师也必须出现在落地页上，
    否则"录了导师却看不到"会让人以为没保存成功。
    """

    isolated_db.add_all(
        [
            PhDAdvisor(
                name="TEST_ADV_LOW",
                match_json={"overall": 40, "grade": "C"},
                source="test",
            ),
            PhDAdvisor(
                name="TEST_ADV_HIGH",
                match_json={"overall": 91, "grade": "A"},
                source="test",
            ),
            PhDAdvisor(name="TEST_ADV_NONE", source="test"),
        ]
    )
    isolated_db.commit()

    top = transition_service.build_academic(isolated_db, date.today(), top_n=10)["phd"][
        "top_advisors"
    ]
    assert [a["name"] for a in top] == [
        "TEST_ADV_HIGH",
        "TEST_ADV_LOW",
        "TEST_ADV_NONE",
    ]
    assert top[0]["match_overall"] == 91
    assert top[2]["match_overall"] is None
