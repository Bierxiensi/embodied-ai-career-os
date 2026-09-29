"""GitHub API 路由 —— commit 半确认 Proposal 通道（计划 3 Task 3 接线，2026-09-29）。

活跃流程（capture-first：系统起草 → 人确认 → append-only 落库）：

- ``GET /suggestions``：**Proposal 草稿的唯一来源**——GitHub 同步起草的待确认
  commit 建议（前端 githubService.getSuggestions 消费）。
- ``POST /suggestions/{id}/confirm``：半确认写路径。状态置 confirmed 的同时经
  ``record_evidence_event`` 追加 ``commit:{sha}`` 证据事件（evidence_gate → L2），
  结果以 ``evidence`` 字段随响应返回（只追加不改名）。
- ``POST /suggestions/{id}/reject``：驳回草稿，不产生证据。
- ``POST /sync``：手动触发同步。**仍为 schema 隐藏**（include_in_schema=False）——
  活跃写端点预算 ≤25（test_active_write_endpoints.py 守），且同步主路径在
  scheduler 定时任务、水位写在 services/github/sync.py 成功路径，不依赖本路由
  入 schema；路由保留可手动调用。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.response import ApiResponse, ok
from app.db.base import SessionLocal
from app.models.commit_suggestion import CommitSuggestion
from app.services.evidence_events import record_evidence_event
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


def _record_commit_evidence(suggestion_id: str, skill: str) -> dict:
    """状态更新后追加 commit L2 证据事件（gate 只在 apply 层写）。

    ref 用模型行的 commit_sha（可追溯，防虚构）；技能用行上的
    confirmed_skill（confirm_suggestion 已写入），缺失时回退请求体 skill。
    """
    db = SessionLocal()
    try:
        row = (
            db.query(CommitSuggestion)
            .filter(CommitSuggestion.id == suggestion_id)
            .first()
        )
        if row is None:
            return {"skill": skill, "applied": False, "error": "suggestion_missing"}
        return record_evidence_event(
            db,
            row.confirmed_skill or skill,
            "commit",
            f"commit:{row.commit_sha}",
        )
    finally:
        db.close()


@router.get("/suggestions")
def list_suggestions() -> ApiResponse[list[SuggestionOut]]:
    """获取待确认的 commit 建议列表（Proposal 草稿来源）。"""
    items = get_pending_suggestions(limit=10)
    return ok([SuggestionOut(**it) for it in items])


@router.post("/suggestions/{suggestion_id}/confirm")
def confirm(suggestion_id: str, req: ConfirmRequest) -> ApiResponse[dict]:
    """确认一条 commit 建议的关联技能（半确认 → 追加 commit L2 证据）。"""
    ok_flag = confirm_suggestion(suggestion_id, req.skill)
    if not ok_flag:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    evidence = _record_commit_evidence(suggestion_id, req.skill)
    return ok({
        "id": suggestion_id,
        "skill": req.skill,
        "status": "confirmed",
        "evidence": evidence,
    })


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
