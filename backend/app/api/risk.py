"""七维风险雷达 API（Phase 2）。

GET /api/risk —— 取数 + compute_risk，返回 RiskOut。
纯规则，无 LLM 依赖，LLM 未配置时全功能可用。

``build_risk_result(db, today)`` 同时被本端点与 /api/plan/today 复用，
避免两处各自取数导致口径漂移。
"""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.core.risk import (
    DEFENSE_DEADLINE,
    PHD_CONTACT_WINDOW,
    RiskResult,
    compute_risk,
    track_strict_pct,
)
from app.db.base import get_db
from app.models.day_artifact import ARTIFACT_KIND_CODE, DayArtifact
from app.models.experiment import Experiment
from app.models.phd import PhDAdvisor
from app.models.skill import Skill
from app.models.task import Task
from app.schemas.risk import RiskOut
from app.services.readiness.service import primary_role

router = APIRouter(prefix="/risk", tags=["risk"])


def _main_track():
    """返回主攻赛道（priority == '主攻'），无则返回 None。

    判定单点在 ``services/readiness.service.primary_role`` —— 这里保留一个
    同名的薄包装只为不打断既有调用点（本模块内 1 处）。
    """

    return primary_role()


def _days_since(dt) -> int | None:
    """从 datetime / 字符串取距今天数；None → None。"""

    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return (date.today() - dt.date()).days


def build_risk_result(db: Session, today: date | None = None) -> RiskResult:
    """取数 + compute_risk（today 可注入，便于测试固定日期）。"""

    today = today or date.today()

    # 执行力：最近实验 / 最近代码产物
    last_exp = db.query(func.max(Experiment.created_at)).scalar()
    last_code = (
        db.query(func.max(DayArtifact.created_at))
        .filter(DayArtifact.kind == ARTIFACT_KIND_CODE)
        .scalar()
    )
    days_since_exp = _days_since(last_exp)
    days_since_code = _days_since(last_code)

    # 学术：是否存在标题/目标含"答辩"的任务
    has_defense = (
        db.query(Task)
        .filter(
            Task.title.contains("答辩") | Task.objective.contains("答辩")
        )
        .first()
        is not None
    )
    defense_deadline_days = (DEFENSE_DEADLINE - today).days
    phd_window_days = (PHD_CONTACT_WINDOW - today).days

    # 博士：已联系导师数
    contacted = (
        db.query(func.count(PhDAdvisor.id))
        .filter(PhDAdvisor.contacted.is_(True))
        .scalar()
        or 0
    )

    # 主攻赛道 strict / gap
    role = _main_track()
    skill_levels = {s.name.lower(): s.level for s in db.query(Skill).all()}
    if role is not None:
        strict_pct, _, _ = track_strict_pct(
            role.required_skills, role.required_level, skill_levels
        )
        gaps = sum(
            1
            for name in role.required_skills
            if skill_levels.get(name.lower(), 0) < role.required_level
        )
        gap_ratio = (
            gaps / len(role.required_skills) if role.required_skills else 0.0
        )
    else:
        strict_pct, gap_ratio = 0, 0.0

    return compute_risk(
        days_since_last_experiment=days_since_exp,
        days_since_last_code_artifact=days_since_code,
        defense_deadline_days=defense_deadline_days,
        has_defense_task=has_defense,
        contacted_advisors=contacted,
        phd_window_days=phd_window_days,
        main_track_strict_pct=strict_pct,
        main_track_gap_ratio=gap_ratio,
        today=today,
    )


@router.get("")
def get_risk(db: Session = Depends(get_db)) -> ApiResponse[RiskOut]:
    """七维风险雷达。"""

    result = build_risk_result(db)
    return ok(RiskOut(**result.to_dict()))
