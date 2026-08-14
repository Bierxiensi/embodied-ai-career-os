"""Reviewer Agent 的 LangGraph 节点。

每个节点接收 state，返回 dict（LangGraph 合并到状态）。
与 Planner 不同，Reviewer 节点涉及 DB 读写（collect/apply/record），
故 db session 通过 state 传递（API 层注入）。

流程：
    collect_context → evaluate_evidence → create_assessment
    → apply_skill_update → record_agent_run
"""

from __future__ import annotations

import json
import uuid

from app.agents.reviewer.rules import (
    build_evidence_entry,
    decide_level,
    score_evidence,
)
from app.agents.reviewer.state import ReviewerState
from app.models.agent_run import AgentRun
from app.models.skill import Skill
from app.models.skill_assessment import SkillAssessment


# ============================================================
# LLM 评估（优先），失败时 fallback 规则评分
# ============================================================


def _evaluate_with_llm(task: dict, learning_log: dict) -> dict | None:
    """LLM 证据评估。失败返回 None，调用方 fallback 规则评分。"""
    from app.llm import ChatMessage, get_llm

    task_title = task.get("title", "")
    skill_name = task.get("skill_name", "")
    acceptance = task.get("acceptance", [])
    log_content = learning_log.get("content", "")
    artifact_url = learning_log.get("artifact_url", "")

    prompt = (
        "你是具身智能学习导师。评估学生的一次学习成果。\n\n"
        f"任务：{task_title}\n"
        f"关联技能：{skill_name}\n"
        f"验收标准：{acceptance}\n"
        f"学生日志：{log_content}\n"
        f"产出链接：{artifact_url or '无'}\n\n"
        "评估维度（每项 0-5 分）：\n"
        "- understanding: 日志中展现了多深的理解？（0=照抄，5=能迁移到新场景）\n"
        "- completion: 验收标准达成了几条？\n"
        "- reflection: 有无自我反思？（总结/改进/难点/收获）\n"
        "- evidence: artifact 链接是否有效？\n\n"
        "返回 JSON：\n"
        '{"understanding": 0-5, "completion": 0-5, "reflection": 0-5, '
        '"evidence": 0-5, "total_score": 0-100, "summary": "一句话评估"}\n'
        "直接输出 JSON，不要其他文字。"
    )

    try:
        llm = get_llm()
        result = llm.chat_json([
            ChatMessage(role="system", content="你是严格的技能评估导师。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
        if result.get("_parse_error"):
            return None
        score = int(result.get("total_score", 0))
        if 0 <= score <= 100:
            return {"evidence_score": min(score, 100), "llm_evaluation": result}
    except Exception:
        pass
    return None


def collect_context(state: ReviewerState) -> dict:
    """节点1：聚合上下文（task + learning_log + skill）。

    task / learning_log 由 API 层注入，此节点查 DB 补全 skill。
    db=None 或 skill 不存在时，用默认空值兜底，避免属性访问报错。
    """
    task = state.get("task") or {}
    learning_log = state.get("learning_log") or {}
    db = state.get("db")

    # 通过 task.skill_name 查关联技能；db 为 None 或 skill_name 为空时跳过
    skill_name = task.get("skill_name", "") or ""
    skill = None
    if db is not None and skill_name:
        skill = db.query(Skill).filter(Skill.name == skill_name).first()

    skill_dict = {
        "id": skill.id if skill is not None else None,
        "name": skill.name if skill is not None else skill_name or "Unknown",
        "level": skill.level if skill is not None else 0,
        "target_level": skill.target_level if skill is not None else 5,
        "evidence": list(skill.evidence) if skill is not None and skill.evidence is not None else [],
    }

    return {"skill": skill_dict}


def evaluate_evidence(state: ReviewerState) -> dict:
    """节点2：计算证据得分。

    LLM 优先（语义理解），失败时 fallback 规则评分。
    """
    task = state.get("task", {})
    learning_log = state.get("learning_log", {})

    # LLM 优先
    llm_result = _evaluate_with_llm(task, learning_log)
    if llm_result is not None:
        return llm_result

    # Fallback: 规则评分
    score = score_evidence(task, learning_log)
    return {"evidence_score": score}


def create_assessment(state: ReviewerState) -> dict:
    """节点3：生成 SkillAssessment 中间结果。

    不直接写 DB，仅产出 assessment dict。
    """
    skill = state.get("skill", {})
    score = state.get("evidence_score", 0)
    old_level = skill.get("level", 0)
    target_level = skill.get("target_level", 5)

    new_level, confidence, reason, should_append = decide_level(
        score, old_level, target_level
    )

    assessment = {
        "skill_id": skill.get("id"),
        "task_id": state.get("task", {}).get("id"),
        "old_level": old_level,
        "new_level": new_level,
        "confidence": confidence,
        "reason": reason,
        "evidence_score": score,
        "should_append_evidence": should_append,
    }
    return {"assessment": assessment}


def apply_skill_update(state: ReviewerState) -> dict:
    """节点4：应用技能等级变更。

    - 写 SkillAssessment 表（中间结果留痕）
    - 更新 Skill.level（如等级有变化）
    - 追加 Skill.evidence（如 should_append）

    db 为 None 或 skill_id 为 None 时：仅内存更新 updated_skill，不写库。
    评估/学习场景下不中断——允许无 DB 的试运行。
    """
    db = state.get("db")
    skill = state.get("skill") or {}
    assessment = state.get("assessment") or {}
    learning_log = state.get("learning_log") or {}
    task = state.get("task") or {}

    updated_skill = dict(skill)
    skill_id = skill.get("id")

    # 技能未注册：仅内存更新，标注原因写入 updated_skill，
    # 让 API 层可区分"评估了但无技能"与"完全没评估"（不再静默跳过）。
    if skill_id is None:
        updated_skill["note"] = "技能未注册，仅生成评估未落库"

    if db is not None and skill_id is not None:
        # 写 SkillAssessment
        db.add(
            SkillAssessment(
                skill_id=skill_id,
                task_id=assessment.get("task_id"),
                old_level=assessment.get("old_level", 0),
                new_level=assessment.get("new_level", 0),
                confidence=assessment.get("confidence", 0.0),
                reason=assessment.get("reason", ""),
                evidence_score=assessment.get("evidence_score", 0),
            )
        )

        # 更新 Skill
        skill_obj = db.query(Skill).filter(Skill.id == skill_id).first()
        if skill_obj is not None:
            new_lvl = assessment.get("new_level", 0)
            old_lvl = assessment.get("old_level", 0)
            if new_lvl != old_lvl:
                skill_obj.level = new_lvl

            if assessment.get("should_append_evidence"):
                entry = build_evidence_entry(task, learning_log)
                current_evidence = list(skill_obj.evidence) if skill_obj.evidence else []
                if entry not in current_evidence:
                    skill_obj.evidence = current_evidence + [entry]

            updated_skill = {
                "id": skill_obj.id,
                "name": skill_obj.name,
                "level": skill_obj.level,
                "target_level": skill_obj.target_level,
                "evidence": list(skill_obj.evidence) if skill_obj.evidence else [],
            }

    return {"updated_skill": updated_skill}


def record_agent_run(state: ReviewerState) -> dict:
    """节点5：记录 Agent 执行到 agent_runs（决策可追溯）。

    Day 6 起 status / duration_ms / trace_id 为独立字段。
    Reviewer 节点内记录为 success（节点执行到此即视为成功）。

    db 为 None 时：不写库，仅返回占位 run_id。
    """
    db = state.get("db")
    task = state.get("task") or {}
    learning_log = state.get("learning_log") or {}
    assessment = state.get("assessment") or {}

    run_id = str(uuid.uuid4())
    input_context = {
        "task_id": task.get("id"),
        "task_title": task.get("title"),
        "skill_name": task.get("skill_name"),
        "log_content": learning_log.get("content", ""),
        "artifact_url": learning_log.get("artifact_url"),
    }
    output_result = {
        "evidence_score": assessment.get("evidence_score", 0),
        "old_level": assessment.get("old_level", 0),
        "new_level": assessment.get("new_level", 0),
        "confidence": assessment.get("confidence", 0.0),
        "reason": assessment.get("reason", ""),
    }

    if db is not None:
        db.add(
            AgentRun(
                id=run_id,
                agent_name="reviewer",
                input_context=json.dumps(input_context, ensure_ascii=False),
                output_result=json.dumps(output_result, ensure_ascii=False),
                status="success",
                duration_ms=0,  # Reviewer 节点内部不计时，由 Executor 统一追踪
                trace_id=run_id,
            )
        )
        db.commit()  # 提交所有写入（SkillAssessment + Skill + AgentRun）

    return {"agent_run_id": run_id}
