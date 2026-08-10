"""LLM Provider 实现。

遵循 embedder.py 的抽象+多实现模式：
    - MockClient：零依赖兜底，返回固定模板（开发/CI 可用）
    - OpenAICompatibleClient：通用 OpenAI Compatible 协议（DeepSeek/Qwen/Kimi）
    - OllamaClient：本地 Ollama API（RTX 4060Ti 16GB → qwen2.5:7b）
"""

from __future__ import annotations

from app.llm.client import LLMClient
from app.llm.models import ChatMessage, LLMConfig


# ============================================================
# MockClient —— 零依赖兜底
# ============================================================

class MockClient(LLMClient):
    """Mock LLM 客户端。

    返回固定模板文本，不依赖任何外部 API。
    适用于：
    - 开发环境无 API key
    - CI 流水线无 GPU
    - 流程验证（确保调用链正确）
    """

    def __init__(self) -> None:
        pass

    @property
    def model_name(self) -> str:
        return "mock-v1"

    def chat(self, messages: list[ChatMessage]) -> str:
        """返回模板回复。根据 user 消息内容做简单匹配。"""
        user_msg = ""
        for m in messages:
            if m.role == "user":
                user_msg = m.content
                break

        # 简单关键词匹配，返回不同的 mock 回复
        if not user_msg:
            return "（Mock LLM：未收到有效问题）"

        return (
            f"Mock LLM 回复：已收到你的问题（{len(user_msg)} 字符）。\n\n"
            "这是模拟回复。接入真实 LLM 后，此处将返回模型生成的个性化内容。\n\n"
            "配置方式：设置环境变量 LLM_PROVIDER=deepseek|ollama|openai_compatible"
        )


# ============================================================
# OpenAICompatibleClient —— 通用远程 API
# ============================================================

class OpenAICompatibleClient(LLMClient):
    """OpenAI Compatible 协议客户端。

    支持所有兼容 OpenAI Chat Completions API 的服务：
    - DeepSeek（https://api.deepseek.com/v1）
    - Qwen / 通义千问（阿里云 DashScope）
    - Kimi / Moonshot
    - 其他自部署的 vLLM / Ollama（OpenAI 兼容模式）
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._client = None  # 懒加载

    @property
    def model_name(self) -> str:
        return self._config.model or "gpt-3.5-turbo"

    def _ensure_client(self):
        """懒加载 OpenAI 客户端（避免 import 时拉取依赖）。"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "使用 OpenAI Compatible 客户端需安装 openai 包："
                    "pip install openai"
                )
            self._client = OpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url or None,
            )

    def chat(self, messages: list[ChatMessage]) -> str:
        self._ensure_client()

        formatted = [{"role": m.role, "content": m.content} for m in messages]

        resp = self._client.chat.completions.create(
            model=self._config.model,
            messages=formatted,
            temperature=0.7,
            max_tokens=1024,
        )

        choice = resp.choices[0]
        return choice.message.content or ""


# ============================================================
# OllamaClient —— 本地模型
# ============================================================

class OllamaClient(LLMClient):
    """Ollama 本地客户端。

    使用 Ollama 的 OpenAI 兼容端点（/v1），
    默认模型 qwen2.5:7b（适合 16GB 显存）。

    前置条件：ollama pull qwen2.5:7b
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._client = None

    @property
    def model_name(self) -> str:
        return self._config.ollama_model

    def _ensure_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "使用 Ollama 客户端需安装 openai 包：pip install openai"
                )
            self._client = OpenAI(
                api_key="ollama",  # Ollama 不需要真实 key
                base_url=self._config.ollama_base_url,
            )

    def chat(self, messages: list[ChatMessage]) -> str:
        self._ensure_client()

        formatted = [{"role": m.role, "content": m.content} for m in messages]

        try:
            resp = self._client.chat.completions.create(
                model=self._config.ollama_model,
                messages=formatted,
                temperature=0.7,
                max_tokens=1024,
            )
            choice = resp.choices[0]
            return choice.message.content or ""
        except Exception:
            # Ollama 不可用时给出友好提示
            raise ConnectionError(
                f"无法连接 Ollama（{self._config.ollama_base_url}）。"
                "请确认：1) ollama serve 已启动 2) ollama pull {self._config.ollama_model} 已完成"
            )
