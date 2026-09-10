"""课程计划（Plan）Pydantic 模型。

对应 /api/plan 系列端点：30 天总览 + 今日施工单 + 四件套勾选。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.task import TaskOut


class PlanDayOut(BaseModel):
    """课程日响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    seq: int
    phase: int
    phase_name: str
    title: str
    theme: str
    objectives: list[str] = []
    acceptance: list[str] = []
    interview_topics: list[str] = []
    resources: list[str] = []
    est_minutes: int = 360
    track_key: str = "llm"

    @field_validator(
        "objectives", "acceptance", "interview_topics", "resources", mode="before"
    )
    @classmethod
    def _none_to_list(cls, v):
        """数据库 JSON 字段可能为 None，统一转空列表。

        另注意 Pydantic v2 from_attributes 的已知坑：未 flush 的 ORM 实例上
        列默认值尚未生效（见 MEMORY.md），因此 track_key / est_minutes 也要有兜底。
        """

        return v or []

    @field_validator("track_key", mode="before")
    @classmethod
    def _default_track(cls, v):
        return v or "llm"

    @field_validator("est_minutes", mode="before")
    @classmethod
    def _default_minutes(cls, v):
        return v if v else 360


class ArtifactOut(BaseModel):
    """每日产出响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_day_id: int
    kind: str
    title: str | None = None
    url: str | None = None
    auto_verified: bool = False
    note: str | None = None
    created_at: datetime


class ArtifactCreate(BaseModel):
    """勾选一件产出（或取消勾选的反向操作由 DELETE 承担）。"""

    plan_day_id: int
    kind: str = Field(pattern="^(code|note|questions|commit)$")
    title: str | None = None
    url: str | None = None
    note: str | None = None


class LedgerItem(BaseModel):
    """「总账」的一行：某项产出累计进度。

    计划 §十：30 天应累计 30 段代码 + 30 篇笔记 + 150 道面试题 + 30 个 commit。
    """

    key: str        # code / note / commit / questions / days
    label: str      # 代码 / 笔记 / commit / 面试题 / 完整天数
    done: int
    target: int


class TodayView(BaseModel):
    """今日施工单。

    回答三个问题：今天第几天（day）、今天干什么（day.title / objectives）、
    今天做完没有（all_done / missing_kinds）。
    """

    day: PlanDayOut

    # 今天算课程第几天（由日历推导，clamp 到 1..30）
    day_index: int
    total_days: int

    # 日历口径，用于 P1 的落后量计算与当前页面的偏差提示
    calendar_days_elapsed: int
    sprint_start: str
    is_before_start: bool
    is_after_end: bool

    # 今日任务（tasks.plan_day_id == day.id）
    tasks: list[TaskOut] = []
    completed_tasks: int = 0

    # 四件套状态
    artifacts: list[ArtifactOut] = []
    artifact_status: dict[str, int] = {}   # kind -> 已交条数
    missing_kinds: list[str] = []
    all_done: bool = False

    # 总账（跨全部 30 天累计）
    ledger: list[LedgerItem] = []
