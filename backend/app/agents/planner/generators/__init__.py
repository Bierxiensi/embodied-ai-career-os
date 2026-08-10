"""可插拔任务生成器。

架构：
    Task Strategy Layer
        ├── RuleGenerator  （Day5 实现：基于模板的确定性生成）
        └── LLMGenerator   （Phase 3 Week 2：LLM 智能生成）

切换方式：PlannerState.generator = "rule" | "llm"
generate_task 节点据此选择生成器，图结构不变。

LLM 失败回退：LLMGenerator 调用异常时自动 fallback 到 RuleGenerator，
确保 Planner API 永远可用（不会因为 LLM 不可用而 500）。
"""

from __future__ import annotations

import warnings
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

    if name == "llm":
        from app.agents.planner.generators.llm_generator import LLMGenerator

        return LLMGenerator()
    # 默认规则引擎
    from app.agents.planner.generators.rule_generator import RuleGenerator

    return RuleGenerator()


def safe_generate(state: PlannerState) -> TaskOutput:
    """安全生成任务：LLM 失败时自动回退 RuleGenerator。

    此函数在 generate_task 节点中被调用，而非直接调 generator.generate()。
    保证 Planner API 的可用性：LLM 不可用 → 静默回退规则引擎，仍返回有效任务。
    """
    from app.agents.planner.generators.rule_generator import RuleGenerator

    gen_name = state.get("generator", "rule")

    generator = get_generator(gen_name)

    try:
        return generator.generate(state)
    except Exception as e:
        # LLM 调用失败 → 自动回退规则引擎
        if gen_name == "llm":
            warnings.warn(
                f"LLM Generator 调用失败：{e}。自动回退 RuleGenerator。"
                f"请检查 LLM_PROVIDER 配置或网络连接。",
                stacklevel=2,
            )
            return RuleGenerator().generate(state)
        # rule generator 失败则直接抛（应为代码逻辑错误，不应发生）
        raise
