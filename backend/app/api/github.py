"""GitHub API 路由 —— commit 半确认 Proposal 通道（计划 3 Task 3 解除 deprecate）。

- ``GET /suggestions``：Proposal 草稿的**唯一来源**——GitHub 同步起草的待确认
  commit 建议（前端 githubService 消费）。
- ``POST /suggestions/{id}/confirm`` / ``POST /suggestions/{id}/reject``：半确认
  写路径，已回到 OpenAPI 文档面（2026-09-24「待计划 3 接线」的 deprecate 标记
  随本任务取消）。
- ``POST /sync``：手动触发同步。**仍为 schema 隐藏**（include_in_schema=False）
  ——活跃写端点预算 ≤25（test_active_write_endpoints.py 守），且同步主路径在
  scheduler 定时任务、水位由 services/github/sync.py 成功路径写入，不依赖本
  路由入 schema；路由保留可手动调用。
"""

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
    """获取待确认的 commit 建议列表（Proposal 草稿来源）。"""
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


@router.post("/sync", include_in_schema=False)
def manual_sync() -> ApiResponse[dict]:
    """手动触发 GitHub 同步（schema 隐藏，见模块 docstring 预算说明）。"""
    count = sync_new_commits()
    return ok({"new_suggestions": count})
