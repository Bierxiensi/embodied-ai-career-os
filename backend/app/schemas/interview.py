"""面试线 Pydantic 请求 / 响应模型（Batch 3）。

面经（InterviewLog）与题库（InterviewQuestion）分离；
弱项统计 / 任务草稿 / 抽题结果由 engine 产出，这里只定义出入参。
"""

from __future__ import annotations

import json
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.interview_question import (
    DIFFICULTIES,
    QUESTION_CATEGORIES,
)


# ───────────────────────────── 面经 ─────────────────────────────

class InterviewLogCreate(BaseModel):
    """记录一条面经。"""

    company: str
    role: str
    round: str | None = None
    asked_questions: list[str] = []
    weak_questions: list[str] = []
    jd_gaps: list[str] = []
    knowledge_gaps: list[str] = []
    next_actions: list[str] = []
    interviewed_at: date | None = None
    notes: str | None = None


class InterviewLogOut(BaseModel):
    """面经出参。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    round: str | None = None
    asked_questions: list | None = None
    weak_questions: list | None = None
    jd_gaps: list | None = None
    knowledge_gaps: list | None = None
    next_actions: list | None = None
    interviewed_at: date | None = None
    notes: str | None = None
    generated_task_ids: list | None = None
    created_at: datetime
    updated_at: datetime


# ───────────────────────────── 题库 ─────────────────────────────

class InterviewQuestionCreate(BaseModel):
    """新增题目。"""

    category: str
    question: str
    difficulty: str = "intermediate"
    answer_outline: str | None = None
    source: str | None = None
    # P2：归属课程日 / 关联技能 / 是否验证（用于四件套 questions 自动判定）
    source_day_seq: int | None = None
    skill_name: str | None = None
    is_verified: bool = False
    question_type: str = "open"
    options: dict | None = None  # {"choices": [...], "correct": "B"}

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        if self.category not in QUESTION_CATEGORIES:
            raise ValueError(f"category 必须为 {QUESTION_CATEGORIES} 之一，收到：{self.category}")
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(f"difficulty 必须为 {DIFFICULTIES} 之一，收到：{self.difficulty}")


class InterviewQuestionPatch(BaseModel):
    """部分更新题目（标记已练习 / 已验证等）。"""

    category: str | None = None
    question: str | None = None
    difficulty: str | None = None
    answer_outline: str | None = None
    source: str | None = None
    source_day_seq: int | None = None
    skill_name: str | None = None
    is_verified: bool | None = None
    hit_count: int | None = None
    question_type: str | None = None
    options: dict | None = None


class InterviewQuestionOut(BaseModel):
    """题目出参。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    question: str
    difficulty: str
    answer_outline: str | None = None
    source: str | None = None
    source_day_seq: int | None = None
    skill_name: str | None = None
    is_verified: bool = False
    hit_count: int
    question_type: str = "open"
    options: str | None = None  # JSON string from DB
    created_at: datetime
    updated_at: datetime

    @field_validator("options", mode="before")
    @classmethod
    def _parse_options_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return v
        return v


# ───────────────────────────── 统计 / 生成 ─────────────────────────────

class WeakStatOut(BaseModel):
    topic: str
    count: int
    log_ids: list[int] = []


class TaskDraftOut(BaseModel):
    title: str
    objective: str
    duration: int
    difficulty: str
    skill_name: str | None = None
    acceptance: list[str] = []


class ToTasksIn(BaseModel):
    """弱项 → 学习任务入参。"""

    limit: int = 5
    duration: int = 40


class SimulateIn(BaseModel):
    """模拟面试抽题入参。"""

    category: str | None = None
    difficulty: str | None = None
    skill_name: str | None = None
    limit: int = 5


# ───────────────────────── 题库覆盖率（P3） ─────────────────────────

class CoverageCategoryOut(BaseModel):
    """一个分类的进度（done vs target）。"""

    key: str
    done: int
    target: int
    gap: int
    core: bool = False


class CoverageSkillOut(BaseModel):
    """技能行：四分类计数 + 缺口。"""

    name: str
    total: int
    gap: int
    # 红格：该技能在哪些分类里一题都没有
    missing: list[str] = []
    counts: dict[str, int] = {}


class QuestionCoverageOut(BaseModel):
    """题库覆盖率总览（GET /api/interview-questions/coverage）。"""

    total: int
    target_total: int
    core_target: int
    core_done: int
    per_skill_target: int
    categories: list[CoverageCategoryOut] = []
    skills: list[CoverageSkillOut] = []
    cells_total: int
    cells_filled: int
