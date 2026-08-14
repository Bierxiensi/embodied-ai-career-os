"""Agent Orchestrator API 路由。

Phase 2 Week 1 Day 5：统一 Agent 执行入口。
Phase 2 Week 1 Day 6：Agent Activity 查询（Observability）。

POST /api/agent/run
    输入：用户自然语言意图
    流程：Supervisor 决策 → 按 plan 执行各 Agent → 汇总结果
    输出：执行链路结果（含每个 Agent 的执行状态与输出）

GET /api/agent/runs
    输入：agent_name（可选过滤）、limit（默认 20）
    输出：Agent 执行历史（按时间倒序），含 status / duration_ms / trace_id

设计说明：
- 此端点是 Multi-Agent 系统的统一入口，替代 Day 1-4 的单 Agent 直调
- 现有 /api/planner/generate / /api/reviewer/review 保留，
  供前端单功能直调（如"生成今日任务"按钮）
- /api/agent/run 用于自然语言驱动的多 Agent 协作场景
- /api/agent/runs 用于 Dashboard Agent Activity 面板展示
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_workflow
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.agent_run import AgentRun

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    """Agent 执行请求。

    user_input 为用户自然语言意图，由 Supervisor 解析。
    agent_inputs 可选，允许调用方为特定 Agent 提供精确输入
    （覆盖默认最小输入，提升业务质量）。
    """

    user_input: str = Field(min_length=1, max_length=500, description="用户自然语言意图")
    agent_inputs: dict[str, dict] | None = Field(
        default=None,
        description="各 Agent 输入覆盖，key 为 agent name",
    )


class AgentStepOut(BaseModel):
    """单个 Agent 执行步骤结果。"""

    agent: str                    # Agent 名称
    status: str                   # success / failed / skipped
    output: dict | None = None    # Agent 输出（失败时为 None）
    error: str | None = None      # 失败原因（成功时为 None）
    reason: str | None = None     # 跳过原因（skipped 时填充）


class AgentSummaryOut(BaseModel):
    """工作流汇总信息。"""

    overall_status: str           # success / partial / failed / empty
    intent: str
    total_agents: int
    success_count: int
    failed_count: int
    skipped_count: int
    elapsed_ms: int


class AgentRunResult(BaseModel):
    """Agent 执行链路结果。"""

    user_input: str
    intent: str
    required_agents: list[str]
    execution_plan: dict
    steps: list[AgentStepOut]
    summary: AgentSummaryOut


@router.post("/run")
def run_agent(
    req: AgentRunRequest, db: Session = Depends(get_db)
) -> ApiResponse[AgentRunResult]:
    """统一 Agent 执行入口。

    流程：
      1. Supervisor 分析 user_input，得到 intent + required_agents
      2. 按 plan 顺序执行各 Agent（planner/reviewer/career/research）
      3. 汇总执行结果返回

    失败隔离：单个 Agent 失败不中断整链，status 标记为 failed。
    """
    # 注入 db session 供需要 DB 的 Agent 使用（如 Reviewer 写 SkillAssessment）
    # S3 修复：经 run_workflow → AgentWorkflow.run 透传 db，复用请求事务
    result = run_workflow(req.user_input, req.agent_inputs, db=db)

    # 转换为响应模型
    steps = [
        AgentStepOut(
            agent=s.get("agent", ""),
            status=s.get("status", "failed"),
            output=s.get("output"),
            error=s.get("error"),
            reason=s.get("reason"),
        )
        for s in result.get("steps", [])
    ]

    summary_raw = result.get("summary", {})
    summary = AgentSummaryOut(
        overall_status=summary_raw.get("overall_status", "empty"),
        intent=summary_raw.get("intent", "unknown"),
        total_agents=summary_raw.get("total_agents", 0),
        success_count=summary_raw.get("success_count", 0),
        failed_count=summary_raw.get("failed_count", 0),
        skipped_count=summary_raw.get("skipped_count", 0),
        elapsed_ms=summary_raw.get("elapsed_ms", 0),
    )

    result_out = AgentRunResult(
        user_input=result.get("user_input", ""),
        intent=result.get("intent", "unknown"),
        required_agents=result.get("required_agents", []),
        execution_plan=result.get("execution_plan", {}),
        steps=steps,
        summary=summary,
    )

    return ok(
        result_out,
        message=f"Agent workflow completed: {summary.overall_status} "
                f"({summary.success_count}/{summary.total_agents} agents)",
    )


# ============================================================
# Day 6：Agent Activity 查询（Observability）
# ============================================================


class AgentRunRecord(BaseModel):
    """单条 Agent 执行记录（用于 Activity 面板展示）。"""

    id: str                         # 记录 ID（即 trace_id）
    agent_name: str                 # Agent 名称
    status: str                     # success / failed
    duration_ms: int                # 耗时（毫秒）
    trace_id: str | None            # 追踪 ID（旧数据为 None）
    created_at: datetime            # 创建时间
    output_summary: str             # 输出摘要（前 80 字符，便于面板预览）
    # 保留原始 input/output 供详情查看（前端按需展开）
    input_context: dict
    output_result: dict


class AgentActivityOut(BaseModel):
    """Agent Activity 查询结果。"""

    total: int                      # 查询到的记录总数
    runs: list[AgentRunRecord]      # 执行记录列表（按时间倒序）


def _safe_json_load(raw: str) -> dict:
    """安全解析 JSON 字符串，失败返回空 dict。"""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _extract_summary(output: dict) -> str:
    """从 Agent 输出中提取简短摘要（前 80 字符）。

    不同 Agent 输出结构不同，按优先级提取关键信息：
    - planner：task.title
    - reviewer：score + level 变化
    - career：priority 列表
    - research：plan.summary
    - 其他：整体 JSON 前截断
    """
    if not output:
        return ""
    # 移除 _trace 元信息（Day 6 起不再写入 DB，但兼容 Day 5 历史）
    output = {k: v for k, v in output.items() if k != "_trace"}

    # planner
    task = output.get("task")
    if isinstance(task, dict) and task.get("title"):
        return task["title"][:80]
    # reviewer
    if "evidence_score" in output:
        score = output.get("evidence_score", "?")
        old = output.get("old_level", "?")
        new = output.get("new_level", "?")
        return f"score={score}, level {old}→{new}"[:80]
    # career
    if "priority" in output:
        priority = output.get("priority", [])
        return f"priority: {priority}"[:80]
    # research
    plan = output.get("plan")
    if isinstance(plan, dict) and plan.get("summary"):
        return plan["summary"][:80]
    # fallback
    return json.dumps(output, ensure_ascii=False)[:80]


@router.get("/runs")
def list_agent_runs(
    agent_name: str | None = Query(
        default=None, description="按 Agent 名称过滤（planner/reviewer/career/research）"
    ),
    limit: int = Query(
        default=20, ge=1, le=100, description="返回记录数（最多 100）"
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[AgentActivityOut]:
    """查询 Agent 执行历史（按时间倒序）。

    用于 Dashboard Agent Activity 面板展示。
    支持 agent_name 过滤、limit 限制返回数量。
    """
    query = db.query(AgentRun)
    if agent_name:
        query = query.filter(AgentRun.agent_name == agent_name)

    total = query.count()
    runs = (
        query.order_by(AgentRun.created_at.desc())
        .limit(limit)
        .all()
    )

    records = [
        AgentRunRecord(
            id=r.id,
            agent_name=r.agent_name,
            status=r.status,
            duration_ms=r.duration_ms,
            trace_id=r.trace_id,
            created_at=r.created_at,
            output_summary=_extract_summary(_safe_json_load(r.output_result)),
            input_context=_safe_json_load(r.input_context),
            output_result=_safe_json_load(r.output_result),
        )
        for r in runs
    ]

    return ok(
        AgentActivityOut(total=total, runs=records),
        message=f"Retrieved {len(records)} agent runs"
                + (f" for agent='{agent_name}'" if agent_name else ""),
    )
