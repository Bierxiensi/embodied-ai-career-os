"""Agent 注册中心。

全局单例（类级状态），集中管理所有 Agent 实例。
供 Supervisor / Orchestrator 按名查找 Agent。

用法：
    AgentRegistry.register(PlannerAgent())
    AgentRegistry.register(ReviewerAgent())

    agent = AgentRegistry.get("planner")
    names = AgentRegistry.list_agents()  # ["planner", "reviewer"]

线程安全说明：
    类级 dict 在 CPython GIL 下读写原子，但多线程并发 register/unregister
    仍可能竞争。注册时机建议在应用启动阶段（单线程）完成，运行时只读查找。
    若需运行时动态注册，调用方自行加锁。
"""

from __future__ import annotations

from app.agents.core.agent import BaseAgent


class AgentRegistry:
    """Agent 注册中心（类级单例）。"""

    # 类级存储：name -> Agent 实例。所有实例共享同一注册表
    _agents: dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent: BaseAgent) -> BaseAgent:
        """注册 Agent。

        Args:
            agent: BaseAgent 实例

        Returns:
            注册的 Agent 实例（链式调用友好）

        Raises:
            ValueError: 同名 Agent 已注册
        """
        if agent.name in cls._agents:
            raise ValueError(f"Agent 已注册: {agent.name}")
        cls._agents[agent.name] = agent
        return agent

    @classmethod
    def unregister(cls, name: str) -> bool:
        """注销 Agent。

        Returns:
            是否成功注销（不存在则返回 False）
        """
        return cls._agents.pop(name, None) is not None

    @classmethod
    def get(cls, name: str) -> BaseAgent | None:
        """按名获取 Agent。

        Returns:
            Agent 实例，不存在返回 None
        """
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> list[str]:
        """列出所有已注册 Agent 名称。

        Returns:
            名称列表（按注册顺序）
        """
        return list(cls._agents.keys())

    @classmethod
    def clear(cls) -> None:
        """清空注册表（仅用于测试隔离）。"""
        cls._agents.clear()
