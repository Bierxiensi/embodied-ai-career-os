"""GitHub API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.response import ApiResponse, ok
from app.services.github.sync import sync_new_commits
from app.services.github.store import (
    confirm_suggestion,
    get_pending_suggestions,
    reject_suggestion,
)

router = APIRouter(prefix="/github", tags=["github"])


class SuggestionOut(BaseModel):
    id: str
    commit_sha: str
    commit_message: str
    repo: str
    ai_suggestions: list
    summary: str | None
    created_at: str | None


class ConfirmRequest(BaseModel):
    skill: str


@router.get("/suggestions")
def list_suggestions() -> ApiResponse[list[SuggestionOut]]:
    """获取待确认的 commit 建议列表。"""
    items = get_pending_suggestions(limit=10)
    return ok([SuggestionOut(**it) for it in items])


@router.post("/suggestions/{suggestion_id}/confirm")
def confirm(suggestion_id: str, req: ConfirmRequest) -> ApiResponse[dict]:
    """确认一条 commit 建议的关联技能。"""
    ok_flag = confirm_suggestion(suggestion_id, req.skill)
    if not ok_flag:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return ok({"id": suggestion_id, "skill": req.skill, "status": "confirmed"})


@router.post("/suggestions/{suggestion_id}/reject")
def reject(suggestion_id: str) -> ApiResponse[dict]:
    """驳回一条 commit 建议。"""
    ok_flag = reject_suggestion(suggestion_id)
    if not ok_flag:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return ok({"id": suggestion_id, "status": "rejected"})


@router.post("/sync")
def manual_sync() -> ApiResponse[dict]:
    """手动触发 GitHub 同步。"""
    count = sync_new_commits()
    return ok({"new_suggestions": count})
