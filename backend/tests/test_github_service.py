"""GitHub Service 单元测试。"""
from datetime import datetime, timezone

import pytest
from app.services.github.analyzer import analyze_commit


def test_analyze_commit_mock():
    """Mock LLM 时返回 None（fallback）。"""
    result = analyze_commit({
        "sha": "abc123",
        "message": "feat: add ROS2 publisher",
        "files": [{"filename": "ros2_ws/src/publisher.py", "additions": 45, "deletions": 0}],
        "additions": 45,
        "deletions": 0,
    })
    # Mock LLM 返回 JSON parse 失败 → None
    assert result is None


def test_analyze_commit_empty_files():
    result = analyze_commit({
        "sha": "abc",
        "message": "chore: update deps",
        "files": [],
        "additions": 1,
        "deletions": 1,
    })
    assert result is None


def test_save_last_sync_writes_aware_iso(tmp_path, monkeypatch):
    """水位落盘：backend/.github_last_sync 存纯 ISO aware UTC 串且可回读。

    背景：`.github_last_sync` 从未产出（docs 实测口径），诊断链路是盲的；
    此前写的是 JSON 包装 + naive 时间，肉眼 / `datetime.fromisoformat` 读不了。
    """
    from app.core.config import settings
    from app.services.github import sync as sync_mod

    target = tmp_path / ".github_last_sync"
    monkeypatch.setattr(settings, "github_last_sync_file", str(target))

    sync_mod._save_last_sync(datetime.now(timezone.utc))

    raw = target.read_text(encoding="utf-8").strip()
    dt = datetime.fromisoformat(raw)  # 纯 ISO 文本，不是 JSON
    assert dt.tzinfo is not None and dt.utcoffset() is not None  # aware UTC
    assert sync_mod._load_last_sync() == dt


def test_sync_success_path_writes_watermark(tmp_path, monkeypatch):
    """成功同步（token 已配、拉取无异常）末尾必须写水位。"""
    from app.core.config import settings
    from app.services.github import sync as sync_mod

    target = tmp_path / ".github_last_sync"
    monkeypatch.setattr(settings, "github_last_sync_file", str(target))
    monkeypatch.setattr(settings, "github_token", "test-token")

    class _FakeClient:
        def __init__(self, **kwargs):
            pass

        def fetch_commits(self, repo, since=None):
            return []

    monkeypatch.setattr(sync_mod, "GitHubClient", _FakeClient)
    assert sync_mod.sync_new_commits() == 0
    dt = datetime.fromisoformat(target.read_text(encoding="utf-8").strip())
    assert dt.tzinfo is not None


def test_load_last_sync_reads_legacy_json(tmp_path, monkeypatch):
    """旧版 JSON 包装水位仍可读（不因格式切换丢历史水位）。"""
    from app.core.config import settings
    from app.services.github import sync as sync_mod

    target = tmp_path / ".github_last_sync"
    monkeypatch.setattr(settings, "github_last_sync_file", str(target))
    ts = "2026-09-29T03:00:00+00:00"
    target.write_text('{"last_sync": "%s"}' % ts, encoding="utf-8")

    got = sync_mod._load_last_sync()
    assert got == datetime.fromisoformat(ts)
