"""LLM 数据模型：消息、响应、结构化输出 Schema。

ChatMessage 对标 OpenAI Chat Completion 的 messages 格式，
后续扩展支持多模态时仅需增加 content 联合类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """单条对话消息。

    Attributes:
        role: system / user / assistant
        content: 消息文本
    """

    role: str
    content: str


@dataclass
class LLMResponse:
    """LLM 调用响应。

    Attributes:
        content: 模型返回的文本
        model: 实际使用的模型名
        usage: token 用量（可选，MockClient 不提供）
    """

    content: str
    model: str = "unknown"
    usage: dict | None = None


@dataclass
class LLMConfig:
    """LLM Provider 配置。

    Attributes:
        provider: mock / ollama / deepseek / openai_compatible
        api_key: API 密钥（ollama 不需要）
        base_url: 自定义 API 地址（openai_compatible 需要）
        model: 模型名
        ollama_base_url: Ollama 本地地址
        ollama_model: Ollama 模型名
    """

    provider: str = "mock"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:7b"
