"""项目模型。对应 spec：项目是主轨道，技能是副产品。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# 数据来源标记语义（projects / tasks / milestones 三张表共用，见 migrations/0007）：
#   user    —— 用户真实数据（默认）
#   seed    —— 初始化种子数据
#   planner —— Planner Agent 生成
#   test    —— 测试残留（可安全清理）
#
# 为什么需要它：审计（2026-09-10）发现开发库里 214 个项目只有 2 个是真的，
# 其余是历次 pytest 写入的 "M Test Project" 等。此前**没有任何字段能区分**
# 真数据与测试数据，清理只能靠猜名字（能猜出 "M Test Project"，猜不出名为 "P" 的）。
# 加上 source 后，测试/种子写入时打标，前端可默认过滤，清理可精确执行。
SOURCE_USER = "user"
SOURCE_SEED = "seed"
SOURCE_PLANNER = "planner"
SOURCE_TEST = "test"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    current_version: Mapped[str] = mapped_column(String(20), default="V0", nullable=False)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    readme: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 数据来源（user / seed / planner / test），用于区分真实数据与测试残留
    source: Mapped[str] = mapped_column(
        String(20), default=SOURCE_USER, server_default=SOURCE_USER, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
