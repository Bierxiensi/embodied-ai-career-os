"""CareerMode / ModeTransition 的 Pydantic 请求/响应契约。

产品依据：docs/PRD_CAREER_OS_MODES.md §7.1（字段定义）、§7.2（接口约束）
约束：所有 API 保持 ``/api`` 前缀与 ``{ "data": ... }`` 统一包裹；新增字段一律
可选并提供默认值，现有前端页面不因字段缺失崩溃。
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CareerModeOut(BaseModel):
    """一个职业阶段模式对外暴露的字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name: str
    objective: str
    # NULL = 该阶段无硬截止（长期转型按季度 / 里程碑推进）
    deadline: date | None = None
    # 该阶段推动的赛道 key；Milestone A 只存不执行（过滤口径属于 Milestone B）
    active_track_keys: list[str] = Field(default_factory=list)
    # 该阶段冻结的赛道 key：只看不推，历史资产保留
    frozen_track_keys: list[str] = Field(default_factory=list)
    is_current: bool

    @computed_field
    @property
    def days_left(self) -> int | None:
        """距 ``deadline`` 的剩余天数；无 deadline 时为 None。

        放在契约层而不是路由里：路由只做 HTTP，"还有多少天"是对响应数据的推导。
        也刻意不在前端重算一遍 —— 否则后端显示 45 天、前端显示 44 天这种取整/时区
        不一致会被当成 bug 反复排查。
        """

        if self.deadline is None:
            return None
        return (self.deadline - date.today()).days


class CareerModeOverview(BaseModel):
    """``GET /api/career-mode`` 的 data：当前模式 + 可切换的全部模式。"""

    current: CareerModeOut
    available: list[CareerModeOut]


class ModeTransitionOut(BaseModel):
    """一次模式切换的历史记录。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    # None = 系统首次激活默认模式，不是用户切换
    from_mode: str | None = None
    to_mode: str
    transitioned_at: datetime
    note: str | None = None


class ModeSwitchRequest(BaseModel):
    """``POST /api/career-mode/switch`` 入参。"""

    mode_key: str = Field(
        min_length=1, max_length=40, description="目标模式 key，如 job_hunt"
    )
    note: str | None = Field(
        default=None, max_length=500, description="切换原因（可选，记入历史）"
    )


class ModeSwitchResult(BaseModel):
    """切换成功的返回：切换后的模式 + 本次切换记录。"""

    current: CareerModeOut
    transition: ModeTransitionOut
