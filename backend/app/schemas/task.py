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
    # 数据来源：user / seed / planner / test（见 migrations/0007）。
    # 前端可据此过滤测试残留；列表接口默认已排除 source=test。
    source: str = "user"
    # 任务所属赛道：llm / vlm / ai-algo / embodied（见 migrations/0008）。
    # 看板按视角过滤任务用；NULL = 未归类（历史 / 手写任务）。
    track_key: str | None = None
    # 归属课程第几天（plan_days.id，见 migrations/0011）。
    # 与 track_key 正交：track_key 说「属于哪条赛道」，plan_day_id 说「属于课程第几天」。
    plan_day_id: int | None = None

    @field_validator("acceptance", "resources", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        """数据库 JSON 字段可能为 None，统一转为空列表。"""

        return v or []

    @field_validator("source", mode="before")
    @classmethod
    def _default_source(cls, v):
        """未 flush 的 ORM 实例 source 仍是 None（列默认值在插入时才生效），
        统一回落为 "user"，避免响应模型校验失败。"""

        return v or "user"


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
    # 不传则由模型默认 "user"；测试/脚本写入时显式传 "test"
    source: str | None = None
    # 所属赛道：llm / vlm / ai-algo / embodied；不传 = 未归类
    track_key: str | None = None
    # 归属课程第几天（plan_days.id）；不传 = 不对应任何课程日
    plan_day_id: int | None = None


class TaskStatusPatch(BaseModel):
    """Task 状态更新请求。仅允许改状态（todo/doing/done）。"""

    status: str = Field(pattern="^(todo|doing|done)$")
