"""博士模块 Pydantic 请求 / 响应模型。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---- ResearchDirection ----

class ResearchDirectionCreate(BaseModel):
    key: str = Field(..., max_length=40)
    name: str = Field(..., max_length=100)
    description: str | None = None
    interest_weight: int = 70


class ResearchDirectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    description: str | None = None
    interest_weight: int
    created_at: datetime


# ---- PhDTarget ----

class PhDTargetCreate(BaseModel):
    institution: str = Field(..., max_length=200)
    city: str | None = None
    tier: str | None = None
    direction_key: str | None = None
    track_key: str | None = None
    in_service_friendly: bool = False
    min_publication: str | None = None
    application_deadline: date | None = None
    notes: str | None = None
    source: str = "user"


class PhDTargetPatch(BaseModel):
    institution: str | None = None
    city: str | None = None
    tier: str | None = None
    direction_key: str | None = None
    track_key: str | None = None
    in_service_friendly: bool | None = None
    min_publication: str | None = None
    application_deadline: date | None = None
    notes: str | None = None


class PhDTargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution: str
    city: str | None = None
    tier: str | None = None
    direction_key: str | None = None
    track_key: str | None = None
    in_service_friendly: bool
    min_publication: str | None = None
    application_deadline: date | None = None
    notes: str | None = None
    source: str = "user"


# ---- PhDAdvisor ----

class PhDAdvisorCreate(BaseModel):
    target_id: int | None = None
    name: str = Field(..., max_length=100)
    title: str | None = None
    research_area: str | None = None
    recruiting: bool = True
    in_service_friendly: bool = False
    homepage: str | None = None
    notes: str | None = None
    contacted: bool = False
    contact_date: datetime | None = None
    source: str = "user"


class PhDAdvisorPatch(BaseModel):
    target_id: int | None = None
    name: str | None = None
    title: str | None = None
    research_area: str | None = None
    recruiting: bool | None = None
    in_service_friendly: bool | None = None
    homepage: str | None = None
    notes: str | None = None
    contacted: bool | None = None
    contact_date: datetime | None = None


class PhDAdvisorOut(BaseModel):
    """导师响应（含从所属机会反查的展示字段，便于前端直接渲染）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int | None = None
    name: str
    title: str | None = None
    research_area: str | None = None
    recruiting: bool
    in_service_friendly: bool
    homepage: str | None = None
    notes: str | None = None
    match_json: dict | None = None
    last_matched_at: datetime | None = None
    contacted: bool = False
    contact_date: datetime | None = None
    source: str = "user"

    # 反查字段（API 层填充，非 ORM 列）
    institution: str | None = None
    city: str | None = None
    tier: str | None = None
    direction_key: str | None = None
    track_key: str | None = None
    application_deadline: date | None = None

    @field_validator("source", mode="before")
    @classmethod
    def _default_source(cls, v):
        """未 flush 的 ORM 实例 source 为 None，回落为 user（与 project 一致）。"""

        return v or "user"
