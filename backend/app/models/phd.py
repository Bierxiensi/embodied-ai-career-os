"""博士模块 ORM 模型（Phase 1）。

三张表：
- ResearchDirection：研究方向主数据（六维匹配"研究方向契合"维度的基准分来源）
- PhDTarget：院校 / 项目机会（招生政策、层次、方向、截止日期）
- PhDAdvisor：导师（招生状态、在职友好度、缓存的六维匹配结果）

设计说明：
- target_id / direction_key 均为**逻辑引用**，不建物理外键 —— 与 career_modes 一致，
  避免机会 / 模式切换级联影响历史。
- match_json 缓存六维匹配结果（{overall, grade, dimensions, gaps, computed_at}），
  由 agents/phd/agent.py 的 PhDMatchEngine 计算后回写，便于前端直接展示。
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResearchDirection(Base):
    """研究方向主数据。

    interest_weight = 该方向在用户转型目标里的"兴趣契合基准分"（0-100），
    由 docs/MY_CONTEXT.md 的转型方向决定，供六维匹配的方向维度直接取用。
    """

    __tablename__ = "research_directions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    interest_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class PhDTarget(Base):
    """一个博士招生机会（院校 / 项目）。"""

    __tablename__ = "phd_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tier: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # 985 / 211 / 双一流 / 中科院 / 市属 / 普通 / 海外
    direction_key: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )  # 逻辑外键 → research_directions.key
    track_key: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )  # llm / vlm / embodied / ai-algo / robotics
    in_service_friendly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    min_publication: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # none / ei / sci
    application_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class PhDAdvisor(Base):
    """导师记录（带缓存的六维匹配结果）。"""

    __tablename__ = "phd_advisors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # 逻辑外键 → phd_targets.id
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 教授 / 副教授 / 研究员
    research_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    recruiting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    in_service_friendly: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    homepage: Mapped[str | None] = mapped_column(String(300), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Phase 2 风险雷达的 phd 维度依赖：是否已联系该导师
    contacted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contact_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
