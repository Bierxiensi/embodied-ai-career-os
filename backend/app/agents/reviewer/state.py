"""Reviewer Agent 状态定义。

LangGraph StateGraph 在各节点间传递的状态。
与 PlannerState 设计原则一致：total=False，便于各节点局部更新。

差异：db session 由 API 层注入到 state——collect_context 只读；
SkillAssessment / skill 等级写库已移交 apply 层（spec §4.3 只读铁律）。
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
    llm_evaluation: dict    # LLM 原始评估（规则 fallback 时缺省）

    # ===== 输出 =====
    review: dict            # 契约提案（skill_name/proposed_level/evidence_score/reason/evidence_refs/verdict）
    applied: bool           # 节点层只在 contract block 时置 False（节点从不落库）
    updated_skill: dict     # 技能状态投影（只读；apply 成功后由 API 层用 DB 真值刷新）
    agent_run_id: str       # agent_runs 记录 ID
