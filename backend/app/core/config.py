"""基础配置。

Phase 1 Day1 仅保留最小配置项；
Phase 1 Day2 扩展数据库配置；
Phase 3 Week 2 扩展 LLM Provider 配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# backend 目录（config.py 上溯两级：core → app → backend），用于推导水位文件绝对路径，
# 避免依赖运行时 cwd 导致相对路径失真。
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    """应用配置。从环境变量读取，便于 Docker 注入。"""

    # 服务运行配置
    app_name: str = "Embodied AI Career OS API"
    app_version: str = "0.1.0"
    reload: bool = False

    # 允许跨域的前端来源，逗号分隔
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])

    # ---------- 数据库 ----------
    # 默认 SQLite（零配置本地开发）；Docker 环境通过 DATABASE_URL 注入 PG
    # 格式示例：
    #   sqlite:///./data/app.db
    #   postgresql+psycopg2://career:career@postgres:5432/career_os
    database_url: str = "sqlite:///./data/app.db"

    # ---------- LLM Provider ----------
    # 支持：mock / ollama / deepseek / openai_compatible
    llm_provider: str = "mock"
    # API Key（deepseek / openai_compatible 需要）
    llm_api_key: str = ""
    # 自定义 API Base URL（openai_compatible 需要）
    llm_base_url: str = ""
    # 模型名（openai_compatible / ollama 需要）
    llm_model: str = ""
    # Ollama 专属：本地服务地址
    ollama_base_url: str = "http://localhost:11434/v1"
    # Ollama 模型名
    ollama_model: str = "qwen2.5:7b"

    # ---------- Reminder ----------
    reminder_channel: str = "terminal"        # serverchan | pushplus | email | terminal
    reminder_channel_key: str = ""            # Server酱 SendKey / PushPlus Token
    reminder_morning_time: str = "08:30"
    reminder_evening_time: str = "21:00"
    reminder_inactivity_days: int = 3
    reminder_timezone: str = "Asia/Shanghai"

    # ---------- GitHub ----------
    github_token: str = ""                    # Personal Access Token
    github_owner: str = "prideandprejudice"   # 仓库 owner（原硬编码于 client.py，现可配置）
    github_repos: list[str] = field(default_factory=lambda: ["embodied-ai-career-os"])
    github_poll_interval_minutes: int = 30
    # 水位文件用绝对路径，避免相对路径在 cwd 变化时失真
    github_last_sync_file: str = str(_BACKEND_ROOT / ".github_last_sync")

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量构建配置。"""

        # 读取 CORS 来源，缺省为前端开发地址
        raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

        return cls(
            reload=os.getenv("RELOAD", "false").lower() == "true",
            cors_origins=origins,
            database_url=os.getenv("DATABASE_URL", "sqlite:///./data/app.db"),
            llm_provider=os.getenv("LLM_PROVIDER", "mock"),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_base_url=os.getenv("LLM_BASE_URL", ""),
            llm_model=os.getenv("LLM_MODEL", ""),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            reminder_channel=os.getenv("REMINDER_CHANNEL", "terminal"),
            reminder_channel_key=os.getenv("REMINDER_CHANNEL_KEY", ""),
            reminder_morning_time=os.getenv("REMINDER_MORNING_TIME", "08:30"),
            reminder_evening_time=os.getenv("REMINDER_EVENING_TIME", "21:00"),
            reminder_inactivity_days=int(os.getenv("REMINDER_INACTIVITY_DAYS", "3")),
            reminder_timezone=os.getenv("REMINDER_TIMEZONE", "Asia/Shanghai"),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_owner=os.getenv("GITHUB_OWNER", "prideandprejudice"),
            github_repos=[r.strip() for r in os.getenv("GITHUB_REPOS", "embodied-ai-career-os").split(",")],
            github_poll_interval_minutes=int(os.getenv("GITHUB_POLL_INTERVAL", "30")),
            github_last_sync_file=os.getenv(
                "GITHUB_LAST_SYNC_FILE", str(_BACKEND_ROOT / ".github_last_sync")
            ),
        )


# 全局单例，供 main.py 直接导入
settings = Settings.from_env()
