"""Project + Milestone Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# ---- Project ----

class ProjectCreate(BaseModel):
    name: str
    goal: str
    description: str | None = None
    status: str = "active"
    current_version: str = "V0"
    github_url: str | None = None
    sort_order: int = 0


class ProjectPatch(BaseModel):
    name: str | None = None
    goal: str | None = None
    description: str | None = None
    status: str | None = None
    current_version: str | None = None
    github_url: str | None = None
    sort_order: int | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    goal: str
    description: str | None = None
    status: str
    current_version: str
    github_url: str | None = None
    readme: str | None = None
    sort_order: int


# ---- Milestone ----

class MilestoneCreate(BaseModel):
    version: str
    title: str
    goal: str
    status: str = "locked"
    sort_order: int = 0


class MilestonePatch(BaseModel):
    version: str | None = None
    title: str | None = None
    goal: str | None = None
    status: str | None = None
    sort_order: int | None = None


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: str
    title: str
    goal: str
    status: str
    sort_order: int
