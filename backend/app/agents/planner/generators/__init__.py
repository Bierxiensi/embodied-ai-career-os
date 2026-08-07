"""可插拔任务生成器。

架构：
    Task Strategy Layer
        ├── RuleGenerator  （Day5 实现：基于模板的确定性生成）
        └── LLMGenerator   （预留：未来接 DeepSeek/Qwen/Ollama）

切换方式：PlannerState.generator = "rule" | "llm"
generate_task 节点据此选择生成器，图结构不变。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.agents.planner.schemas import TaskOutput
from app.agents.planner.state import PlannerState


class TaskGenerator(ABC):
    """生成器抽象基类。定义 generate 契约，供 rule/llm 实现。"""

    @abstractmethod
    def generate(self, state: PlannerState) -> TaskOutput:
        """根据状态生成任务。子类实现具体策略。"""
        raise NotImplementedError


def get_generator(name: str) -> TaskGenerator:
    """工厂方法：按名称取生成器实例。

    集中注册，便于未来扩展（如加 "hybrid" 生成器）。
    """

    # 延迟导入避免循环依赖与启动开销
    if name == "llm":
        from app.agents.planner.generators.llm_generator import LLMGenerator

        return LLMGenerator()
    # 默认规则引擎
    from app.agents.planner.generators.rule_generator import RuleGenerator

    return RuleGenerator()
