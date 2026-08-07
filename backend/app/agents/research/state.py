"""Research Agent 状态定义。

LangGraph StateGraph 在各节点间传递的状态。
total=False 允许各节点局部更新（LangGraph 合并语义）。

流转：parse_topic → match_template → decompose_tasks → build_plan
"""

from __future__ import annotations

from typing import TypedDict


class ResearchTask(TypedDict):
    """单项研究任务（decompose_tasks 节点产出）。"""

    category: str          # 类别：paper / code / experiment / verification
    title: str             # 任务标题
    description: str       # 任务描述
    resources: list[str]   # 推荐资源


class ResearchState(TypedDict, total=False):
    """Research 状态机。

    字段分组：
    - 输入：topic（技术主题，如 ACT / VLA / Isaac Lab）
    - 中间态：normalized_topic / template
    - 输出：tasks / plan
    """

    # ===== 输入 =====
    topic: str                     # 用户输入的原始主题

    # ===== 中间态 =====
    normalized_topic: str          # 规范化后的主题名（用于模板匹配）
    template: dict                 # 命中的研究模板

    # ===== 输出 =====
    tasks: list[ResearchTask]      # 拆解后的研究任务列表
    plan: dict                     # 完整研究计划（含 summary / tasks / next_steps）
