"""Planner Agent 的 LangGraph 节点。

每个节点接收 state，返回 dict（LangGraph 合并到状态）。
节点保持纯函数特性，便于单测与替换。

流程：
    analyze_skill_gap → select_learning_target → generate_task → validate_task
"""

from __future__ import annotations

from app.agents.planner.state import GapItem, PlannerState


def analyze_skill_gap(state: PlannerState) -> dict:
    """节点1：计算每个技能的 gap（target-level）并降序排序。"""

    skills = state.get("skills", [])
    gaps: list[GapItem] = [
        GapItem(
            name=s["name"],
            level=s["level"],
            target=s["target"],
            gap=s["target"] - s["level"],
        )
        for s in skills
    ]
    # gap 大的在前；gap 相同时 level 低的在前（更薄弱优先）
    gaps.sort(key=lambda g: (-g["gap"], g["level"]))
    return {"gaps": gaps}


def select_learning_target(state: PlannerState) -> dict:
    """节点2：选择目标学习技能。

    优先级：
      1. current_focus 非空 → 强制聚焦该技能（用户指定）
      2. 否则 → 取 gaps 首项（最大缺口）
    """

    focus = state.get("current_focus")
    if focus:
        return {"selected_skill": focus}

    gaps = state.get("gaps", [])
    if not gaps:
        return {"selected_skill": "Unknown"}
    return {"selected_skill": gaps[0]["name"]}


def generate_task(state: PlannerState) -> dict:
    """节点3：调用生成器产出任务。

    根据 state.generator 选择 rule/llm 生成器（可插拔架构）。
    默认 rule。LLM 调用失败时自动 fallback RuleGenerator（safe_generate）。
    """

    from app.agents.planner.generators import safe_generate

    task = safe_generate(state)
    return {"task": dict(task)}


def validate_task(state: PlannerState) -> dict:
    """节点4：校验任务结构完整性。

    检查 TaskOutput 必填字段，valid 标记下游可用性。
    Day5 保持轻量校验；未来 Reviewer Agent 会做更深入评估。
    """

    task = state.get("task") or {}
    required = ["title", "skill", "duration", "acceptance", "status"]
    valid = all(task.get(k) is not None for k in required)
    return {"valid": valid}
