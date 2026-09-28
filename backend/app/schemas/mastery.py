"""掌握单元 Pydantic 契约（API 层 snake_case，前端 service 转 camelCase）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UnitItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    kind: str
    body: str
    # answer/rationale 不随 GET 单元返回（防提前看答案）；测验判定后由响应单独给出
    is_verified: bool = False
    verified_at: datetime | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    source_ref: str
    title: str
    skill_ids: list[str] = []
    day_seq: int | None = None
    generation_mode: str
    status: str
    items: list[UnitItemOut] = []


class AnswerIn(BaseModel):
    item_id: int
    answer: str = Field(min_length=1, max_length=2000)


class AnswerOut(BaseModel):
    item_id: int
    correct: bool
    verified: bool
    rationale: str | None = None
    card_id: int | None = None


class ReviewIn(BaseModel):
    rating: str = Field(pattern="^(again|hard|good|easy)$")
    duration_seconds: int | None = Field(default=None, ge=0, le=3600)


class ReviewCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    front: str
    back: str
    due_at: datetime
    interval_days: float
    ef: float
    lapse_count: int
    good_streak: int
    card_status: str
