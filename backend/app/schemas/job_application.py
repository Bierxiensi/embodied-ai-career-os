"""JobApplication Pydantic 请求/响应模型。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class JobApplicationCreate(BaseModel):
    company: str
    role: str
    track: str = "other"
    source: str | None = None
    status: str = "applied"
    salary_range: str | None = None
    applied_at: date | None = None
    next_action: str | None = None
    notes: str | None = None


class JobApplicationPatch(BaseModel):
    company: str | None = None
    role: str | None = None
    track: str | None = None
    source: str | None = None
    status: str | None = None
    salary_range: str | None = None
    applied_at: date | None = None
    next_action: str | None = None
    notes: str | None = None


class JobApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company: str
    role: str
    track: str
    source: str | None = None
    status: str
    salary_range: str | None = None
    applied_at: date | None = None
    next_action: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
