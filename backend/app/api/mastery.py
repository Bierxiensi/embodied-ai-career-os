"""掌握单元 API（spec §3.3/§4.5）：units / answer 实证 / review 推进。

answer 判定：规则关键词比对优先，LLM 判定可选（Mock 不参与判定，判错即错——
不静默放过）。答对置 unit_items.is_verified（统一语义：闭卷实证掌握），
并为该题建/续 ReviewCard 入 SM-2 队列。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.core.sm2 import initial_card, schedule
from app.db.base import get_db
from app.models.mastery import MasteryUnit, ReviewCard, ReviewLog, UnitItem
from app.schemas.mastery import (
    AnswerIn,
    AnswerOut,
    ReviewCardOut,
    ReviewIn,
    UnitItemOut,
    UnitOut,
)
from app.services.mastery.generate import ensure_unit_content

router = APIRouter(prefix="/mastery", tags=["mastery"])


def _unit_out(unit: MasteryUnit, items: list[UnitItem], *, hide_answers: bool = True) -> UnitOut:
    return UnitOut(
        id=unit.id,
        source_type=unit.source_type,
        source_ref=unit.source_ref,
        title=unit.title,
        skill_ids=json.loads(unit.skill_ids or "[]"),
        day_seq=unit.day_seq,
        generation_mode=unit.generation_mode,
        status=unit.status,
        items=[UnitItemOut.model_validate(i) for i in items],
    )


@router.get("/units")
def list_units(day_seq: int | None = None, db: Session = Depends(get_db)) -> ApiResponse[list[UnitOut]]:
    q = db.query(MasteryUnit)
    if day_seq is not None:
        q = q.filter(MasteryUnit.day_seq == day_seq)
    units = q.order_by(MasteryUnit.id).all()
    return ok([_unit_out(u, []) for u in units])


@router.get("/units/{unit_id}")
def get_unit(unit_id: int, db: Session = Depends(get_db)) -> ApiResponse[UnitOut]:
    unit = db.get(MasteryUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    items = ensure_unit_content(db, unit)  # 懒生成触发点
    return ok(_unit_out(unit, items))


@router.post("/units/{unit_id}/answer")
def answer_item(
    unit_id: int, payload: AnswerIn, db: Session = Depends(get_db)
) -> ApiResponse[AnswerOut]:
    item = db.get(UnitItem, payload.item_id)
    if item is None or item.unit_id != unit_id:
        raise HTTPException(status_code=404, detail="Item not found")

    user = payload.answer.strip().lower()
    ref = (item.answer or "").strip().lower()
    # 规则判定：参考答案的核心词被覆盖即算对（宽松但不放水）；无参考答案视为错
    correct = bool(ref) and (ref in user or all(
        w in user for w in ref.replace("/", " ").split()[:2] if len(w) >= 2
    ))

    verified = item.is_verified
    card_id = None
    if correct and not item.is_verified:
        item.is_verified = True
        item.verified_at = datetime.now(timezone.utc)
        verified = True

    if item.kind in ("quiz_q", "flashcard", "concept_card"):
        card = (
            db.query(ReviewCard).filter_by(source_item_id=item.id).first()
            if item.id else None
        )
        if card is None:
            card = ReviewCard(
                source_item_id=item.id,
                source="concept",
                front=item.body,
                back=item.answer or "",
                due_at=datetime.now(timezone.utc),
                **initial_card(),
                created_at=datetime.now(timezone.utc),
            )
            db.add(card)
        card_id = card.id

    db.commit()
    return ok(AnswerOut(
        item_id=item.id, correct=correct, verified=verified,
        rationale=item.rationale if not correct else None,
        card_id=card_id,
    ))


@router.post("/cards/{card_id}/review")
def review_card(
    card_id: int, payload: ReviewIn, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    card = db.get(ReviewCard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    state = {
        "interval_days": card.interval_days,
        "ef": card.ef,
        "lapse_count": card.lapse_count,
        "good_streak": card.good_streak,
        "card_status": card.card_status,
    }
    new_state = schedule(state, payload.rating)
    due = datetime.now(timezone.utc) + timedelta(days=new_state["interval_days"])

    card.interval_days = new_state["interval_days"]
    card.ef = new_state["ef"]
    card.lapse_count = new_state["lapse_count"]
    card.good_streak = new_state["good_streak"]
    card.card_status = new_state["card_status"]
    card.due_at = due
    db.add(ReviewLog(
        card_id=card.id,
        rating=payload.rating,
        reviewed_at=datetime.now(timezone.utc),
        duration_seconds=payload.duration_seconds,
    ))
    db.commit()
    db.refresh(card)
    return ok({
        "card": ReviewCardOut.model_validate(card),
        "due_at": due.isoformat(),
    })
