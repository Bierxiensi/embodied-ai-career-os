"""LLM Generator：基于 LLM 的智能任务生成。

通过 LLM 理解技能缺口、能量状态、可用时间，生成个性化学习任务。
LLM 调用失败时自动回退 RuleGenerator（由 __init__.py 工厂处理）。

接入方式：
    - 本地 Ollama：LLM_PROVIDER=ollama（qwen2.5:7b，适合 RTX 4060Ti）
    - API：LLM_PROVIDER=deepseek + DEEPSEEK_API_KEY
    - 兜底：LLM_PROVIDER=mock（默认，无外部依赖）
"""

from __future__ import annotations

import json

from app.agents.planner.generators import TaskGenerator
from app.agents.planner.schemas import TaskOutput
from app.agents.planner.state import PlannerState
from app.agents.planner.templates import TEMPLATES
from app.llm import ChatMessage, get_llm


# 技能模板关键词 → 用于 few-shot 示例
_FEW_SHOT_SKILLS = ["ROS2", "Isaac", "VLA"]


def _build_system_prompt() -> str:
    """构建 system prompt：角色设定 + 输出格式约束。"""
    return """你是一个具身智能学习规划师（Embodied AI Learning Planner）。

你的用户是一名软件工程师，正在从 AI Agent 应用开发转型为 Robot AI / VLA 工程师。
他拥有 SO101 机械臂真机，已跑通过 ACT 训练但泛化效果有限。
目标岗位：Robot AI Engineer / VLA Engineer，薪资 30k+。

你的任务：根据用户当前的技能状态、能量水平和可用时间，
生成一个唯一、具体、可验收的今日学习任务。

规则：
1. 每天只生成一个核心任务（用户每天只有 30-60 分钟）
2. 优先项目驱动、动手实践，而非纯理论学习
3. 任务必须可验收（用户能明确判断"做了/没做"）
4. 难度随能量水平调整：低能量→入门任务，高能量→挑战任务
5. 推荐真实可用的学习资源（官方文档/GitHub/论文）
6. 任务与 Robot AI Engineer 能力模型对齐（ROS2 / VLA / Robot Learning / Isaac）"""


def _build_user_prompt(state: PlannerState) -> str:
    """构建 user prompt：当前状态 + 任务要求。"""
    skills_str = "\n".join(
        f"  - {s['name']}: 当前 Lv{s['level']} → 目标 Lv{s['target']} (缺口 {s['target'] - s['level']})"
        for s in state.get("skills", [])[:6]
    )

    # V2: 注入项目上下文
    project_context = state.get("project_context", "")
    if project_context:
        project_context = f"\n项目上下文：\n{project_context}"

    focus = state.get("current_focus", "")
    focus_line = f"\n当前聚焦技能：{focus}（优先为该技能生成任务）" if focus else ""

    energy = state.get("energy_level", "normal")
    energy_map = {"low": "较低（选入门任务，降低门槛）", "normal": "正常", "high": "充沛（可以挑战进阶任务）"}
    energy_desc = energy_map.get(energy, "正常")

    return f"""今日状态：

可用时间：{state.get('available_minutes', 45)} 分钟
能量水平：{energy_desc}
目标岗位：{state.get('target_role', 'Robot AI Engineer')}
{focus_line}{project_context}

当前技能状态（仅列出缺口最大的前几项）：
{skills_str}

请根据以上信息，生成今日唯一学习任务。
输出严格的 JSON 格式，包含以下字段：
- title: 任务标题（简洁、行动导向，如 "ROS2 Publisher 节点实战"）
- skill: 关联技能名称
- objective: 学习目标（一句话描述要达成什么）
- duration: 预计时长（分钟，不超过可用时间的 90%）
- difficulty: 难度（beginner/intermediate/advanced）
- acceptance: 验收标准（3-5 条可检查的具体条目）
- resources: 推荐资源（2-3 个真实可用的链接或名称）
- status: 固定为 "todo"

直接输出 JSON，不要包含其他文字。"""


def _build_few_shot_examples() -> str:
    """从 templates.py 取 2-3 个模板作为 few-shot 示例（嵌入 system prompt）。"""
    examples: list[str] = []

    for skill in _FEW_SHOT_SKILLS:
        templates = TEMPLATES.get(skill, [])
        if templates:
            t = templates[0]
            # M4-1 修复：acceptance / resources 是 list，
            # 原 f-string 直接插值会用 Python repr（单引号），不符合 JSON 规范。
            # 改用 json.dumps 生成合法 JSON 数组（ensure_ascii=False 保留中文）。
            examples.append(
                f"示例（{skill} {t['difficulty']}）：\n"
                f'{{"title": "{t["title"]}", '
                f'"skill": "{skill}", '
                f'"objective": "{t["objective"]}", '
                f'"duration": {t["base_minutes"]}, '
                f'"difficulty": "{t["difficulty"]}", '
                f'"acceptance": {json.dumps(t["acceptance"], ensure_ascii=False)}, '
                f'"resources": {json.dumps(t["resources"], ensure_ascii=False)}, '
                f'"status": "todo"}}'
            )

    if examples:
        return "Few-shot 示例（参考格式和风格）：\n" + "\n".join(examples)
    return ""


def _validate_and_fill(task_dict: dict, state: PlannerState) -> TaskOutput:
    """校验 LLM 产出并填充缺失字段。"""
    # M4-2 修复：chat_json 解析失败时返回 {"_parse_error": True, "raw": ...}。
    # 原实现未检查该标记，仍走兜底填充，生成无意义任务；
    # 这里命中 _parse_error 即 raise，由外层 safe_generate 降级到 RuleGenerator。
    if task_dict.get("_parse_error"):
        raise ValueError(
            f"LLM JSON 解析失败，raw={task_dict.get('raw', '')[:120]!r}"
        )

    skill = state.get("selected_skill", "")
    available = state.get("available_minutes", 45)

    return TaskOutput(
        title=task_dict.get("title") or f"{skill} 学习任务",
        skill=task_dict.get("skill") or skill or "Robot AI",
        objective=task_dict.get("objective") or f"围绕 {skill or 'Robot AI'} 进行项目驱动学习",
        duration=min(
            int(task_dict.get("duration", available)),
            available,
        ),
        difficulty=task_dict.get("difficulty") or "beginner",
        acceptance=task_dict.get("acceptance") or [
            f"完成 {skill or 'Robot AI'} 相关实践",
            "代码提交 Git",
        ],
        resources=task_dict.get("resources") or ["官方文档", "GitHub"],
        status="todo",
    )


# ============================================================
# LLMGenerator
# ============================================================

class LLMGenerator(TaskGenerator):
    """LLM 任务生成器。

    组装 prompt → 调用 LLM → 解析 JSON → 校验 → 返回 TaskOutput。
    LLM 调用异常由外层（__init__.py 工厂）catch 并 fallback RuleGenerator。
    """

    def generate(self, state: PlannerState) -> TaskOutput:
        llm = get_llm()

        # 组装消息
        system_content = _build_system_prompt()
        few_shot = _build_few_shot_examples()
        if few_shot:
            system_content += f"\n\n{few_shot}"

        messages = [
            ChatMessage(role="system", content=system_content),
            ChatMessage(role="user", content=_build_user_prompt(state)),
        ]

        # 调用 LLM 获取结构化输出
        result = llm.chat_json(messages)

        # 校验并返回
        return _validate_and_fill(result, state)
