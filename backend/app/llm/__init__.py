"""LLM Provider Layer —— 统一多模型接入层。

用法：
    from app.llm import get_llm

    llm = get_llm()
    answer = llm.chat([ChatMessage(role="user", content="你好")])
    result = llm.chat_json(messages, output_schema={...})

Provider 选择（环境变量 LLM_PROVIDER）：
    - mock（默认）：零依赖模板返回
    - ollama：本地模型
    - deepseek：DeepSeek API
    - openai_compatible：通用 OpenAI 兼容 API
"""

from app.llm.client import LLMClient
from app.llm.factory import get_llm
from app.llm.models import ChatMessage, LLMConfig, LLMResponse

__all__ = [
    "ChatMessage",
    "LLMClient",
    "LLMConfig",
    "LLMResponse",
    "get_llm",
]
