"""LLM 工厂函数。

遵循 embedder.py 的工厂+单例缓存+fallback 模式：
    get_llm() → 按 LLM_PROVIDER 选择 Provider，不可用时自动 fallback 到 MockClient
"""

from __future__ import annotations

import warnings

from app.core.config import settings
from app.llm.client import LLMClient
from app.llm.models import LLMConfig
from app.llm.providers import MockClient, OllamaClient, OpenAICompatibleClient

# 单例缓存：LLM 客户端创建后全局复用
_llm_cache: dict[str, LLMClient] = {}


def get_llm() -> LLMClient:
    """获取 LLM 客户端实例（带单例缓存）。

    按 LLM_PROVIDER 环境变量选择：
    - mock（默认）：零依赖模板返回
    - ollama：本地模型（qwen2.5:7b）
    - deepseek：DeepSeek API（OpenAI Compatible）
    - openai_compatible：通用 OpenAI Compatible API（Qwen/Kimi 等）

    远程 API 不可用时打 warning 并 fallback 到 MockClient。

    Returns:
        LLMClient 实例。线程安全（GIL 保护缓存读写）。
    """
    provider = settings.llm_provider
    cache_key = _cache_key(provider)

    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    client = _build_client(provider)
    _llm_cache[cache_key] = client
    return client


def _cache_key(provider: str) -> str:
    """生成缓存 key。不同 provider + 不同 model 需区分缓存。"""
    if provider == "ollama":
        return f"ollama:{settings.ollama_model}"
    if provider in ("deepseek", "openai_compatible"):
        return f"{provider}:{settings.llm_model}"
    return provider


def _build_client(provider: str) -> LLMClient:
    """按 provider 构建客户端。失败时 fallback 到 MockClient。"""
    try:
        return _try_build(provider)
    except Exception as e:
        warnings.warn(
            f"LLM Provider '{provider}' 不可用：{e}。"
            f"Fallback 到 MockClient。"
            f"配置真实 LLM：设置环境变量 LLM_PROVIDER + API key / base URL。",
            stacklevel=2,
        )
        return MockClient()


def _try_build(provider: str) -> LLMClient:
    """尝试构建指定 provider 的客户端。"""
    config = LLMConfig(
        provider=settings.llm_provider,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
    )

    if provider == "mock":
        return MockClient()

    if provider == "ollama":
        # 简单的连接检测：尝试 import openai（构建时做，懒加载在 chat 时再做）
        return OllamaClient(config)

    if provider == "deepseek":
        if not config.api_key:
            raise ValueError("DeepSeek 需要设置 DEEPSEEK_API_KEY 环境变量")
        # DeepSeek 与 OpenAI 兼容
        config.base_url = config.base_url or "https://api.deepseek.com/v1"
        config.model = config.model or "deepseek-chat"
        return OpenAICompatibleClient(config)

    if provider == "openai_compatible":
        if not config.api_key:
            raise ValueError("openai_compatible 需要设置 LLM_API_KEY 环境变量")
        if not config.base_url:
            raise ValueError("openai_compatible 需要设置 LLM_BASE_URL 环境变量")
        return OpenAICompatibleClient(config)

    # 未知 provider → fallback
    warnings.warn(
        f"未知 LLM_PROVIDER '{provider}'，fallback 到 MockClient。"
        f"支持：mock / ollama / deepseek / openai_compatible",
        stacklevel=2,
    )
    return MockClient()
