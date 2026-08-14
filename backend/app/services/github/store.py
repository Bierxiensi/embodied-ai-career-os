"""CommitSuggestion 存储层。"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.db.base import SessionLocal
from app.models.commit_suggestion import CommitSuggestion


def save_suggestion(commit: dict, analysis: dict, repo: str) -> str | None:
    """存储一条 commit 分析建议。返回 suggestion id，失败返回 None。

    commit_sha 去重：同一 sha 已存在则跳过插入，返回已有 id，
    避免水位回退/重试导致重复 commit 被多次存储。
    """
    db = SessionLocal()
    try:
        commit_sha = commit.get("sha", "")
        # 先查重：已存在则直接返回已有 id，不重复插入
        existing = (
            db.query(CommitSuggestion)
            .filter(CommitSuggestion.commit_sha == commit_sha)
            .first()
        )
        if existing is not None:
            return existing.id

        sid = str(uuid.uuid4())
        db.add(CommitSuggestion(
            id=sid,
            commit_sha=commit_sha,
            commit_message=commit.get("message", ""),
            repo=repo,
            files_changed=[f.get("filename") for f in commit.get("files", [])],
            diff_summary=analysis.get("summary", ""),
            ai_suggestions=analysis.get("suggestions", []),
            status="pending",
        ))
        db.commit()
        return sid
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def get_pending_suggestions(limit: int = 10) -> list[dict]:
    """获取待确认的建议列表。"""
    db = SessionLocal()
    try:
        rows = db.query(CommitSuggestion).filter(
            CommitSuggestion.status == "pending"
        ).order_by(CommitSuggestion.created_at.desc()).limit(limit).all()

        return [
            {
                "id": r.id,
                "commit_sha": r.commit_sha[:7],
                "commit_message": r.commit_message,
                "repo": r.repo,
                "ai_suggestions": r.ai_suggestions,
                "summary": r.diff_summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def confirm_suggestion(suggestion_id: str, skill: str) -> bool:
    """确认一条建议的关联技能。"""
    db = SessionLocal()
    try:
        row = db.query(CommitSuggestion).filter(
            CommitSuggestion.id == suggestion_id
        ).first()
        if row is None:
            return False
        row.status = "confirmed"
        row.confirmed_skill = skill
        row.confirmed_at = datetime.utcnow()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def reject_suggestion(suggestion_id: str) -> bool:
    """驳回一条建议。"""
    db = SessionLocal()
    try:
        row = db.query(CommitSuggestion).filter(
            CommitSuggestion.id == suggestion_id
        ).first()
        if row is None:
            return False
        row.status = "rejected"
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()
