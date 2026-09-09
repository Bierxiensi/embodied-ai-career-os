"""求职投递 API。CRUD + 漏斗统计。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.base import get_db
from app.models.job_application import STATUS_ORDER, JobApplication
from app.schemas.job_application import (
    JobApplicationCreate,
    JobApplicationOut,
    JobApplicationPatch,
)

router = APIRouter(prefix="/job-applications", tags=["job-applications"])


@router.get("")
def list_applications(db: Session = Depends(get_db)):
    """获取全部投递记录，按状态漏斗顺序 + 更新时间倒序。"""
    rows = db.query(JobApplication).all()

    order = {s: i for i, s in enumerate(STATUS_ORDER)}
    rows.sort(key=lambda r: (order.get(r.status, 99), -(r.updated_at.timestamp() if r.updated_at else 0)))
    return ok([JobApplicationOut.model_validate(r) for r in rows])


@router.post("")
def create_application(payload: JobApplicationCreate, db: Session = Depends(get_db)):
    """新增投递记录。"""
    row = JobApplication(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(JobApplicationOut.model_validate(row), "已添加投递记录")


@router.patch("/{application_id}")
def patch_application(
    application_id: int, payload: JobApplicationPatch, db: Session = Depends(get_db)
):
    """更新投递记录（状态流转、下一步动作、备注）。"""
    row = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="投递记录不存在")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ok(JobApplicationOut.model_validate(row), "已更新")


@router.delete("/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    """删除投递记录。"""
    row = db.query(JobApplication).filter(JobApplication.id == application_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    db.delete(row)
    db.commit()
    return ok(None, "已删除")


@router.get("/stats")
def application_stats(db: Session = Depends(get_db)):
    """漏斗统计：各状态数量 + 转化率。"""
    rows = db.query(JobApplication.status, func.count(JobApplication.id)).group_by(
        JobApplication.status
    ).all()
    counts = {s: 0 for s in STATUS_ORDER}
    for status, count in rows:
        counts[status] = counts.get(status, 0) + int(count)

    total = sum(counts.values())
    screening_plus = counts.get("screening", 0) + counts.get("interview", 0) + counts.get("offer", 0)
    return ok({
        "total": total,
        "by_status": counts,
        "response_rate": round(screening_plus / total * 100) if total else 0,
        "interview_count": counts.get("interview", 0) + counts.get("offer", 0),
        "offer_count": counts.get("offer", 0),
    })
