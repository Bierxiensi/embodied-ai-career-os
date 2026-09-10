"""日报 / 周报引擎单测（Batch 4）。

覆盖：
- 纯函数：week_key / week_bounds / parse_next_action_date / funnel_of / render
- 隔离内存库：due_followups（计划到期 / 停滞超期 / 正常）、build_daily、build_weekly
- API 层：GET daily/weekly/followups/schedule、POST send 幂等

纯逻辑部分不依赖 DB / LLM；DB 部分用 ``sqlite:///:memory:`` 隔离，不污染开发库
（API 层沿用例行的 TestClient 集成风格）。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.report.engine import (
    REPORT_DAILY,
    REPORT_WEEKLY,
    ReportData,
    ReportSection,
    build_daily,
    build_weekly,
    due_followups,
    funnel_of,
    parse_next_action_date,
    render,
    week_bounds,
    week_key,
)


# ─────────────────────────── 隔离内存库 fixture ───────────────────────────

@pytest.fixture
def db():
    """隔离的内存 SQLite 会话（自动建全部表，用完即弃）。"""
    from app import models  # noqa: F401  确保 Base.metadata 感知所有表

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


TODAY = date(2026, 9, 10)


# ─────────────────────────── 纯函数 ───────────────────────────

def test_week_key_and_bounds():
    assert week_key(TODAY) == "2026-W37"
    start, end = week_bounds(TODAY)
    assert start == date(2026, 9, 7)   # 周一
    assert end == date(2026, 9, 13)    # 周日
    assert start.weekday() == 0
    assert end.weekday() == 6


def test_parse_next_action_date_iso_and_slash():
    assert parse_next_action_date("2026-09-12 前发感谢信", TODAY) == date(2026, 9, 12)
    assert parse_next_action_date("9/12 跟进 HR", TODAY) == date(2026, 9, 12)
    assert parse_next_action_date("09-12 二面", TODAY) == date(2026, 9, 12)


def test_parse_next_action_date_day_of_month():
    # 当月内未过期 → 当月
    assert parse_next_action_date("12日之前答复", TODAY) == date(2026, 9, 12)


def test_parse_next_action_date_rolls_to_next_year():
    # 解析出的日期明显早于当前（>180 天）→ 视为明年，避免"1/5"被当成过去
    assert parse_next_action_date("1/5 补投", TODAY) == date(2027, 1, 5)


def test_parse_next_action_date_none():
    assert parse_next_action_date(None, TODAY) is None
    assert parse_next_action_date("尽快跟进", TODAY) is None


def test_funnel_of_counts_and_rate():
    apps = [
        {"status": "applied"},
        {"status": "applied"},
        {"status": "screening"},
        {"status": "interview"},
        {"status": "rejected"},
    ]
    f = funnel_of(apps)
    assert f["total"] == 5
    assert f["applied"] == 2
    assert f["screening"] == 1
    assert f["interview"] == 1
    assert f["rejected"] == 1
    assert f["offer"] == 0
    # 响应 = screening + interview + offer = 2 → 40%
    assert f["response_rate"] == 40


def test_funnel_of_empty_is_zero():
    f = funnel_of([])
    assert f["total"] == 0
    assert f["response_rate"] == 0


def test_render_contains_sections():
    data = ReportData(
        kind=REPORT_DAILY,
        period_key="2026-09-10",
        title="测试日报",
        sections=[
            ReportSection("a", "段落一", ["行1", "行2"]),
            ReportSection("b", "段落二", []),
        ],
    )
    title, body = render(data)
    assert title == "测试日报"
    assert "【段落一】" in body
    assert "· 行1" in body
    assert "· 行2" in body
    # 空段落渲染为占位，不出现空白标题
    assert "【段落二】" in body
    assert "（无）" in body


def test_report_data_to_dict_roundtrip():
    data = ReportData(
        kind=REPORT_WEEKLY,
        period_key="2026-W37",
        title="t",
        sections=[ReportSection("k", "标题", ["x"])],
        metrics={"a": 1},
    )
    d = data.to_dict()
    assert d["kind"] == REPORT_WEEKLY
    assert d["period_key"] == "2026-W37"
    assert d["sections"][0] == {"key": "k", "title": "标题", "lines": ["x"]}
    assert d["metrics"] == {"a": 1}
    assert "generated_at" in d


# ─────────────────────────── due_followups ───────────────────────────

def _add_app(db, **kw):
    from app.models.job_application import JobApplication

    app_row = JobApplication(**kw)
    db.add(app_row)
    db.commit()
    db.refresh(app_row)
    return app_row


def test_due_followups_next_action_overdue(db):
    _add_app(
        db,
        company="A 公司",
        role="LLM 算法",
        status="screening",
        applied_at=TODAY - timedelta(days=2),
        next_action="9/8 前发感谢信",  # 已过期
    )
    due = due_followups(db, TODAY, stale_days=5)
    assert len(due) == 1
    assert due[0]["company"] == "A 公司"
    assert due[0]["overdue"] is True
    assert "到期" in due[0]["reason"]


def test_due_followups_stale_application(db):
    # 插入时显式给 updated_at（default 只在未提供时生效），模拟"停滞 10 天"
    _add_app(
        db,
        company="B 公司",
        role="AI 算法",
        status="applied",
        applied_at=TODAY - timedelta(days=20),
        updated_at=datetime(2026, 8, 31, 9, 0, 0),
    )

    due = due_followups(db, TODAY, stale_days=5)
    assert len(due) == 1
    assert due[0]["company"] == "B 公司"
    assert due[0]["overdue"] is False
    assert "停滞" in due[0]["reason"]


def test_due_followups_none_when_fresh(db):
    _add_app(
        db,
        company="C 公司",
        role="VLM 算法",
        status="screening",
        applied_at=TODAY,
        next_action="尽快跟进",  # 无日期
    )
    assert due_followups(db, TODAY, stale_days=5) == []


def test_due_followups_ignores_finished_status(db):
    _add_app(
        db,
        company="D 公司",
        role="LLM",
        status="offer",
        applied_at=TODAY - timedelta(days=30),
        updated_at=datetime(2026, 8, 1, 9, 0, 0),
    )
    # offer 属于已结束状态，停滞不应再提醒
    assert due_followups(db, TODAY, stale_days=5) == []


# ─────────────────────────── build_daily / build_weekly ───────────────────────────

def test_build_daily_empty_db_no_crash(db):
    data = build_daily(db, today=TODAY, stale_days=5)
    assert data.kind == REPORT_DAILY
    assert data.period_key == "2026-09-10"
    keys = [s.key for s in data.sections]
    assert keys == ["postings", "resume", "questions", "tasks", "applications", "priority"]
    # 空库也要有可读占位，不能有未定义/异常
    assert data.metrics["due_followups"] == 0
    assert data.metrics["recommended_postings"] == 0
    # 简历动作在事实库为空时应提示先建锚点
    resume = next(s for s in data.sections if s.key == "resume")
    assert any("事实锚点库为空" in line for line in resume.lines)


def test_build_daily_includes_recommended_posting(db):
    from app.models.job_match import GRADE_A, JobMatch
    from app.models.job_posting import JobPosting

    p = JobPosting(
        company="理想智能",
        title="大模型算法工程师",
        track="llm",
        tier=1,
        jd_text="Transformer SFT LoRA",
        dedup_key="理想智能-大模型算法工程师",
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    db.add(JobMatch(
        posting_id=p.id,
        match_score=86,
        grade=GRADE_A,
        dimension_scores={"tech_stack": 80, "project": 100, "edu_exp": 75,
                          "research": 100, "industry": 100},
        gaps=[{"skill": "SFT", "level": 3, "required": 4, "gap": 1}],
        matched_track="llm",
    ))
    db.commit()

    data = build_daily(db, today=TODAY, stale_days=5)
    postings = next(s for s in data.sections if s.key == "postings")
    assert any("理想智能" in line for line in postings.lines)
    assert any("A86" in line for line in postings.lines)
    assert data.metrics["recommended_postings"] == 1
    # 今日优先应把最高分岗位排上
    priority = next(s for s in data.sections if s.key == "priority")
    assert any("理想智能" in line for line in priority.lines)


def test_build_weekly_empty_db_no_crash(db):
    data = build_weekly(db, today=TODAY)
    assert data.kind == REPORT_WEEKLY
    assert data.period_key == "2026-W37"
    keys = [s.key for s in data.sections]
    assert keys == ["funnel", "gaps", "project", "interviews", "tasks", "research"]
    assert data.metrics["week_start"] == "2026-09-07"
    assert data.metrics["week_end"] == "2026-09-13"


def test_weekly_research_section_lists_config_skills(db):
    from app.models.skill import Skill

    db.add(Skill(name="Small-data Forecasting", category="Strong", level=4, target_level=4))
    db.add(Skill(name="Explainability", category="Strong", level=4, target_level=4))
    db.commit()

    data = build_weekly(db, today=TODAY)
    research = next(s for s in data.sections if s.key == "research")
    joined = " ".join(research.lines)
    assert "Small-data Forecasting" in joined
    assert "Explainability" in joined
    assert any("STM-SHAP" in line for line in research.lines)


def test_weekly_interviews_counts_this_week(db):
    from app.models.interview_log import InterviewLog

    db.add(InterviewLog(
        company="某大厂", role="LLM 算法", round="一面",
        asked_questions=[], weak_questions=["KV Cache 显存估算"],
        jd_gaps=[], knowledge_gaps=[], next_actions=[],
        interviewed_at=date(2026, 9, 9),  # 本周内
        generated_task_ids=[],
    ))
    db.add(InterviewLog(
        company="老东家", role="后端", round="一面",
        asked_questions=[], weak_questions=[], jd_gaps=[], knowledge_gaps=[],
        next_actions=[], interviewed_at=date(2026, 8, 20),  # 上周，不应计入
        generated_task_ids=[],
    ))
    db.commit()

    data = build_weekly(db, today=TODAY)
    assert data.metrics["interviews"]["count"] == 1
    assert data.metrics["interviews"]["weak_topics"][0]["topic"] == "KV Cache 显存估算"


# ─────────────────────────── API 层（TestClient 集成） ───────────────────────────

def test_api_reports_preview_and_schedule():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        daily = client.get("/api/reports/daily")
        assert daily.status_code == 200
        body = daily.json()
        assert body["success"] is True
        assert body["data"]["kind"] == "daily"
        assert len(body["data"]["sections"]) == 6

        weekly = client.get("/api/reports/weekly")
        assert weekly.status_code == 200
        assert weekly.json()["data"]["kind"] == "weekly"

        followups = client.get("/api/reports/followups")
        assert followups.status_code == 200
        assert "items" in followups.json()["data"]

        schedule = client.get("/api/reports/schedule")
        assert schedule.status_code == 200
        sdata = schedule.json()["data"]
        assert sdata["daily_time"] == "08:30"
        assert sdata["weekly_day"] == "mon"
        ids = {j["id"] for j in sdata["jobs"]}
        assert {"job_daily_report", "job_weekly_report", "job_followup_remind"} <= ids


def test_api_report_send_is_idempotent():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        first = client.post("/api/reports/daily/send?force=true")
        assert first.status_code == 200
        assert first.json()["data"]["sent"] is True

        # 同一 period_key 再次发送（不带 force）应跳过
        second = client.post("/api/reports/daily/send")
        assert second.status_code == 200
        payload = second.json()["data"]
        assert payload["skipped"] is True
        assert payload["sent"] is False

        # force 可强制重推
        third = client.post("/api/reports/daily/send?force=true")
        assert third.json()["data"]["sent"] is True

        history = client.get("/api/reports/history?kind=daily")
        assert history.status_code == 200
        assert len(history.json()["data"]) >= 1


def test_api_reports_bad_kind_rejected():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        assert client.post("/api/reports/bogus/send").status_code == 400
        assert client.get("/api/reports/history?kind=bogus").status_code == 400
