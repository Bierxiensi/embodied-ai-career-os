"""文本嵌入器：text → 向量。

抽象 + 双实现 + 工厂：
    - Embedder（抽象基类）：统一 embed / embed_batch / dim / model_name 契约
    - HashEmbedder：hashing trick 伪嵌入（纯 Python，开发态 fallback）
    - SentenceTransformerEmbedder：真实语义嵌入（生产态，懒加载）
    - get_embedder()：工厂，优先 ST，缺失时 fallback 到 HashEmbedder

设计要点：
- 零依赖 fallback：环境无 sentence-transformers / numpy 时仍可测试检索流程
- 语义近似性：HashEmbedder 通过共享词哈希碰撞产生余弦相似度，
  相似文本（共享词多）得分高，足以验证 RAG 流程正确性
- 维度对齐：HashEmbedder 默认 384 维，与 all-MiniLM-L6-v2 一致，
  便于后续切换模型时向量库结构不变
- 线程安全：embed / embed_batch 无状态，可并发调用
"""

from __future__ import annotations

import hashlib
import math
import threading
import warnings
from abc import ABC, abstractmethod
from typing import Any


class Embedder(ABC):
    """文本嵌入器抽象基类。

    子类需实现 embed / embed_batch / dim / model_name。
    所有方法应线程安全（无共享可变状态）。
    """

    @property
    @abstractmethod
    def dim(self) -> int:
        """嵌入向量维度。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型标识，用于向量库按模型过滤。"""
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """单文本 → 归一化向量。"""
        raise NotImplementedError

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入，默认逐个调用 embed（子类可优化为批量推理）。

        线程安全：无共享状态，可被并发调用。
        """
        return [self.embed(t) for t in texts]


class HashEmbedder(Embedder):
    """基于 hashing trick 的伪嵌入器（开发态 fallback）。

    原理：
    - 分词后对每个 token 做 md5 哈希
    - hash % dim 决定维度位置，hash 符号位决定 +1/-1
    - 累加后 L2 归一化

    特性：
    - 纯 Python，零依赖
    - 确定性：相同文本 → 相同向量
    - 语义近似：共享词多的文本余弦相似度更高（够测试检索流程）
    - 维度默认 384，对齐 all-MiniLM-L6-v2 便于切换
    """

    def __init__(self, dim: int = 384, model_name: str = "hash-384") -> None:
        self._dim = dim
        self._model_name = model_name

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, text: str) -> list[float]:
        """单文本 → 归一化向量。

        分词用空格 + 常见标点切分，兼容中英文。
        """
        vec = [0.0] * self._dim
        tokens = _tokenize(text)
        for token in tokens:
            # md5 哈希 → 整数，决定位置与符号
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            # 高位决定符号，避免同位置累加抵消
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign

        # L2 归一化（零向量兜底，避免除零）
        norm = math.sqrt(sum(v * v for v in vec))
        if norm < 1e-12:
            return vec
        return [v / norm for v in vec]


class SentenceTransformerEmbedder(Embedder):
    """基于 sentence-transformers 的真实语义嵌入器（生产态）。

    懒加载模型：首次 embed 时才加载，避免 import 时拉取 torch。
    依赖缺失时抛 ImportError（由工厂 fallback 到 HashEmbedder）。
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self._model_name = model_name
        self._model: Any = None  # 懒加载
        # RAG #14 修复：多线程并发首次 embed 时，_ensure_model 可能重复加载模型
        # （GIL 不保护"检查-然后设置"的复合操作）。用 Lock 保护懒加载。
        self._model_lock = threading.Lock()

    @property
    def dim(self) -> int:
        # all-MiniLM-L6-v2 为 384 维；其他模型首次 embed 后从模型获取
        if self._model is not None:
            return self._model.get_sentence_embedding_dimension()
        return 384

    @property
    def model_name(self) -> str:
        return self._model_name

    def _ensure_model(self) -> None:
        """懒加载模型，线程安全（RAG #14：Lock 保护避免并发重复加载）。"""
        # 双重检查：已加载直接返回，避免无谓加锁
        if self._model is not None:
            return
        with self._model_lock:
            # 持锁后再次检查，防止等待锁的线程重复加载
            if self._model is not None:
                return
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise ImportError(
                    "使用 SentenceTransformerEmbedder 需安装："
                    "pip install sentence-transformers"
                ) from e
            self._model = SentenceTransformer(self._model_name)

    def embed(self, text: str) -> list[float]:
        self._ensure_model()
        # normalize_embeddings=True 输出已归一化向量
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量推理，比逐个 encode 快一个数量级。"""
        self._ensure_model()
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]


# ============================================================
# 工厂函数
# ============================================================

# 单例缓存：embedder 构造昂贵（ST 加载模型），全局复用
_embedder_cache: dict[str, Embedder] = {}


def get_embedder(prefer_st: bool = True) -> Embedder:
    """获取 embedder 实例（带单例缓存）。

    Args:
        prefer_st: True 时优先尝试 sentence-transformers，缺失则 fallback

    Returns:
        Embedder 实例。优先 ST，fallback 到 HashEmbedder（打 warning）。

    线程安全：缓存字典读写由 GIL 保护，幂等。
    """
    cache_key = "st" if prefer_st else "hash"

    if cache_key in _embedder_cache:
        return _embedder_cache[cache_key]

    embedder: Embedder
    if prefer_st and _sentence_transformers_available():
        # 依赖可用，用真实语义嵌入（模型首次 embed 时懒加载）
        embedder = SentenceTransformerEmbedder()
        _embedder_cache[cache_key] = embedder
        return embedder

    if prefer_st:
        warnings.warn(
            "sentence-transformers 未安装，fallback 到 HashEmbedder。"
            "开发态可测试检索流程，生产环境请安装："
            "pip install sentence-transformers",
            stacklevel=2,
        )

    # fallback 或显式选择 hash
    embedder = HashEmbedder()
    _embedder_cache[cache_key] = embedder
    return embedder


def _sentence_transformers_available() -> bool:
    """检测 sentence-transformers 是否可 import（不实际加载模型）。"""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _tokenize(text: str) -> list[str]:
    """简易分词：小写化 + 按非字母数字切分。

    兼容中英文：中文按字、英文按词。无外部依赖。
    """
    if not text:
        return []
    text = text.lower()
    # 连续字母数字（含中文）作为一个 token
    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
    if buf:
        tokens.append("".join(buf))
    return tokens
