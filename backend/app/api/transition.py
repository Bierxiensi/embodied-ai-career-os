"""统一落地页聚合 API（Phase 3）。

端点：
    GET /api/transition/dashboard    Career Transition Dashboard 的三区数据
                                     （职业进度 / 当前工作 / 学术与博士）

本文件只做三件事：接参 → 调 service → 返回统一 ``{ data }`` 包裹。
"哪五个区、每区取哪个真源"全部是 service 层的事，
路由不复制任何业务判断（docs/CODEX_MODULAR_DESIGN_STANDARD.md §2）。

为什么与 /api/plan/today 分开：
    today 回答"今天干什么"（随日期变化：当日任务、当日 ROI 排序、当日风险）；
    本端点回答"这四条线现在各到哪儿了"（与日期无关的进度事实）。
    拆开之后 /today 页并行拉两个端点即可；合并会让 plan 路由承担职业与学业职责。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.schemas.transition import TransitionDashboard
from app.services.transition import service as transition_service

router = APIRouter(prefix="/transition", tags=["transition"])


@router.get("/dashboard")
def get_transition_dashboard(
    db: Session = Depends(get_db),
) -> ApiResponse[TransitionDashboard]:
    """Career Transition Dashboard 聚合数据。

    就绪度与 ``/api/job-hunt`` 同源（都走 services/readiness）——
    两页的"离岗位差多少"必须一致，否则用户无从判断哪个数字可信。
    """

    payload = transition_service.build_dashboard(db, today=date.today())
    return ok(TransitionDashboard(**payload))
