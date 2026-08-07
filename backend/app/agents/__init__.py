"""Agent 包入口。

Phase 2 Week 1：Multi-Agent 框架。
- core/：BaseAgent / AgentExecutor / AgentRegistry 基础设施
- planner/ / reviewer/：Phase 1 已有 Agent（Phase 2 加 agent.py 适配类）
- supervisor/：Phase 2 Week 1 Day2 入口 Agent
- registry_setup.setup_default_agents()：应用启动时注册全部 Agent
"""

from app.agents.registry_setup import setup_default_agents

__all__ = ["setup_default_agents"]
