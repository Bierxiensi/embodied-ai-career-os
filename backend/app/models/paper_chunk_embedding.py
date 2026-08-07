"""PaperChunk 向量嵌入模型。

存储 paper_chunks 的向量表示，Day 2 RAG 检索的数据源。

设计说明：
- 独立表而非加列到 paper_chunks：支持同一 chunk 多模型 embedding 共存
  （如 hash-384 开发态 + sentence-transformers 生产态）
- embedding 字段存 JSON 字符串（list[float]），便于调试与零依赖
- model_name + dim 标识嵌入来源，检索时按 model_name 过滤
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaperChunkEmbedding(Base):
    """论文分块向量嵌入记录。"""

    __tablename__ = "paper_chunk_embeddings"

    id: Mapped[str] = mapped_column(
        String, primary_key=True
    )  # UUID，单条嵌入记录主键

    chunk_id: Mapped[str] = mapped_column(
        String, ForeignKey("paper_chunks.id"), nullable=False, index=True
    )  # 关联 paper_chunks.id

    # 嵌入向量（JSON 字符串：list[float]）。
    # 用 JSON 而非 BLOB：零依赖、可读、数据量小（百级 chunk）可接受
    embedding: Mapped[str] = mapped_column(Text, nullable=False)

    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # 嵌入模型标识，如 "hash-384" / "sentence-transformers/all-MiniLM-L6-v2"

    dim: Mapped[int] = mapped_column(Integer, nullable=False)  # 向量维度

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
