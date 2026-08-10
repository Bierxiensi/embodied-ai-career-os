"""LLMClient 抽象基类。

统一 chat / chat_json 契约，具体 Provider 实现此类。
遵循 embedder.py 的抽象模式：子类实现核心方法，工厂负责选择与 fallback。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.models import ChatMessage


class LLMClient(ABC):
    """LLM 客户端抽象基类。

    子类需实现 chat；chat_json 有默认实现（调用 chat 后解析 JSON）。
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前使用的模型名。"""
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: list[ChatMessage]) -> str:
        """发送对话，返回模型回复文本。

        Args:
            messages: 对话消息列表（system + user + history）

        Returns:
            模型回复的文本内容。
        """
        raise NotImplementedError

    def chat_json(
        self,
        messages: list[ChatMessage],
        output_schema: dict | None = None,
    ) -> dict:
        """发送对话，返回模型回复并解析为 JSON dict。

        默认实现：调用 chat() 后尝试从回复中提取 JSON。
        子类可覆盖以使用原生的 function calling / JSON mode。

        Args:
            messages: 对话消息列表
            output_schema: 期望的 JSON Schema（供子类实现 function calling）

        Returns:
            解析后的 dict。解析失败时返回 {"_parse_error": True, "raw": text}
        """
        import json
        import re

        text = self.chat(messages)

        # 尝试提取 JSON 块（```json ... ``` 或直接 { ... }）
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            text = json_match.group(1).strip()

        # 尝试找最外层花括号
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            text = text[brace_start : brace_end + 1]

        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return {"_parse_error": True, "raw": text}
