"""Task Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskOut(BaseModel):
    """Task 响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    objective: str | None = None
    duration: int | None = None
    difficulty: str | None = None
    status: str
    skill_name: str | None = None
    acceptance: list[str] = []
    resources: list[str] = []
    project_id: int | None = None
    milestone_id: int | None = None

    @field_validator("acceptance", "resources", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        """数据库 JSON 字段可能为 None，统一转为空列表。"""

        return v or []


class TaskCreate(BaseModel):
    """Task 创建请求。对齐 Planner TaskOutput 结构。"""

    title: str
    objective: str | None = None
    duration: int | None = Field(default=None, ge=1, le=480)
    difficulty: str | None = None
    skill_name: str | None = None
    acceptance: list[str] = []
    resources: list[str] = []
    status: str = "todo"
    project_id: int | None = None
    milestone_id: int | None = None


class TaskStatusPatch(BaseModel):
    """Task 状态更新请求。仅允许改状态（todo/doing/done）。"""

    status: str = Field(pattern="^(todo|doing|done)$")
