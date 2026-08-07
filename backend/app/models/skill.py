"""技能模型。

对应 PRD Skill Graph：技能树。
level / target_level 用 0-5 整数对应 MY_CONTEXT 星级（★★★★★ = 5）。
evidence 记录能力证明项（项目/GitHub/作品），用于生成能力证明图谱。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Skill(Base):
    """技能节点。category 用于分组（如 Agent / Robotics / ROS2）。"""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 技能名称，如 ROS2 / Isaac / VLA
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    # 技能分类，如 Agent / Robotics
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 当前等级 0-5
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 目标等级 0-5
    target_level: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # 能力证明清单（JSON 数组）：项目/GitHub/作品链接
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
