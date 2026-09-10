"""报告 Pydantic 出参模型（Batch 4）。

日报 / 周报由 ``services/report/engine`` 计算、``services/report/service`` 落库推送；
这里只定义 API 的出入参形状。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReportSectionOut(BaseModel):
    """报告的一段（key 供前端定位，title 为展示标题）。"""

    key: str
    title: str
    lines: list[str] = []


class ReportOut(BaseModel):
    """即时构建的报告（GET /api/reports/{kind}）。"""

    kind: str
    period_key: str
    title: str
    sections: list[ReportSectionOut] = []
    metrics: dict = {}
    generated_at: str


class ReportLogOut(BaseModel):
    """归档报告（GET /api/reports/history）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    period_key: str
    title: str
    body: str
    sections: list | None = None
    metrics: dict | None = None
    sent: bool
    sent_at: str | None = None
    generated_at: str | None = None


class FollowupOut(BaseModel):
    """待跟进投递。"""

    id: int
    company: str
    role: str
    status: str
    next_action: str | None = None
    reason: str
    days: int
    overdue: bool = False


class SendResultOut(BaseModel):
    """推送结果（POST /api/reports/{kind}/send）。"""

    kind: str
    period_key: str
    sent: bool
    skipped: bool
    reason: str | None = None
    title: str | None = None


class JobInfoOut(BaseModel):
    """调度器中的 job。"""

    id: str
    trigger: str
    next_run: str | None = None


class ScheduleOut(BaseModel):
    """报告调度总览。"""

    enabled: bool
    daily_time: str
    weekly_day: str
    weekly_time: str
    followup_time: str
    followup_stale_days: int
    channel: str
    jobs: list[JobInfoOut] = []
