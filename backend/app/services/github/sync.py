"""GitHub 同步调度 —— 定时拉取 + 分析 + 存储。"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

from app.core.config import settings
from app.services.github.client import GitHubClient
from app.services.github.analyzer import analyze_commit
from app.services.github.store import save_suggestion

logger = logging.getLogger(__name__)


def _load_last_sync() -> datetime | None:
    """从文件读取上次同步时间。"""
    path = settings.github_last_sync_file
    if os.path.exists(path):
        try:
            with open(path) as f:
                ts = json.load(f).get("last_sync", "")
                if ts:
                    return datetime.fromisoformat(ts)
        except Exception:
            pass
    return None


def _save_last_sync(dt: datetime) -> None:
    """保存本次同步时间。"""
    with open(settings.github_last_sync_file, "w") as f:
        json.dump({"last_sync": dt.isoformat()}, f)


def sync_new_commits() -> int:
    """拉取新 commit → LLM 分析 → 存储。返回新增 suggestion 数量。

    水位推进策略：仅当同步全程无异常时才推进水位；任一仓库拉取/存储失败时
    保留旧水位，下次 sync 自动重试，避免提交被永久漏同步。
    """
    if not settings.github_token:
        logger.debug("GitHub token not configured, skipping sync")
        return 0

    # owner 由配置注入（原硬编码于 client，现可经 GITHUB_OWNER 覆盖）
    client = GitHubClient(token=settings.github_token, owner=settings.github_owner)
    last_sync = _load_last_sync()
    total_new = 0
    sync_ok = True

    try:
        for repo in settings.github_repos:
            commits = client.fetch_commits(repo.strip(), since=last_sync)
            for commit in commits:
                analysis = analyze_commit(commit)
                if analysis is None:
                    continue
                if analysis.get("suggest_ignore"):
                    continue
                sid = save_suggestion(commit, analysis, repo)
                if sid:
                    total_new += 1
    except Exception as e:
        # 拉取/解析失败：记录日志，不推进水位，下次重试
        logger.error("GitHub sync 失败，水位未推进: %s", e)
        sync_ok = False

    # 仅成功完成同步才推进水位，失败时保留旧水位以便下次重试
    if sync_ok:
        _save_last_sync(datetime.utcnow())

    if total_new > 0:
        logger.info("GitHub sync: %d new suggestions", total_new)
    return total_new
