"""Reviewer Agent 状态定义。

LangGraph StateGraph 在各节点间传递的状态。
与 PlannerState 设计原则一致：total=False，便于各节点局部更新。

差异：Reviewer 节点涉及 DB 读写，db session 由 API 层注入到 state。
"""

from typing import Any, TypedDict


class ReviewerState(TypedDict, total=False):
    """Reviewer 状态机。

    分为输入 / 中间态 / 输出三组。
    流转：collect_context → evaluate_evidence → create_assessment
          → apply_skill_update → record_agent_run
    """

    # ===== 输入 =====
    task: dict              # 完成的任务（含 title/skill_name/acceptance 等）
    learning_log: dict      # 学习日志（含 content/artifact_url 等）
    skill: dict             # 关联技能当前状态（含 id/level/target_level/evidence）
    db: Any                 # SQLAlchemy Session（API 层注入，节点内 DB 操作使用）

    # ===== 中间态 =====
    evidence_score: int     # 证据得分 0-100
    assessment: dict        # SkillAssessment 中间结果

    # ===== 输出 =====
    updated_skill: dict     # 应用后的技能状态
    agent_run_id: str       # agent_runs 记录 ID
