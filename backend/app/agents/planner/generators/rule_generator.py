"""Rule Generator：基于模板的确定性任务生成。

策略：
1. 根据 energy_level 选难度（low→beginner，high→intermediate，normal→默认）
2. 从 templates 取匹配模板
3. 时长按 available_minutes 截断（保证任务可在可用时间内启动）
4. 输出 TaskOutput

确定性、可单测、无外部依赖。未来替换为 LLMGenerator 时此文件保留作为兜底。
"""

from __future__ import annotations

from app.agents.planner.generators import TaskGenerator
from app.agents.planner.schemas import TaskOutput
from app.agents.planner.state import PlannerState
from app.agents.planner.templates import get_template

# 能量水平 → 偏好难度
ENERGY_TO_DIFFICULTY = {
    "low": "beginner",     # 低能量选入门任务，降低启动阻力
    "normal": None,        # 默认取首个
    "high": "intermediate",  # 高能量挑战进阶
}


class RuleGenerator(TaskGenerator):
    """规则引擎生成器。"""

    def generate(self, state: PlannerState) -> TaskOutput:
        skill = state.get("selected_skill", "")
        available = state.get("available_minutes", 45)
        energy = state.get("energy_level", "normal")

        # 按能量水平选难度
        difficulty = ENERGY_TO_DIFFICULTY.get(energy)
        template = get_template(skill, difficulty)

        # 兜底：技能无模板时生成通用任务
        if template is None:
            return _fallback_task(skill, available)

        # 时长截断：实际可用时间不足基准时长时，按可用时间启动
        duration = min(available, template["base_minutes"])

        return TaskOutput(
            title=template["title"],
            skill=skill,
            objective=template["objective"],
            duration=duration,
            difficulty=template["difficulty"],
            acceptance=template["acceptance"],
            resources=template["resources"],
            status="todo",
        )


def _fallback_task(skill: str, available: int) -> TaskOutput:
    """无模板时的兜底任务：通用学习任务。"""

    return TaskOutput(
        title=f"{skill} 学习与实践",
        skill=skill,
        objective=f"围绕 {skill} 进行项目驱动学习并产出可提交成果",
        duration=available,
        difficulty="beginner",
        acceptance=[
            f"明确 {skill} 当前一个具体学习点",
            "动手实践并产出代码或笔记",
            "Git 提交学习成果",
        ],
        resources=["官方文档", "GitHub 相关项目"],
        status="todo",
    )
