"""GitHub API 客户端 —— 拉取 commit 列表。"""

from __future__ import annotations

import json
from datetime import datetime
from urllib.request import Request, urlopen


class GitHubClient:
    """GitHub REST API 轻量封装。使用 urllib（零依赖）。"""

    BASE = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self._token = token

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def fetch_commits(self, repo: str, since: datetime | None = None,
                      per_page: int = 10) -> list[dict]:
        """拉取 repo 最近 commit 列表。

        Args:
            repo: 仓库名（如 "embodied-ai-career-os"）
            since: ISO 时间字符串，只拉此时间之后的 commit
            per_page: 每页数量

        Returns:
            commit 列表，每项含 sha / message / files 列表 / stats
        """
        commits: list[dict] = []
        url = f"{self.BASE}/repos/prideandprejudice/{repo}/commits?per_page={per_page}"
        if since is not None:
            url += f"&since={since.isoformat()}"

        try:
            req = Request(url, headers=self._headers())
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for item in data:
                sha = item.get("sha", "")
                commit_info = item.get("commit", {})
                message = commit_info.get("message", "")

                files = self._fetch_commit_files(repo, sha)

                commits.append({
                    "sha": sha,
                    "message": message.split("\n")[0],
                    "full_message": message,
                    "files": files,
                    "additions": sum(f.get("additions", 0) for f in files),
                    "deletions": sum(f.get("deletions", 0) for f in files),
                    "timestamp": commit_info.get("committer", {}).get("date", ""),
                })
        except Exception:
            pass

        return commits

    def _fetch_commit_files(self, repo: str, sha: str) -> list[dict]:
        """拉取单个 commit 的文件变更列表。"""
        url = f"{self.BASE}/repos/prideandprejudice/{repo}/commits/{sha}"
        try:
            req = Request(url, headers=self._headers())
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read())
            return data.get("files", [])
        except Exception:
            return []
