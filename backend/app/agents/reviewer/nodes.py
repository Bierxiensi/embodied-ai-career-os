"""Reviewer Agent 的 LangGraph 节点。

每个节点接收 state，返回 dict（LangGraph 合并到状态）。

只读铁律（spec §4.3）：Reviewer 链路**不写** SkillAssessment / skill 等级——
节点只产出契约提案（review），落库唯一通道是
``app.services.evidence_events.apply_review_proposal``（API 层调用）。
collect_context / evaluate_evidence 只读 DB 或不碰 DB；
record_agent_run 仍写 agent_runs（tracing，非技能状态）。

流程：
    collect_context → evaluate_evidence → create_assessment
    → apply_skill_update（只读投影） → record_agent_run
"""

from __future__ import annotations

import json
import uuid

from app.agents.reviewer.rules import (
    decide_level,
    score_evidence,
)
from app.agents.reviewer.state import ReviewerState
from app.models.agent_run import AgentRun
from app.models.skill import Skill


# ============================================================
# 评审契约（fail-closed，spec §4.3）
# ============================================================


def validate_review_contract(payload: dict) -> dict:
    """评审契约校验（fail-closed，spec §4.3）。

    任何缺字段/类型错 → verdict=block，如实带 error；不静默降分、不吞异常。
    """
    required = {
        "skill_name": str,
        "proposed_level": int,
        "evidence_score": int,
        "reason": str,
        "evidence_refs": list,
    }
    try:
        for field, typ in required.items():
            if field not in payload or not isinstance(payload[field], typ):
                return {**payload, "verdict": "block", "error": f"contract:{field}"}
        if not (0 <= payload["proposed_level"] <= 5):
            return {**payload, "verdict": "block", "error": "contract:proposed_level_range"}
        if not (0 <= payload["evidence_score"] <= 100):
            return {**payload, "verdict": "block", "error": "contract:evidence_score_range"}
        payload.setdefault("verdict", "pass")
        return payload
    except Exception as e:  # 校验自身异常也必须 fail-closed
        return {"verdict": "block", "error": f"contract:validator_crashed:{e}"}


def _evidence_refs(task: dict, learning_log: dict) -> list[str]:
    """从产出链接提取可追溯 ref（commit:sha）。

    只认 commit 型 URL：ref 词表是 unit_item:id / commit:sha / experiment:id，
    杜绝把任意链接冒充证据。取不到可追溯 ref 时返回空列表——
    apply_review_proposal 会以 evidence_refs_empty 拒绝落库（防虚构）。
    """
    url = str(learning_log.get("artifact_url") or "").strip()
    if "/commit/" not in url:
        return []
    sha = url.rstrip("/").split("/commit/")[-1].split("/")[0].split("?")[0]
    return [f"commit:{sha}"] if sha else []


def _build_review_proposal(state: ReviewerState, score: int) -> dict:
    """把评分结果组装成契约提案（只读；是否落库由 apply 层裁决）。"""
    task = state.get("task") or {}
    skill = state.get("skill") or {}
    learning_log = state.get("learning_log") or {}

    old_level = int(skill["level"]) if skill.get("level") is not None else 0
    target_level = (
        int(skill["target_level"]) if skill.get("target_level") is not None else 5
    )
    new_level, _confidence, reason, _should_append = decide_level(
        score, old_level, target_level
    )
    return {
        "skill_name": task.get("skill_name") or skill.get("name") or "",
        "proposed_level": int(new_level),
        "evidence_score": int(score),
        "reason": reason,
        "evidence_refs": _evidence_refs(task, learning_log),
        "verdict": "pass",
    }


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
        "你是大模型后训练（Post-Training）学习导师。评估学生的一次学习成果。\n\n"
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
    """节点2：计算证据得分并产出契约提案（只读，spec §4.3）。

    LLM 优先（语义理解），失败时 fallback 规则评分；
    评分结果组装成 review 提案后必须过 validate_review_contract——
    契约不通过（缺字段/类型错/越界）→ verdict=block + applied=False，零写库。
    本节点不落库；是否落库由 API 层经 apply_review_proposal 裁决。
    """
    task = state.get("task", {})
    learning_log = state.get("learning_log", {})

    # LLM 优先
    llm_result = _evaluate_with_llm(task, learning_log)
    if llm_result is not None:
        score = int(llm_result["evidence_score"])
        extra = {"llm_evaluation": llm_result.get("llm_evaluation")}
    else:
        # Fallback: 规则评分
        score = score_evidence(task, learning_log)
        extra = {}

    result = validate_review_contract(_build_review_proposal(state, score))
    if result.get("verdict") == "block":
        # fail-closed：契约不过，提案直接裁决为 block，不写库、不降分
        return {"evidence_score": score, "review": result, "applied": False, **extra}
    return {"evidence_score": score, "review": result, **extra}


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
    """节点4：投影技能状态（只读，spec §4.3）。

    历史行为（写 SkillAssessment / 改 Skill.level / 追加 Skill.evidence）
    已整体移交 API 层的 apply_review_proposal——本节点不再碰 DB，只把
    collect_context 读到的当前状态投影给响应；API 层在 apply 成功后用
    DB 真值刷新 updated_skill。
    """
    skill = state.get("skill") or {}

    updated_skill = dict(skill)
    # 技能未注册：标注原因，让 API 层可区分"评估了但无技能"与"完全没评估"
    if updated_skill.get("id") is None:
        updated_skill["note"] = "技能未注册，仅生成评估未落库"

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
        db.commit()  # 提交 tracing + 路由前置事实写入（Task/LearningLog/AgentRun）；
        # SkillAssessment / Skill 等级由 API 层 apply_review_proposal 单独提交

    return {"agent_run_id": run_id}
