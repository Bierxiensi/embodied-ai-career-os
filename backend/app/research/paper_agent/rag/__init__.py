"""RAG 子包：论文向量检索。

模块组成：
    - embedder：文本 → 向量（HashEmbedder fallback + SentenceTransformer 生产）
    - vector_store：向量存储 + 余弦检索（SQLite 实现）
    - indexer：paper_chunks → 向量库（增量/全量构建）
    - retriever：query → top-k 相关 chunks

典型流程：
    1. PaperAgent 解析论文 → paper_chunks 入库（Day 1）
    2. indexer.build_index() → chunks 嵌入入向量库（Day 2）
    3. retriever.search() → 语义检索（Day 2，Day 3 Knowledge Agent 用）
"""

from app.research.paper_agent.rag.embedder import (
    Embedder,
    HashEmbedder,
    SentenceTransformerEmbedder,
    get_embedder,
)
from app.research.paper_agent.rag.indexer import IndexResult, build_index
from app.research.paper_agent.rag.retriever import search, search_by_paper
from app.research.paper_agent.rag.vector_store import (
    SQLiteVectorStore,
    VectorStore,
    get_vector_store,
)

__all__ = [
    "Embedder",
    "HashEmbedder",
    "SentenceTransformerEmbedder",
    "get_embedder",
    "VectorStore",
    "SQLiteVectorStore",
    "get_vector_store",
    "IndexResult",
    "build_index",
    "search",
    "search_by_paper",
]
