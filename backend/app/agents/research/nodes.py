"""Research Agent 的 LangGraph 节点。

每个节点接收 state，返回 dict（LangGraph 合并到状态）。
节点保持纯函数特性，便于单测与替换。

流程：
    parse_topic → match_template → decompose_tasks → build_plan

Day 4 不联网，全部基于本地模板。
Week 4-6 接入 RAG 后，match_template 可替换为向量检索。
"""

from __future__ import annotations

from app.agents.research.state import ResearchState, ResearchTask
from app.agents.research.templates import (
    ResearchTemplate,
    fallback_template,
    match_template,
)

# 研究任务的 4 个类别（固定顺序，对应 paper → code → experiment → verification）
TASK_CATEGORIES = ["paper", "code", "experiment", "verification"]


def parse_topic(state: ResearchState) -> dict:
    """节点1：解析用户输入的主题。

    清理空白字符，规范化主题名。
    空输入兜底为 "Unknown"，保证下游不报错。

    Args:
        state: 含 topic

    Returns:
        {"normalized_topic": "ACT"}
    """
    raw = state.get("topic", "")
    normalized = (raw or "").strip() or "Unknown"
    return {"normalized_topic": normalized}


def _match_with_llm(topic: str) -> dict | None:
    """LLM 研究主题拆解。失败返回 None。"""
    from app.llm import ChatMessage, get_llm

    prompt = (
        "为主题生成结构化研究计划模板。\n\n"
        f"主题：{topic}\n\n"
        "返回 JSON：\n"
        f'{{"topic": "{topic}", '
        '"paper": {"title": "推荐阅读的论文", "description": "读什么", "resources": ["链接"]}, '
        '"code": {"title": "推荐研究的代码库", "description": "看什么", "resources": ["GitHub链接"]}, '
        '"experiment": {"title": "建议的最小实验", "description": "做什么", "resources": []}, '
        '"verification": {"title": "验证标准", "description": "怎么算成功", "resources": []}}}\n'
        "直接输出 JSON。"
    )

    try:
        llm = get_llm()
        return llm.chat_json([
            ChatMessage(role="system", content="你是机器人/AI研究员。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
    except Exception:
        return None


def match_template_node(state: ResearchState) -> dict:
    """节点2：匹配研究模板。

    LLM 优先（动态生成），失败时 fallback 预设模板。

    Args:
        state: 含 normalized_topic

    Returns:
        {"template": ResearchTemplate}
    """
    topic = state.get("normalized_topic", "Unknown")

    # 先查预设模板（精确匹配优先）
    template = match_template(topic)
    if template is not None:
        return {"template": dict(template)}

    # LLM 动态生成
    llm_result = _match_with_llm(topic)
    if llm_result is not None:
        return {"template": llm_result}

    # Fallback
    return {"template": dict(fallback_template(topic))}


def decompose_tasks(state: ResearchState) -> dict:
    """节点3：将模板拆解为研究任务列表。

    按固定顺序（paper → code → experiment → verification）输出 4 项任务。
    每项任务含 category / title / description / resources。

    Args:
        state: 含 template

    Returns:
        {"tasks": [ResearchTask, ...]}
    """
    template: ResearchTemplate = state.get("template", {})

    tasks: list[ResearchTask] = []
    for category in TASK_CATEGORIES:
        item = template.get(category, {})
        tasks.append(
            ResearchTask(
                category=category,
                title=item.get("title", f"{category} task"),
                description=item.get("description", ""),
                resources=item.get("resources", []),
            )
        )

    return {"tasks": tasks}


def build_plan(state: ResearchState) -> dict:
    """节点4：组装完整研究计划。

    输出含 summary / tasks / next_steps，供下游 Planner 与前端展示。

    Args:
        state: 含 normalized_topic / tasks

    Returns:
        {"plan": {"summary": ..., "tasks": [...], "next_steps": [...]}}
    """
    # 优先用模板的标准 topic 名（如 ACT），回退到用户输入的规范化主题
    template: ResearchTemplate = state.get("template", {})
    topic = template.get("topic") or state.get("normalized_topic", "Unknown")
    tasks: list[ResearchTask] = state.get("tasks", [])

    # 简短摘要：主题 + 任务数
    summary = f"针对「{topic}」生成 {len(tasks)} 项研究任务（论文/代码/实验/验证）"

    # 下一步建议：第一项任务为起点
    next_steps = []
    if tasks:
        first = tasks[0]
        next_steps.append(f"先从「{first['title']}」开始")
        if len(tasks) > 1:
            next_steps.append(f"完成后依次推进剩余 {len(tasks) - 1} 项")

    plan = {
        "topic": topic,
        "summary": summary,
        "tasks": tasks,
        "next_steps": next_steps,
    }
    return {"plan": plan}
