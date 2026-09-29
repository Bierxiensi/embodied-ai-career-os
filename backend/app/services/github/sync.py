"""GitHub 同步调度 —— 定时拉取 + 分析 + 存储。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.services.github.client import GitHubClient
from app.services.github.analyzer import analyze_commit
from app.services.github.store import save_suggestion

logger = logging.getLogger(__name__)


def _load_last_sync() -> datetime | None:
    """从文件读取上次同步时间（纯 ISO 时间串）。

    兼容旧版 JSON 包装格式 `{"last_sync": "..."}`——历史水位不因格式切换丢失。
    """
    path = Path(settings.github_last_sync_file)
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
        try:
            ts = json.loads(raw).get("last_sync", "")  # 旧版 JSON 包装
        except (json.JSONDecodeError, AttributeError):
            ts = raw  # 纯 ISO 文本（当前格式）
        return datetime.fromisoformat(ts) if ts else None
    except Exception:
        return None


def _save_last_sync(dt: datetime) -> None:
    """水位落盘：backend/.github_last_sync 存纯 ISO aware UTC 时间串。

    路径沿用模块既有约定（settings.github_last_sync_file → backend/ 根，见
    config._BACKEND_ROOT），避免相对路径随 cwd 失真。
    """
    path = Path(settings.github_last_sync_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dt.isoformat(), encoding="utf-8")


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

    # 仅成功完成同步才推进水位，失败时保留旧水位以便下次重试。
    # 水位落盘（此前从未产出，"同步从未产出"无法诊断）——spec §4.5：
    # backend/.github_last_sync = 纯 ISO aware UTC 时间串。
    if sync_ok:
        _save_last_sync(datetime.now(timezone.utc))

    if total_new > 0:
        logger.info("GitHub sync: %d new suggestions", total_new)
    return total_new
