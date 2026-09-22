"""风险雷达 + Career ROI 响应模型（Phase 2）。"""

from __future__ import annotations

from pydantic import BaseModel


class RiskDimensionOut(BaseModel):
    """单个风险维度。"""

    key: str
    label: str
    level: str          # green | amber | red
    reason: str


class RiskOut(BaseModel):
    """七维风险聚合。"""

    dimensions: list[RiskDimensionOut] = []
    overall_level: str = "green"   # 取最差维度


class RoiTaskOut(BaseModel):
    """单个任务的 ROI 排序项（Top5 视图）。"""

    task_id: int
    title: str
    skill_name: str | None = None
    roi: float
    reasons: list[str] = []
