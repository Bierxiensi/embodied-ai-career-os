"""Supervisor Agent 的 LangGraph 节点。

每个节点接收 state，返回 dict（LangGraph 合并到状态）。
节点保持纯函数特性，便于单测与替换。

流程：
    analyze_intent → select_agents → create_plan

Day 2 使用规则路由（关键词匹配），Week 2 接入 LLM 时仅替换
analyze_intent 节点实现，其余节点与图结构不变。
"""

from __future__ import annotations

from app.agents.supervisor.state import SupervisorState

# ===== 意图 → 下游 Agent 映射 =====
# 集中维护，便于扩展与单测
INTENT_AGENTS_MAP: dict[str, list[str]] = {
    "learn": ["research", "planner"],
    "complete": ["reviewer"],
    "career": ["career"],
    "unknown": ["planner"],
}

# ===== 意图关键词（按匹配优先级排列）=====
# career 优先于 learn：如"成为 X 工程师"应归为职业规划而非学习
# complete 次之：明确表达完成动作
# learn 最后兜底学习类
_INTENT_KEYWORDS: list[tuple[str, list[str]]] = [
    (
        "career",
        ["成为", "职业", "规划", "转型", "岗位", "career", "goal", "target"],
    ),
    (
        "complete",
        ["完成", "复盘", "提交", "done", "complete", "review", "finish"],
    ),
    (
        "learn",
        ["学习", "学", "练习", "实践", "learn", "study", "practice"],
    ),
]


def analyze_intent(state: SupervisorState) -> dict:
    """节点1：识别用户意图。

    规则路由：按关键词优先级匹配。
    - career 优先：含"成为/职业/规划"等归为职业规划
    - complete 次之：含"完成/复盘"等归为任务完成
    - learn 兜底：含"学习/学"等归为学习
    - 未命中任何关键词 → unknown

    Args:
        state: 含 user_input

    Returns:
        {"intent": "learn" | "complete" | "career" | "unknown"}
    """
    user_input = (state.get("user_input") or "").lower()

    for intent, keywords in _INTENT_KEYWORDS:
        if any(kw.lower() in user_input for kw in keywords):
            return {"intent": intent}

    return {"intent": "unknown"}


def select_agents(state: SupervisorState) -> dict:
    """节点2：根据意图选择需要调度的下游 Agent。

    查 INTENT_AGENTS_MAP 映射表，未匹配意图走 unknown 分支（planner）。

    Args:
        state: 含 intent

    Returns:
        {"required_agents": ["research", "planner"], ...}
    """
    intent = state.get("intent", "unknown")
    agents = INTENT_AGENTS_MAP.get(intent, INTENT_AGENTS_MAP["unknown"])
    return {"required_agents": list(agents)}


def create_plan(state: SupervisorState) -> dict:
    """节点3：生成执行计划。

    Day 2 仅产出顺序执行步骤（plan 列表），不实际调度。
    Day 5 Orchestrator 接入后，按此计划依次执行各 Agent。

    Args:
        state: 含 required_agents / intent

    Returns:
        {"execution_plan": {...}, "result": {...}}
    """
    agents = state.get("required_agents", [])
    intent = state.get("intent", "unknown")

    # 顺序执行步骤：每个 Agent 一个步骤
    steps = [
        {"step": i + 1, "agent": agent, "action": f"execute_{agent}"}
        for i, agent in enumerate(agents)
    ]

    plan = {
        "intent": intent,
        "agents": agents,
        "steps": steps,
    }

    # Day 2 result 仅占位，实际执行结果由 Day 5 Orchestrator 填充
    result = {
        "status": "planned",
        "message": f"Supervisor planned {len(agents)} agent(s) for intent '{intent}'",
    }

    return {"execution_plan": plan, "result": result}
