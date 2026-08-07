"""Career Agent 的 LangGraph 节点。

每个节点接收 state，返回 dict（LangGraph 合并到状态）。
节点保持纯函数特性，便于单测与替换。

流程：
    analyze_target → compute_gaps → prioritize → recommend
"""

from __future__ import annotations

from app.agents.career.rules import (
    compute_gap,
    get_required_skills,
    prioritize_skills,
)
from app.agents.career.state import CareerState, SkillStatus


def analyze_target(state: CareerState) -> dict:
    """节点1：分析目标岗位，提取必需技能清单。

    规则查表（ROLE_REQUIRED_SKILLS）。未知岗位返回空列表，
    由下游节点 fallback 为"全部当前技能按 gap 排序"。

    Args:
        state: 含 target_role

    Returns:
        {"required_skills": ["ROS2", "Isaac", ...]}
    """
    target_role = state.get("target_role", "")
    required = get_required_skills(target_role)
    return {"required_skills": required}


def compute_gaps(state: CareerState) -> dict:
    """节点2：计算每个技能的缺口。

    遍历 current_skills，按是否在 required_skills 中标记 required 字段。
    未知岗位（required_skills 为空）时所有技能 required=False，
    仍按 gap 排序，保证 fallback 路径可用。

    Args:
        state: 含 current_skills / required_skills

    Returns:
        {"gaps": [SkillGapItem, ...]}
    """
    current: list[SkillStatus] = state.get("current_skills", [])
    required_set = set(state.get("required_skills", []))

    gaps = [compute_gap(s, required=s["name"] in required_set) for s in current]
    return {"gaps": gaps}


def prioritize(state: CareerState) -> dict:
    """节点3：按优先级排序技能。

    委托 rules.prioritize_skills，规则集中维护。
    输出为技能名列表（已剔除 gap=0 的达标技能）。

    Args:
        state: 含 gaps

    Returns:
        {"priority": ["Isaac", "ROS2", ...]}
    """
    gaps = state.get("gaps", [])
    priority = prioritize_skills(gaps)
    return {"priority": priority}


def recommend(state: CareerState) -> dict:
    """节点4：生成推荐路线。

    Day 3 阶段为模板化推荐：
    - 取 priority 前 3 项作为近期重点
    - 生成 3 步学习路线（每步对应一个技能）
    - rationale 解释排序依据

    Args:
        state: 含 priority / target_role

    Returns:
        {"recommendation": {"steps": [...], "rationale": "..."}}
    """
    priority = state.get("priority", [])
    target_role = state.get("target_role", "目标岗位")
    gaps = state.get("gaps", [])

    # 近期重点：前 3 项（不足 3 项则全取）
    focus = priority[:3]

    # 生成学习步骤：每步一个技能
    steps = [
        {
            "step": i + 1,
            "skill": skill,
            "action": f"集中突破 {skill}，缩小岗位缺口",
        }
        for i, skill in enumerate(focus)
    ]

    # 排序依据说明（供前端展示与面试讲解）
    gap_summary = ", ".join(
        f"{g['name']}(gap={g['gap']})"
        for g in gaps
        if g["name"] in focus
    )
    rationale = (
        f"针对 {target_role} 岗位，按 [必需技能优先 → gap 大优先 → level 低优先] "
        f"排序，近期重点：{gap_summary or '暂无缺口'}"
    )

    recommendation = {
        "focus": focus,
        "steps": steps,
        "rationale": rationale,
    }
    return {"recommendation": recommendation}
