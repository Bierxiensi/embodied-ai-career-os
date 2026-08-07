"""PaperChunk ORM 模型。

存储论文分块，Day 2 RAG 接入后此表为向量检索的数据源。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaperChunk(Base):
    """论文分块记录。"""

    __tablename__ = "paper_chunks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # UUID 字符串主键

    paper_id: Mapped[str] = mapped_column(
        String, ForeignKey("papers.id"), nullable=False, index=True
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    section: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unknown", index=True
    )  # abstract / introduction / method / experiment / conclusion / unknown
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    char_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
