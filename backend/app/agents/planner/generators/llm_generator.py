"""LLM Generator（预留接口）。

Day5 不实现真实调用，仅抛出 NotImplementedError。
未来接入 DeepSeek / Qwen / Ollama 时，实现 generate 方法即可，
图结构与节点代码无需改动。

设计预留：
- generate 内部组装 prompt（含 gap/focus/energy 上下文）
- 调用 LLM API 获取结构化输出
- 解析为 TaskOutput（可用 Pydantic / function calling 保证 schema）
"""

from __future__ import annotations

from app.agents.planner.generators import TaskGenerator
from app.agents.planner.schemas import TaskOutput
from app.agents.planner.state import PlannerState


class LLMGenerator(TaskGenerator):
    """LLM 任务生成器。

    未来实现路径：
        1. 从 state 提取 selected_skill / gaps / energy_level / available_minutes
        2. 组装 system + user prompt（可读取 templates.py 作为 few-shot 示例）
        3. 调用 LLM（DeepSeek/Qwen/Ollama）
        4. 用 function calling / Pydantic 解析为 TaskOutput
    """

    def generate(self, state: PlannerState) -> TaskOutput:
        raise NotImplementedError(
            "LLMGenerator 尚未实现。Day5 使用 RuleGenerator，"
            "接入 LLM 时实现此方法即可，图结构无需改动。"
        )
