"""Project + Milestone Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


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


class ProjectReadmeIn(BaseModel):
    """保存 README。

    ``content`` 省略时，服务端用证据链**重新生成**骨架再保存（"一键导出"）；
    给定 ``content`` 时保存用户润色后的文本（"润色后回存"）。
    """

    content: str | None = None


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
    # 数据来源：user / seed / planner / test（见 migrations/0007）。
    # 列表接口默认已排除 source=test，避免测试残留淹没真实项目。
    source: str = "user"
    # 前端 #1 修复：list 接口附加里程碑进度统计（get 接口也填充）。
    # 声明为可选，create/patch 等不涉及统计的端点保持默认值，不破坏既有契约。
    milestone_total: int | None = None
    milestone_completed: int | None = None
    progress_pct: int | None = None

    @field_validator("source", mode="before")
    @classmethod
    def _default_source(cls, v):
        """未 flush 的 ORM 实例 source 为 None（列默认值插入时才生效），回落为 user。"""

        return v or "user"


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
    workspace: str | None = None
    required_modifications: list | None = None


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: str
    title: str
    goal: str
    status: str
    sort_order: int
    workspace: str | None = None
    required_modifications: list | None = None
    # 数据来源：user / seed / planner / test（见 migrations/0007）
    source: str = "user"

    @field_validator("source", mode="before")
    @classmethod
    def _default_source(cls, v):
        """未 flush 的 ORM 实例 source 为 None（列默认值插入时才生效），回落为 user。"""

        return v or "user"
