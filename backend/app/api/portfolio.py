"""作品集组装 API（只读）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.services.packaging.portfolio import build_portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/assemble")
def assemble(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    return ok(build_portfolio(db))
