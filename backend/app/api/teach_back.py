"""Teach-Back API：一次口述回收 = 一份自动学习日志 + 错项复习卡（intake 之一）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.core.sm2 import initial_card
from app.db.base import get_db
from app.models.learning_log import LearningLog
from app.models.mastery import MasteryUnit, ReviewCard, UnitItem
from app.services.evidence_events import record_evidence_event
from app.services.mastery.teachback import judge_answer

router = APIRouter(prefix="/teach-back", tags=["teach-back"])


class SpokenIn(BaseModel):
    item_id: int
    spoken: str = Field(min_length=1, max_length=2000)


class TeachBackIn(BaseModel):
    unit_id: int
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    answers: list[SpokenIn] = Field(min_length=1, max_length=10)


@router.post("/complete")
def complete(
    payload: TeachBackIn, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    unit = db.get(MasteryUnit, payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")

    verdicts = []
    lines = []
    cards_created = 0
    for ans in payload.answers:
        item = db.get(UnitItem, ans.item_id)
        if item is None or item.unit_id != unit.id:
            raise HTTPException(status_code=404, detail=f"Item {ans.item_id} not found")
        verdict = judge_answer(item.body, item.answer or "", ans.spoken)
        passed = bool(verdict["passed"])
        verdicts.append({
            "item_id": item.id,
            "passed": passed,
            "judge_mode": str(verdict["mode"]),  # 降级可见：判定是 LLM 给的还是规则兜底
            "hint": None if passed else (item.rationale or "重读本题对应概念卡"),
        })
        lines.append(f"[{'通过' if passed else '待复习'}] {item.body} → {ans.spoken}")
        if passed and not item.is_verified:
            item.is_verified = True
            item.verified_at = datetime.now(timezone.utc)
            for skill_name in json.loads(unit.skill_ids or "[]"):
                record_evidence_event(db, skill_name, "teachback_pass", f"unit_item:{item.id}")
        if not passed:
            # 一题一卡：先按 source_item_id 查已有卡（与 mastery 首答路径一致），
            # 已有卡不重复建（quiz 答错 + teach-back 答错同一 item 只留 1 张）
            existing = (
                db.query(ReviewCard).filter_by(source_item_id=item.id).first()
                if item.id else None
            )
            if existing is None:
                db.add(ReviewCard(
                    source_item_id=item.id,
                    source="teachback",
                    front=item.body,
                    back=item.answer or "",
                    due_at=datetime.now(timezone.utc),
                    **initial_card(),
                    created_at=datetime.now(timezone.utc),
                ))
                cards_created += 1

    # 自动落学习日志：content = 用户口述原话（按条拼接），AI 只判对错不改写
    content = f"Teach-Back · {unit.title}\n" + "\n".join(lines)
    log = LearningLog(
        task_id=None,
        unit_id=unit.id,
        content=content,
        duration_minutes=payload.duration_minutes,
        artifact_url=None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return ok({
        "verdicts": verdicts,
        "log_id": log.id,
        "cards_created": cards_created,
    })
