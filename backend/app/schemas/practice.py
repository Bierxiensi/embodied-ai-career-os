"""练习与测验 Pydantic schemas。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator
import json


# ─── 答题请求 / 响应 ───────────────────────────────────────────

class PracticeIn(BaseModel):
    """单题答题请求。"""

    question_id: int
    question_type: str = "open"  # open / choice / fill / judge
    user_answer: str
    generated_options: list[str] | None = None  # LLM 生成的选项（回传评分上下文）
    skill_name: str | None = None
    mode: str = "single"  # single / quiz
    session_id: str | None = None


class PracticeOut(BaseModel):
    """单题答题结果。"""

    model_config = ConfigDict(from_attributes=True)

    correct: bool
    score: int
    max_score: int = 100
    feedback: str
    correct_answer: str
    outline_covered: list[str]
    outline_missed: list[str]
    record_id: int

    @field_validator("outline_covered", "outline_missed", mode="before")
    @classmethod
    def _parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return []
        return v if isinstance(v, list) else []


# ─── 小测验 ─────────────────────────────────────────────────

class QuizStartIn(BaseModel):
    """开始小测验请求。"""

    skill_name: str | None = None
    category: str | None = None
    count: int = 10


class QuizQuestionOut(BaseModel):
    """测验中的单题（不含答案）。"""

    id: int
    question: str
    question_type: str
    options: list[str] | None = None  # 选择题的选项
    skill_name: str | None = None
    difficulty: str = "intermediate"

    @field_validator("options", mode="before")
    @classmethod
    def _parse_options(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed.get("choices") if isinstance(parsed, dict) else parsed
            except (json.JSONDecodeError, ValueError):
                return None
        return v


class QuizStartOut(BaseModel):
    """测验开始响应。"""

    session_id: str
    questions: list[QuizQuestionOut]
    count: int


class QuizRecordOut(BaseModel):
    """测验中的一条答题记录。"""

    model_config = ConfigDict(from_attributes=True)

    question_id: int
    question_type: str
    question: str
    user_answer: str
    correct_answer: str | None = None
    correct: bool
    score: int
    feedback: str | None = None

    @field_validator("correct", mode="before")
    @classmethod
    def _parse_correct(cls, v):
        return bool(v)


class QuizTypeStats(BaseModel):
    """某题型的统计。"""

    count: int
    correct: int
    avg_score: float


class QuizResultOut(BaseModel):
    """测验结果。"""

    session_id: str
    total_score: float
    count: int
    correct_count: int
    by_type: dict[str, QuizTypeStats]
    weak_skills: list[str]
    records: list[QuizRecordOut]


# ─── 练习统计 ───────────────────────────────────────────────

class PracticeTypeStats(BaseModel):
    """某题型的练习统计。"""

    practiced: int
    correct: int
    accuracy: float


class PracticeSkillStats(BaseModel):
    """某技能的练习统计。"""

    skill: str
    practiced: int
    correct: int
    accuracy: float


class PracticeSessionSummary(BaseModel):
    """一次测验的摘要。"""

    session_id: str
    date: str
    score: float
    count: int


class PracticeStatsOut(BaseModel):
    """练习总统计。"""

    total_practiced: int
    total_correct: int
    accuracy: float
    by_type: dict[str, PracticeTypeStats]
    by_skill: list[PracticeSkillStats]
    weak_skills: list[str]
    weak_types: list[str]
    recent_sessions: list[PracticeSessionSummary]
