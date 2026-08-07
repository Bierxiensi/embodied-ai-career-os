"""Career Agent 规则库（Rule-based，不接 LLM）。

包含：
- 岗位 → 必需技能映射表（Skill Ontology 的简化版）
- Gap 计算
- 优先级排序策略

设计为纯函数，便于单测与未来替换为 LLM 实现。
"""

from __future__ import annotations

from app.agents.career.state import SkillGapItem, SkillStatus

# ===== 岗位 → 必需技能映射表 =====
# 集中维护，Week 2 可接入 LLM 动态生成
# 每个岗位列出的技能为"达到该岗位胜任线所需"的清单
ROLE_REQUIRED_SKILLS: dict[str, list[str]] = {
    "Robot AI Engineer": [
        "ROS2",
        "Isaac",
        "PyTorch",
        "Deep Learning",
        "Robot Learning",
        "VLA",
        "Python",
    ],
    "AI Application Engineer": [
        "Python",
        "Agent Application",
        "Deep Learning",
        "PyTorch",
        "Frontend",
        "Web Engineering",
    ],
    # 兜底：未知岗位返回空，由节点走 fallback
}

# ===== 优先级排序权重 =====
# gap 越大权重越高；level 越低（越薄弱）权重越高
# 综合分 = gap * GAP_WEIGHT + (MAX_LEVEL - level) * LEVEL_WEIGHT
# gap 主导，level 仅在同 gap 时做次级排序
GAP_WEIGHT = 10
LEVEL_WEIGHT = 1
MAX_LEVEL = 5


def get_required_skills(target_role: str) -> list[str]:
    """获取岗位必需技能清单。

    大小写不敏感。未知岗位返回空列表（节点层走 fallback）。

    Args:
        target_role: 目标岗位名称

    Returns:
        必需技能名列表
    """
    return ROLE_REQUIRED_SKILLS.get(target_role, [])


def compute_gap(skill: SkillStatus, required: bool) -> SkillGapItem:
    """计算单个技能的缺口。

    gap = max(target - level, 0)，避免负值（已超目标的技能 gap=0）。

    Args:
        skill: 技能当前状态
        required: 是否为岗位必需技能

    Returns:
        SkillGapItem 缺口项
    """
    gap = max(skill["target"] - skill["level"], 0)
    return SkillGapItem(
        name=skill["name"],
        level=skill["level"],
        target=skill["target"],
        gap=gap,
        required=required,
    )


def prioritize_skills(gaps: list[SkillGapItem]) -> list[str]:
    """按优先级排序技能名。

    排序规则（降序，分高优先）：
    1. 必需技能 > 非必需技能（required=True 优先）
    2. gap 大的优先（缺口越大越紧急）
    3. gap 相同时 level 低的优先（越薄弱越需补）
    4. 上述均同则按名称字典序（保证稳定排序）

    过滤：gap=0 的技能不进优先级列表（已达标无需学）。

    Args:
        gaps: 缺口列表

    Returns:
        排序后的技能名列表（高优先 → 低优先），不含已达标技能
    """
    # 仅保留有缺口的技能（gap=0 已达标，无需学习）
    pending = [g for g in gaps if g["gap"] > 0]

    # 稳定排序：从次要键到主要键逐步排序，每步保持前序相对位置
    # 优先级（高→低）：必需技能 > gap 大 > level 低 > 名称字典序
    pending.sort(key=lambda g: g["name"])                      # 字典序正序（最次要）
    pending.sort(key=lambda g: g["level"])                     # level 升序（低优先）
    pending.sort(key=lambda g: g["gap"], reverse=True)         # gap 降序（缺口大优先）
    pending.sort(key=lambda g: 1 if g["required"] else 0, reverse=True)  # 必需优先（最主要）

    return [g["name"] for g in pending]
