"""Career API 路由。

Day6 范围：GET + PUT（个人系统，无需多用户/删除）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, fail, ok
from app.db.base import get_db
from app.models.career import Career
from app.schemas.career import CareerOut, CareerUpdate

router = APIRouter(prefix="/career", tags=["career"])


@router.get("")
def get_career(db: Session = Depends(get_db)) -> ApiResponse[CareerOut]:
    """获取当前职业目标。单用户系统，返回第一条记录。"""

    career = db.query(Career).order_by(Career.id).first()
    if not career:
        return fail(message="Career not configured", data=None)
    return ok(CareerOut.model_validate(career))


@router.put("")
def upsert_career(
    payload: CareerUpdate, db: Session = Depends(get_db)
) -> ApiResponse[CareerOut]:
    """更新或创建职业目标。

    单用户系统：若存在则更新第一条，否则创建。
    """

    career = db.query(Career).order_by(Career.id).first()
    if career is None:
        # 创建：target_role 必填
        if not payload.target_role:
            raise HTTPException(status_code=422, detail="target_role required on create")
        career = Career(target_role=payload.target_role)
        db.add(career)
    else:
        # 更新：仅覆盖非 None 字段
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(career, field, value)

    db.commit()
    db.refresh(career)
    return ok(CareerOut.model_validate(career), message="Career updated")
