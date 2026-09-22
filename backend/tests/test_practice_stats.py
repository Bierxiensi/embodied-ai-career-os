"""自测练习统计端点测试（``GET /api/interview/practice/stats``）。

背景
----
题库的定位从「求职期 KPI」转为「存档 + 按需自测」（2026-09 留任决策）之后，
本端点成为用户查看自己学习效果的**唯一入口**，但此前**零测试覆盖**。
前端 ``PracticeStatsCard`` 直接消费它的返回结构，一旦字段漂移会静默渲染空白。

覆盖
----
  A. 空库分支 —— 未练习过时不得 500、不得除零，返回全零骨架
  B. 聚合语义（精确断言）—— 题型/技能正确率、weak_* 阈值(<50)、技能升序、最近测验
  C. 真实库冒烟（增量断言）—— 路由挂载正确、ORM 与 schema 不漂移

隔离
----
由 ``tests/conftest.py`` 提供会话级临时库。B 用自建独立库（依赖注入覆盖，天然无污染），
C 用真实库但只做增量断言 + 自清理。绝不碰开发库。
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, SessionLocal, get_db
from app.main import app
from app.models.interview_question import InterviewQuestion
from app.models.practice_record import PracticeRecord

client = TestClient(app)

STATS_URL = "/api/interview/practice/stats"


def _stats() -> dict:
    """取统计体，顺带校验统一响应包装。"""

    resp = client.get(STATS_URL)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True, body
    return body["data"]


@contextmanager
def _fresh_db(tmp_path):
    """在临时文件库上覆盖 ``get_db``，返回可控的会话工厂。

    用**文件**而非 ``sqlite://`` 内存库：TestClient 会把同步端点丢进线程池，
    内存库的 SingletonThreadPool 在不同线程上拿不到同一连接，表会"消失"。
    """

    engine = create_engine(f"sqlite:///{(tmp_path / 'practice.db').as_posix()}")
    # 使用全局 Base，确保 practice_records / interview_questions 都已注册
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def _override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    try:
        yield TestSession
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def _seed(TestSession, rows: list[dict]) -> None:
    db = TestSession()
    try:
        for r in rows:
            db.add(PracticeRecord(**r))
        db.commit()
    finally:
        db.close()


# ============================================================
# A. 空库分支
# ============================================================


def test_stats_empty_db_returns_zero_skeleton(tmp_path):
    """一次都没练过 → 全零骨架，不 500、不除零。"""

    with _fresh_db(tmp_path):
        data = _stats()

    assert data["total_practiced"] == 0
    assert data["total_correct"] == 0
    assert data["accuracy"] == 0
    assert data["by_type"] == {}
    assert data["by_skill"] == []
    assert data["weak_skills"] == []
    assert data["weak_types"] == []
    assert data["recent_sessions"] == []


# ============================================================
# B. 聚合语义（精确断言）
# ============================================================


def test_stats_aggregates_weak_and_recent(tmp_path):
    """弱项判定(<50)、技能升序、按题型统计、最近测验 —— 精确断言。

    数据：弱技能 2 题全错（open），强技能 2 题全对（choice），
    另在一场 quiz 会话里放 2 题（100 分 + 0 分 → 均分 50）。
    """

    rows = [
        # 弱技能：0/2
        dict(question_id=900001, question_type="open", user_answer="a",
             correct=False, score=0, skill_name="TEST_WEAK_SKILL",
             mode="single", session_id=None),
        dict(question_id=900002, question_type="open", user_answer="b",
             correct=False, score=20, skill_name="TEST_WEAK_SKILL",
             mode="single", session_id=None),
        # 强技能：2/2
        dict(question_id=900003, question_type="choice", user_answer="A",
             correct=True, score=100, skill_name="TEST_STRONG_SKILL",
             mode="single", session_id=None),
        dict(question_id=900004, question_type="choice", user_answer="B",
             correct=True, score=100, skill_name="TEST_STRONG_SKILL",
             mode="single", session_id=None),
        # 一场测验：满分 + 零分，均分 50
        dict(question_id=900005, question_type="judge", user_answer="正确",
             correct=True, score=100, skill_name="TEST_STRONG_SKILL",
             mode="quiz", session_id="quiz_test_B"),
        dict(question_id=900006, question_type="judge", user_answer="错误",
             correct=False, score=0, skill_name="TEST_WEAK_SKILL",
             mode="quiz", session_id="quiz_test_B"),
    ]

    with _fresh_db(tmp_path) as TestSession:
        _seed(TestSession, rows)
        data = _stats()

    # 总量：6 条，答对 3 条 → 50%
    assert data["total_practiced"] == 6
    assert data["total_correct"] == 3
    assert data["accuracy"] == 50.0

    # 按题型
    by_type = data["by_type"]
    assert by_type["open"]["practiced"] == 2
    assert by_type["open"]["correct"] == 0
    assert by_type["open"]["accuracy"] == 0.0
    assert by_type["choice"]["accuracy"] == 100.0
    assert by_type["judge"]["practiced"] == 2
    assert by_type["judge"]["accuracy"] == 50.0

    # 弱项阈值 strict < 50
    assert data["weak_skills"] == ["TEST_WEAK_SKILL"]
    assert data["weak_types"] == ["open"]

    # 技能按正确率升序（最弱的排最前）
    skills = [(s["skill"], s["accuracy"]) for s in data["by_skill"]]
    assert skills == [
        ("TEST_WEAK_SKILL", 0.0),      # 3 条全错
        ("TEST_STRONG_SKILL", 100.0),  # 3 条全对
    ]

    # 最近测验：唯一一场，2 题均分 50
    assert len(data["recent_sessions"]) == 1
    sess = data["recent_sessions"][0]
    assert sess["session_id"] == "quiz_test_B"
    assert sess["count"] == 2
    assert sess["score"] == 50.0
    assert sess["date"] and "-" in sess["date"]


def test_stats_weak_threshold_is_strictly_below_50(tmp_path):
    """恰好 50% 不算弱项 —— 阈值是 < 50 而非 <= 50。"""

    rows = [
        dict(question_id=910001, question_type="open", user_answer="a",
             correct=True, score=100, skill_name="TEST_BOUNDARY",
             mode="single", session_id=None),
        dict(question_id=910002, question_type="open", user_answer="b",
             correct=False, score=0, skill_name="TEST_BOUNDARY",
             mode="single", session_id=None),
    ]

    with _fresh_db(tmp_path) as TestSession:
        _seed(TestSession, rows)
        data = _stats()

    assert data["accuracy"] == 50.0
    assert data["weak_skills"] == []
    assert data["weak_types"] == []


def test_stats_ignores_records_without_skill_name(tmp_path):
    """没有 skill_name 的记录不进技能维度，但仍计入总量（否则正确率会虚高）。"""

    rows = [
        dict(question_id=920001, question_type="open", user_answer="a",
             correct=True, score=100, skill_name=None,
             mode="single", session_id=None),
        dict(question_id=920002, question_type="open", user_answer="b",
             correct=True, score=100, skill_name="TEST_ONLY_SKILL",
             mode="single", session_id=None),
    ]

    with _fresh_db(tmp_path) as TestSession:
        _seed(TestSession, rows)
        data = _stats()

    assert data["total_practiced"] == 2
    assert [s["skill"] for s in data["by_skill"]] == ["TEST_ONLY_SKILL"]


# ============================================================
# C. 真实库冒烟（增量断言 + 自清理）
# ============================================================


def test_stats_live_db_incremental_and_cleanup():
    """在真实（隔离）库上走一遍：路由挂载正确、ORM 与 schema 不漂移。

    只做增量断言，避免受同会话其他模块数据影响；结束后清理自己造的数据。
    """

    before = _stats()

    # 用 API 建题（拿到合法 id，满足外键约束）
    resp = client.post(
        "/api/interview-questions",
        json={
            "category": "LLM",
            "question": "practice-stats 冒烟题：KV Cache 的作用？",
            "skill_name": "TEST_STATS_SMOKE",
            "source_day_seq": 1,
            "answer_outline": "要点…",
        },
    )
    assert resp.status_code == 200, resp.text
    qid = resp.json()["data"]["id"]

    record_ids: list[int] = []
    db = SessionLocal()
    try:
        for correct, score in ((True, 100), (False, 0)):
            rec = PracticeRecord(
                question_id=qid,
                question_type="open",
                user_answer="冒烟答案",
                correct=correct,
                score=score,
                skill_name="TEST_STATS_SMOKE",
                mode="single",
            )
            db.add(rec)
        db.commit()
        record_ids = [
            r.id
            for r in db.query(PracticeRecord)
            .filter(PracticeRecord.skill_name == "TEST_STATS_SMOKE")
            .all()
        ]
        assert len(record_ids) == 2
    finally:
        db.close()

    try:
        after = _stats()
        assert after["total_practiced"] == before["total_practiced"] + 2
        assert after["total_correct"] == before["total_correct"] + 1
        smoke = next(s for s in after["by_skill"] if s["skill"] == "TEST_STATS_SMOKE")
        assert smoke["practiced"] == 2
        assert smoke["accuracy"] == 50.0
    finally:
        db = SessionLocal()
        try:
            db.query(PracticeRecord).filter(
                PracticeRecord.id.in_(record_ids)
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()
        client.delete(f"/api/interview-questions/{qid}")
