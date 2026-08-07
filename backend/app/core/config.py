"""基础配置。

Phase 1 Day1 仅保留最小配置项；
后续阶段（Day2 数据库、Day5 Agent）再扩展。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """应用配置。从环境变量读取，便于 Docker 注入。"""

    # 服务运行配置
    app_name: str = "Embodied AI Career OS API"
    app_version: str = "0.1.0"
    reload: bool = False

    # 允许跨域的前端来源，逗号分隔
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000"])

    # 数据库连接串。
    # 开发态默认 SQLite（零配置）；切 PostgreSQL 仅需设置 DATABASE_URL=postgresql+psycopg://user:pwd@host:5432/db
    database_url: str = "sqlite:///./data/app.db"

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
        )


# 全局单例，供 main.py 直接导入
settings = Settings.from_env()
