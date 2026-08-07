"""Paper ORM 模型。

存储论文结构化摘要，由 PaperAgent 的 summarizer 产出后持久化。
Day 2 RAG 检索时，通过 paper_id 关联 paper_chunks 表。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Paper(Base):
    """论文记录。"""

    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # UUID 字符串主键

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf / md / txt
    arxiv_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 结构化摘要（summarizer 产出）
    method: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dataset: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contribution: Mapped[str] = mapped_column(Text, nullable=False, default="")
    relation_to_my_project: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[str] = mapped_column(
        String(10), nullable=False, default="low", server_default="low"
    )

    # 元数据
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
