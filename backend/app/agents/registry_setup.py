"""Agent 注册初始化。

在应用启动时将所有具体 Agent 注册到 AgentRegistry。
供 main.py lifespan 调用，确保 Supervisor/Orchestrator 启动后能按名查找 Agent。

设计要点：
- 幂等：重复调用不会抛异常（已注册则跳过），便于热重载与测试
- 注册顺序即为 list_agents() 返回顺序：planner / reviewer / supervisor
- Day 2 注册 planner / reviewer / supervisor；Day 3/4 追加 career / research
- Phase 3 Day 3 追加 knowledge（Paper Knowledge Agent，基于 RAG 问答）
"""

from __future__ import annotations

from app.agents.core.registry import AgentRegistry


def setup_default_agents() -> list[str]:
    """注册默认 Agent 集合到全局 Registry。

    幂等：已注册的同名 Agent 跳过，不抛异常。
    适合 dev server 热重载场景（lifespan 可能多次触发）。

    Returns:
        注册完成后 Registry 中所有 Agent 名称（按注册顺序）。
    """
    # 延迟导入避免循环依赖（agent 模块导入 graph，graph 导入 nodes）
    from app.agents.career.agent import CareerAgent
    from app.agents.knowledge.agent import PaperKnowledgeAgent
    from app.agents.planner.agent import PlannerAgent
    from app.agents.reviewer.agent import ReviewerAgent
    from app.agents.research.agent import ResearchAgent
    from app.agents.supervisor.agent import SupervisorAgent

    # 按调度优先级注册：supervisor 为入口，其余为执行单元
    candidates = [
        SupervisorAgent(),
        PlannerAgent(),
        ReviewerAgent(),
        CareerAgent(),
        ResearchAgent(),
        PaperKnowledgeAgent(),  # Phase 3 Day 3：论文知识问答
    ]

    for agent in candidates:
        # 幂等：已注册则跳过，避免热重载时 ValueError
        if AgentRegistry.get(agent.name) is None:
            AgentRegistry.register(agent)

    return AgentRegistry.list_agents()
