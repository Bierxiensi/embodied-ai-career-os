"""职业阶段模式 API（Milestone A：模式骨架）。

端点：
    GET  /api/career-mode              当前模式 + 可切换的全部模式
    POST /api/career-mode/switch       切换模式（写一条切换历史）
    GET  /api/career-mode/transitions  切换历史（最近在前）

本文件只做三件事：接参 → 调 ``app/services/career_mode`` → 返回统一 ``{ data }``
包裹。"当前模式是什么""切换意味着什么""切换会不会动到历史数据"全部是 service
层的事，路由不复制任何业务判断（docs/CODEX_MODULAR_DESIGN_STANDARD.md §2）。

失败语义：
    400  目标模式不存在（用户可执行：从 available 里选一个）
    409  当前已是该模式（不是错误状态，但也没有任何变更需要落库）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.schemas.career_mode import (
    CareerModeOut,
    CareerModeOverview,
    ModeSwitchRequest,
    ModeSwitchResult,
    ModeTransitionOut,
)
from app.services.career_mode import service as career_mode_service
from app.services.career_mode.service import (
    ModeAlreadyCurrentError,
    UnknownCareerModeError,
)

router = APIRouter(prefix="/career-mode", tags=["career-mode"])


@router.get("")
def get_career_mode(db: Session = Depends(get_db)) -> ApiResponse[CareerModeOverview]:
    """当前模式 + 全部可选模式（供全局导航展示与切换器渲染）。"""

    current = career_mode_service.get_current_mode(db)
    available = career_mode_service.list_modes(db)

    return ok(
        CareerModeOverview(
            current=CareerModeOut.model_validate(current),
            available=[CareerModeOut.model_validate(row) for row in available],
        )
    )


@router.post("/switch")
def switch_career_mode(
    payload: ModeSwitchRequest, db: Session = Depends(get_db)
) -> ApiResponse[ModeSwitchResult]:
    """切换当前模式。

    切换只改变"当前阶段"，不会删除、修改或隐藏任何既有职业目标、岗位、任务、
    投递与面试记录 —— 这是 PRD §5 F1.3 对用户的承诺，由表结构保证（模式表不持有
    业务数据引用，见 app/models/career_mode.py）。
    """

    try:
        mode, transition = career_mode_service.switch_mode(
            db, payload.mode_key, payload.note
        )
    except UnknownCareerModeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ModeAlreadyCurrentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return ok(
        ModeSwitchResult(
            current=CareerModeOut.model_validate(mode),
            transition=ModeTransitionOut.model_validate(transition),
        ),
        message=f"已切换到「{mode.name}」",
    )


@router.get("/transitions")
def list_mode_transitions(
    db: Session = Depends(get_db),
) -> ApiResponse[list[ModeTransitionOut]]:
    """模式切换历史，最近的在最前。"""

    rows = career_mode_service.list_transitions(db)
    return ok([ModeTransitionOut.model_validate(row) for row in rows])
