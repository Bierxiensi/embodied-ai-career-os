"""面试闭环引擎单测（Batch 3）。

覆盖：弱项聚合、弱项→任务草稿、知识缺口并入、题库抽题（分类/难度/命中次数/limit）、schema 校验。
全部为纯规则，不依赖 DB / LLM。
"""

from __future__ import annotations

import pytest

from app.agents.interview.engine import (
    WeakItem,
    pick_questions,
    weak_to_tasks,
    weakness_stats,
)
from app.schemas.interview import InterviewQuestionCreate


_LOGS = [
    {"id": 1, "weak_questions": ["KV Cache 显存估算", "FlashAttention 原理", ""]},
    {"id": 2, "weak_questions": ["KV Cache 显存估算", "LoRA 与 QLoRA 的取舍"]},
    {"id": 3, "weak_questions": ["KV Cache 显存估算"]},
]


_QUESTIONS = [
    {"id": 1, "category": "LLM", "question": "Q1", "difficulty": "intermediate", "hit_count": 5},
    {"id": 2, "category": "LLM", "question": "Q2", "difficulty": "advanced", "hit_count": 0},
    {"id": 3, "category": "LLM", "question": "Q3", "difficulty": "intermediate", "hit_count": 2},
    {"id": 4, "category": "Coding", "question": "Q4", "difficulty": "advanced", "hit_count": 1},
]


def test_weakness_stats_aggregates_and_sorts():
    stats = weakness_stats(_LOGS)
    assert stats[0].topic == "KV Cache 显存估算"
    assert stats[0].count == 3
    assert stats[0].log_ids == [1, 2, 3]
    # 其余两条各 1 次
    assert sorted(s.count for s in stats) == [1, 1, 3]


def test_weakness_stats_ignores_blank():
    stats = weakness_stats([{"id": 9, "weak_questions": ["", "   "]}, {"id": 10, "weak_questions": None}])
    assert stats == []


def test_weak_to_tasks_maps_and_limits():
    stats = weakness_stats(_LOGS)
    drafts = weak_to_tasks(stats, limit=2)
    assert len(drafts) == 2
    assert drafts[0].title.startswith("补强：")
    assert drafts[0].title == "补强：KV Cache 显存估算"
    assert drafts[0].acceptance  # 非空验收标准
    assert drafts[0].duration == 40


def test_weak_to_tasks_includes_gaps_without_dup():
    stats = [WeakItem(topic="KV Cache 显存估算", count=3, log_ids=[1])]
    drafts = weak_to_tasks(stats, gaps=["KV Cache 显存估算", "vLLM PagedAttention"], limit=5)
    titles = [d.title for d in drafts]
    assert titles == ["补强：KV Cache 显存估算", "补强：vLLM PagedAttention"]  # 去重


def test_pick_questions_filter_category():
    picked = pick_questions(_QUESTIONS, category="Coding", limit=10)
    assert [q["id"] for q in picked] == [4]


def test_pick_questions_prefers_low_hit_count():
    picked = pick_questions(_QUESTIONS, category="LLM", limit=10)
    # hit_count: Q2(0) < Q3(2) < Q1(5)
    assert [q["id"] for q in picked] == [2, 3, 1]


def test_pick_questions_limit_and_difficulty():
    picked = pick_questions(_QUESTIONS, difficulty="advanced", limit=1)
    assert len(picked) == 1
    assert picked[0]["difficulty"] == "advanced"


def test_question_create_rejects_bad_category():
    with pytest.raises(ValueError):
        InterviewQuestionCreate(category="Bogus", question="x")


def test_question_create_rejects_bad_difficulty():
    with pytest.raises(ValueError):
        InterviewQuestionCreate(category="LLM", question="x", difficulty="impossible")


def test_question_create_accepts_valid():
    q = InterviewQuestionCreate(category="LLM", question="x", difficulty="advanced")
    assert q.category == "LLM"
    assert q.difficulty == "advanced"
