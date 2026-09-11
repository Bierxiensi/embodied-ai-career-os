"""GitHub commit 抓取客户端（证据闭环 P2）。

只用标准库 urllib，不引入 requests 依赖，保证本地 / 容器都能跑。

用途：按日期抓取某仓库的 commit，供 plan 把「Git commit」这件四件套
按课程日自动归集（auto_verified=True），不再手工勾选。

鉴权：GITHUB_TOKEN 环境变量（或调用方传入）。未配置时调用方负责优雅跳过，
本模块只抛出 RuntimeError，让路由层决定怎么展示。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date

GITHUB_API = "https://api.github.com"


def fetch_github_commits(
    repo: str,
    since: str,
    until: str,
    token: str | None = None,
    per_page: int = 100,
) -> list[dict]:
    """抓取 owner/repo 在 [since, until] 区间的 commit。

    Args:
        repo: "owner/repo"
        since / until: ISO 日期（YYYY-MM-DD）
        token: GitHub PAT；缺省读 GITHUB_TOKEN 环境变量

    Returns:
        [{sha, message, date(YYYY-MM-DD), html_url, author}, ...]

    Raises:
        RuntimeError: 未配置 token / repo 格式错 / API 报错
    """

    token = token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN 未配置，无法抓取 GitHub commit")
    if not repo or "/" not in repo:
        raise RuntimeError("repo 必须是 owner/repo 格式")

    params = (
        f"since={since}T00:00:00Z"
        f"&until={until}T23:59:59Z"
        f"&per_page={per_page}"
    )
    url = f"{GITHUB_API}/repos/{repo}/commits?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "career-os-plan",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API {e.code}: {e.reason}")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"GitHub 请求失败: {e}")

    out: list[dict] = []
    for c in data:
        commit = c.get("commit", {})
        author_obj = c.get("author") or {}
        out.append(
            {
                "sha": c.get("sha"),
                "message": (commit.get("message") or "").split("\n")[0][:200],
                "date": (commit.get("author", {}).get("date") or "")[:10],
                "html_url": c.get("html_url"),
                "author": author_obj.get("login") or commit.get("author", {}).get("name"),
            }
        )
    return out


def day_index_for_commit(commit_date: str, sprint_start: str, total_days: int = 30) -> int | None:
    """把 commit 日期映射到课程日序号（1..30），超出窗口返回 None。"""

    try:
        idx = (date.fromisoformat(commit_date) - date.fromisoformat(sprint_start)).days + 1
    except ValueError:
        return None
    if 1 <= idx <= total_days:
        return idx
    return None
