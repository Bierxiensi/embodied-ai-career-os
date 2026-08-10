"""Prompt 模板生成 —— 按目标工具 + 任务类型生成适配 prompt。"""

from __future__ import annotations

# 工具角色配置
TOOL_ROLES = {
    "trae": "你是 Trae，一个 IDE 内置的 AI 编程助手。请帮我写代码。",
    "claude": "你是 Claude Code，一个命令行 AI 编程助手。请帮我写代码。",
    "chatgpt": "你是 ChatGPT，一个 AI 技术顾问。请帮我分析架构和概念。",
    "deepseek": "你是 DeepSeek，一个 AI 编程助手。请帮我解释代码和推导算法。",
    "workbuddy": "你是 WorkBuddy，一个本地 AI 工作助手。请帮我检索项目资料。",
}


def generate_tool_prompt(task, tool: str) -> str:
    """为指定工具生成适配 prompt。

    Args:
        task: 任务对象（含 title / objective / skill_name / acceptance / resources）
        tool: 工具名（trae / claude / chatgpt / deepseek / workbuddy）

    Returns:
        可直接复制粘贴的 prompt 文本
    """
    role = TOOL_ROLES.get(tool, "")
    acceptance = "\n".join(f"  - {a}" for a in (task.acceptance or []))
    resources = "\n".join(f"  - {r}" for r in (task.resources or []))

    if tool in ("trae", "claude"):
        return f"""{role}

任务：{task.title}

目标：{task.objective or task.title}

验收标准：
{acceptance}

参考资源：
{resources}

要求：
- 先解释整体架构，再写代码
- 每段关键代码后加注释说明
- 完成后标注我需要检查的关键点
- 代码放到 {task.skill_name or 'main'} 相关目录"""

    if tool == "chatgpt":
        return f"""{role}

我需要设计一个方案：{task.title}

背景：
- 我是有 6.5 年开发经验的工程师，正在转型具身智能
- 当前 {task.skill_name} 技能等级：入门
- 目标：{task.objective}

请帮我分析：
1. 这个任务的架构决策
2. 推荐的技术方案
3. 可能踩到的坑
4. 和 Robot AI Engineer 岗位能力模型的关联

先不要写代码，只讨论方案和架构。"""

    if tool == "workbuddy":
        return f"""{role}

当前项目上下文：
- 仓库：embodied-ai-career-os
- 模块：{task.skill_name or '通用'}
- 目标：{task.objective or task.title}

参考资料：
{resources}

请帮我：
1. 分析项目中与 {task.skill_name} 相关的现有代码
2. 推荐实现 {task.title} 的最佳路径
3. 如果已有相关笔记/文档，优先引用"""

    # 默认：通用 prompt
    return f"任务：{task.title}\n目标：{task.objective}\n技能：{task.skill_name}\n验收：{acceptance}"
