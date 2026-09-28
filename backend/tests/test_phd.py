"""博士模块（Phase 1）测试。

覆盖：
  1. PhDMatchEngine 纯规则确定性（高契合 / 低契合两个基准场景）
  2. API 流程：方向 → 机会 → 导师 → 匹配 → 列表富集
  3. 迁移方言兼容：三个新 .sql 在全目录扫描下无 SQLite 残留

测试库隔离由 tests/conftest.py 提供（会话级临时库），不碰开发库。
"""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.agents.phd.agent import PhDMatchEngine, WEIGHTS
from app.main import app
from migrations import run_migration as rm

client = TestClient(app)


# ============================================================
# 1. 六维匹配引擎（纯规则，确定可解释）
# ============================================================

def test_engine_high_fit():
    """高契合场景：985 + 北京 + 无成果门槛 + 在职友好 + 常年招生。"""

    today = date(2026, 9, 20)
    res = PhDMatchEngine.compute(
        direction_interest=100,
        tier="985",
        city="北京",
        min_publication="none",
        target_in_service=True,
        advisor_in_service=False,
        application_deadline=None,
        today=today,
    )
    assert res.dimensions["direction_fit"] == 100
    assert res.dimensions["institution_tier"] == 92  # 985
    assert res.dimensions["geo"] == 100
    assert res.dimensions["publication_match"] == 100
    assert res.dimensions["in_service_friendly"] == 100
    assert res.dimensions["timeline"] == 55  # 未公布（X4 新分带：中性偏保守）
    expected = int(round(
        WEIGHTS["direction_fit"] * 100
        + WEIGHTS["institution_tier"] * 92
        + WEIGHTS["geo"] * 100
        + WEIGHTS["publication_match"] * 100
        + WEIGHTS["in_service_friendly"] * 100
        + WEIGHTS["timeline"] * 55
    ))
    assert res.overall == expected == 92
    assert res.grade == "A"
    # X4 新分带 55 < gap 阈值 60：未公布截止日计入 timeline gap
    assert [g["dimension"] for g in res.gaps] == ["timeline"]


def test_engine_low_fit_flags_gaps():
    """低契合场景：普通院校 + 异地 + 需 SCI + 不友好 + 已错过窗口。"""

    today = date(2026, 9, 20)
    res = PhDMatchEngine.compute(
        direction_interest=55,
        tier="普通",
        city="外地",
        min_publication="sci",
        target_in_service=False,
        advisor_in_service=False,
        application_deadline=date(2025, 1, 1),  # 已过
        today=today,
    )
    assert res.dimensions["institution_tier"] == 55  # 普通
    assert res.dimensions["geo"] == 60
    assert res.dimensions["publication_match"] == 60  # sci，用户为 EI
    assert res.dimensions["in_service_friendly"] == 40
    assert res.dimensions["timeline"] == 20  # 已错过
    expected = int(round(
        WEIGHTS["direction_fit"] * 55
        + WEIGHTS["institution_tier"] * 55
        + WEIGHTS["geo"] * 60
        + WEIGHTS["publication_match"] * 60
        + WEIGHTS["in_service_friendly"] * 40
        + WEIGHTS["timeline"] * 20
    ))
    assert res.overall == expected == 49
    gap_dims = {g["dimension"] for g in res.gaps}
    assert gap_dims == {
        "direction_fit",
        "institution_tier",
        "in_service_friendly",
        "timeline",
    }
    # publication_match=60 不计入 gap（阈值 <60）
    assert "publication_match" not in gap_dims


def test_engine_timeline_band():
    """时间窗口分带（X4 新分带）：黄金窗口 95 / 两年内 75 / 更远 55 / 已错过 20 / 未公布 55。"""

    base = date(2026, 9, 20)
    def tl(deadline):
        return PhDMatchEngine.compute(
            direction_interest=70, tier="211", city="北京",
            min_publication="none", target_in_service=True,
            advisor_in_service=False, application_deadline=deadline, today=base,
        ).dimensions["timeline"]
    assert tl(date(2027, 3, 1)) == 95    # 黄金窗口（162 天）
    assert tl(date(2028, 1, 1)) == 75    # 两年内（468 天）
    assert tl(date(2030, 1, 1)) == 55    # 更远
    assert tl(date(2025, 1, 1)) == 20    # 已错过
    assert tl(None) == 55                # 未公布


# ============================================================
# 2. API 流程
# ============================================================

def test_api_phd_flow():
    """方向 → 机会 → 导师 → 匹配 → 列表富集。"""

    # 方向
    d = client.post("/api/phd/directions", json={
        "key": "test_dir", "name": "测试方向", "interest_weight": 100,
    })
    assert d.status_code == 200, d.text
    assert d.json()["data"]["key"] == "test_dir"

    # 机会
    t = client.post("/api/phd/targets", json={
        "institution": "测试院校", "city": "北京", "tier": "211",
        "direction_key": "test_dir", "track_key": "embodied",
        "in_service_friendly": True, "min_publication": "none",
        "application_deadline": "2027-03-01",
    })
    assert t.status_code == 200, t.text
    target_id = t.json()["data"]["id"]

    # 导师
    a = client.post("/api/phd/advisors", json={
        "target_id": target_id, "name": "测试导师", "title": "教授",
        "research_area": "具身智能", "recruiting": True,
        "in_service_friendly": True,
    })
    assert a.status_code == 200, a.text
    adv_id = a.json()["data"]["id"]
    assert a.json()["data"]["institution"] == "测试院校"  # 反查富集

    # 匹配
    m = client.post(f"/api/phd/advisors/{adv_id}/match")
    assert m.status_code == 200, m.text
    assert m.json()["data"]["overall"] >= 80  # 高契合 → A

    # 列表返回 match_json + 截止日
    lst = client.get("/api/phd/advisors")
    assert lst.status_code == 200, lst.text
    found = next(x for x in lst.json()["data"] if x["id"] == adv_id)
    assert found["match_json"]["overall"] >= 80
    assert str(found["application_deadline"]) == "2027-03-01"


def test_api_phd_target_filter():
    """机会列表按 track_key 过滤。"""

    client.post("/api/phd/targets", json={
        "institution": "过滤测试院校", "city": "北京", "tier": "985",
        "direction_key": "vla", "track_key": "embodied",
        "in_service_friendly": False, "min_publication": "none",
    })
    resp = client.get("/api/phd/targets", params={"track_key": "embodied"})
    assert resp.status_code == 200
    insts = {t["institution"] for t in resp.json()["data"]}
    assert "过滤测试院校" in insts


def test_api_phd_advisor_not_found():
    resp = client.post("/api/phd/advisors/999999/match")
    assert resp.status_code == 404


# ============================================================
# 3. 迁移方言兼容
# ============================================================

def test_phd_migrations_translate_without_residue():
    """三个新迁移在 PG 翻译后无 SQLite 残留（全目录扫描的子集）。"""

    for fname in ("0021_research_directions.sql", "0022_phd_targets.sql", "0023_phd_advisors.sql"):
        out = rm.translate_sql_for_postgres((rm.MIGRATIONS_DIR / fname).read_text(encoding="utf-8"))
        assert rm.find_untranslatable_syntax(out) == [], f"{fname} 翻译后仍含 SQLite 专属写法"
