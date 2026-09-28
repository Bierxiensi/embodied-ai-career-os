"""Agent 工作流编排核心。

职责：
1. 调用 Supervisor 分析用户意图，得到 required_agents + execution_plan
2. 按 plan 顺序执行各 Agent（planner/reviewer/career/research）
3. 收集每个 Agent 的执行结果，汇总返回

设计要点：
- 顺序执行：Day 5 不做并行调度，按 plan.steps 顺序串行执行
- 上下文传递：前一个 Agent 的输出可作为下一个 Agent 的输入
  （Day 5 暂不实现自动上下文传递，各 Agent 独立执行，结果汇总）
- 失败隔离：单个 Agent 失败不中断整链，记录 error 后继续
  （避免一个 Agent 失败导致整条链路无结果）
- Agent 查找：通过 AgentRegistry 按名查找，解耦具体实现

执行链示例（学习 VLA）：
    Supervisor → required_agents=["research", "planner"]
    → 执行 research → 执行 planner
    → 汇总结果
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.core.registry import AgentRegistry
from app.agents.orchestrator.executor import OrchestratorExecutor
from app.agents.supervisor.state import SupervisorState


class AgentWorkflow:
    """Agent 工作流编排器。

    用法：
        wf = AgentWorkflow()
        result = wf.run("我要学习 VLA")
        # result = {
        #     "user_input": "我要学习 VLA",
        #     "intent": "learn",
        #     "required_agents": ["research", "planner"],
        #     "execution_plan": {...},
        #     "steps": [
        #         {"agent": "research", "status": "success", "output": {...}},
        #         {"agent": "planner", "status": "success", "output": {...}},
        #     ],
        #     "summary": {...},
        # }
    """

    def __init__(self, executor: OrchestratorExecutor | None = None) -> None:
        # 允许注入自定义 executor（如测试 mock），默认用 OrchestratorExecutor
        self._executor = executor or OrchestratorExecutor()
        # Y9：run() 在 supervisor 决策前落存 user_input，
        # 供 _run_single_agent → _resolve_input 做意图→参数提取（实例级，非全局）
        self._last_user_input = ""

    def run(
        self,
        user_input: str,
        agent_inputs: dict[str, dict] | None = None,
        db: Any = None,
    ) -> dict:
        """执行完整工作流：Supervisor 决策 → 按 plan 执行各 Agent。

        Args:
            user_input: 用户原始输入文本
            agent_inputs: 各 Agent 的输入 state 覆盖。
                          key 为 agent name，value 为输入 dict。
                          未提供时用默认输入（Day 5 用最小可用输入）。
            db: 可选 DB session。注入后复用请求事务（如 Reviewer 写 SkillAssessment）；
                为 None 时各 Agent 自建 session 或安全降级（不写库）。

        Returns:
            工作流执行结果（含 supervisor 结果 + 各 agent 步骤 + 汇总）。
        """
        start_ms = time.perf_counter()

        # S3 修复：注入 db 时重建 executor，让 _record 与节点层都复用请求事务
        if db is not None:
            self._executor = OrchestratorExecutor(db=db)

        # Y9：在 supervisor 决策前落存 user_input，子 agent 输入提取用
        self._last_user_input = user_input

        # 1. Supervisor 决策
        supervisor_result = self._run_supervisor(user_input)

        required_agents: list[str] = supervisor_result.get("required_agents", [])
        execution_plan: dict = supervisor_result.get("execution_plan", {})
        intent: str = supervisor_result.get("intent", "unknown")

        # 停止规则（spec §4.3）：一次会话最多 1 个主 Agent + 可选 1 个 knowledge；
        # decision-ready 即停——不因能力存在就多派 agent。
        MAX_AGENTS_PER_RUN = 2
        agent_inputs = agent_inputs or {}
        steps: list[dict] = []
        for agent_name in required_agents[:MAX_AGENTS_PER_RUN]:
            step = self._run_single_agent(agent_name, agent_inputs, db)
            steps.append(step)

        # 3. 汇总结果
        elapsed_ms = int((time.perf_counter() - start_ms) * 1000)
        summary = self._build_summary(
            user_input=user_input,
            intent=intent,
            required_agents=required_agents,
            steps=steps,
            elapsed_ms=elapsed_ms,
        )

        return {
            "user_input": user_input,
            "intent": intent,
            "required_agents": required_agents,
            "execution_plan": execution_plan,
            "steps": steps,
            "summary": summary,
        }

    def _run_supervisor(self, user_input: str) -> dict:
        """执行 Supervisor Agent，返回决策结果。

        Supervisor 内部不写 agent_runs（纯决策），由 orchestrator 统一 tracing。
        """
        supervisor = AgentRegistry.get("supervisor")
        if supervisor is None:
            return {
                "intent": "unknown",
                "required_agents": [],
                "execution_plan": {},
                "result": {"status": "error", "message": "supervisor not registered"},
            }

        state: SupervisorState = {"user_input": user_input}
        return supervisor.invoke(state)

    def _run_single_agent(
        self,
        agent_name: str,
        agent_inputs: dict[str, dict],
        db: Any = None,
    ) -> dict:
        """执行单个 Agent，封装为步骤结果。

        失败隔离：捕获异常，记录 error，不抛出。
        """
        agent = AgentRegistry.get(agent_name)

        # Agent 未注册
        if agent is None:
            return {
                "agent": agent_name,
                "status": "skipped",
                "reason": f"agent '{agent_name}' not registered",
                "output": None,
            }

        # 取输入 state：优先用调用方提供的覆盖，其次 user_input 意图提取，最后占位/画像默认
        input_state = self._resolve_input(
            agent_name, agent_inputs, db, user_input=self._last_user_input
        )

        try:
            output = self._executor.run(agent_name, input_state)
            return {
                "agent": agent_name,
                "status": "success",
                "output": output,
            }
        except Exception as e:
            # 失败隔离：记录 error，不中断整链
            return {
                "agent": agent_name,
                "status": "failed",
                "error": str(e),
                "output": None,
            }

    def _extract_params(self, user_input: str, agent_name: str) -> dict | None:
        """意图→参数提取（Y9）：从用户话里抽 topic / 可用时长 / 目标技能。

        LLM 优先，失败回退规则；都提取不出返回 None（调用方再走占位兜底）。
        契约同 supervisor._analyze_intent_llm：任何异常返回 None，不抛出。
        """
        text = (user_input or "").strip()
        if not text:
            return None

        # knowledge：问题原文直透（检索节点自行预处理）。
        # 放在 topic/时长提取之前，保证不论是否抽出参数都返回 question，
        # 否则 ask→knowledge 链路拿到空 question，永远答"未在知识库中找到"。
        if agent_name == "knowledge":
            return {"question": text}

        # ---- 规则兜底：时长 + 主题 ----
        import re

        minutes = None
        m = re.search(r"(\d{2,3})\s*(分钟|min|minutes)", text, re.IGNORECASE)
        if m:
            minutes = max(5, min(480, int(m.group(1))))
        topic = None
        for kw in ("SFT", "LoRA", "QLoRA", "DPO", "GRPO", "RLHF", "PPO", "vLLM", "VLM"):
            if kw.lower() in text.lower():
                topic = kw
                break

        # ---- LLM 优先 ----
        try:
            from app.llm import ChatMessage, get_llm

            llm = get_llm()
            result = llm.chat_json([
                ChatMessage(role="system", content="你是参数提取器。只输出 JSON。"),
                ChatMessage(
                    role="user",
                    content=(
                        "从用户输入提取学习参数，主题必须是这些之一："
                        "SFT/LoRA/QLoRA/DPO/GRPO/RLHF/PPO/vLLM/VLM/其他。\n"
                        f'用户输入："{text}"\n'
                        '返回 JSON：{"topic": "<主题或null>", "available_minutes": <int或null>}'
                    ),
                ),
            ])
            if isinstance(result, dict):
                topic = result.get("topic") or topic
                if result.get("available_minutes"):
                    minutes = max(5, min(480, int(result["available_minutes"])))
        except Exception:
            pass

        if minutes is None and topic is None:
            return None
        if agent_name == "research":
            return {"topic": topic or "Post-Training"}
        if agent_name == "planner":
            return {"available_minutes": minutes or 45, "skills": self._real_skills()}
        return {}

    @staticmethod
    def _real_skills() -> list[dict]:
        """真实技能画像（前 6 项）→ Planner 的 SkillInput dict。

        SKILL_PROFILE 元素是 SkillProfile dataclass：字段为 name/level/
        target_level（无 target 字段），而 PlannerState.SkillInput 键是
        name/level/target，故在此做 target_level → target 的显式映射。
        """
        from app.core.skill_profile import SKILL_PROFILE

        return [
            {"name": s.name, "level": s.level, "target": s.target_level}
            for s in SKILL_PROFILE[:6]
        ]

    def _resolve_input(
        self,
        agent_name: str,
        agent_inputs: dict[str, dict],
        db: Any = None,
        user_input: str = "",
    ) -> dict:
        """解析 Agent 输入 state（Y9 重写，2026-09-24）。

        优先级：调用方覆盖 > 意图提取（user_input）> 真实画像默认 > 占位（显式标记）。
        占位只保证 Agent 不报错，且打 `_input_source=placeholder` 痕迹，
        不得冒充真实输入（旧实现的 Isaac 占位曾被 Dashboard 当真实活动展示）。
        """
        if agent_name in agent_inputs:
            return agent_inputs[agent_name]

        extracted = self._extract_params(user_input, agent_name)
        if extracted:
            return extracted

        real_skills = self._real_skills()
        defaults: dict[str, dict] = {
            "planner": {
                "available_minutes": 45,
                "skills": real_skills,
                "_input_source": "profile_default",
                # L2 修复：移除 "persist": False。
                # persist 是 OrchestratorExecutor 的参数而非 state key，
                # 原值被 PlannerState 静默丢弃；agent_runs 落库由 executor 默认 persist=True 控制。
            },
            "reviewer": {
                "task": {
                    "id": 0,
                    "title": "Post-Training 概念入门",
                    "skill_name": "SFT",
                    "acceptance": ["能描述 SFT 的目标", "能区分 SFT 与 RLHF"],
                },
                "learning_log": {
                    "content": user_input or "（无日志内容）",
                    "duration_minutes": 45,
                    "artifact_url": None,
                },
                # S3 修复：透传请求 db，避免节点自建 session；None 时节点安全降级
                "db": db,
                "_input_source": "profile_default",
            },
            "career": {
                "target_role": "大模型后训练 / Post-Training 算法工程师（主攻）",
                "current_skills": real_skills,
                "_input_source": "profile_default",
            },
            "research": {
                "topic": "DPO",
                "_input_source": "placeholder",
            },
        }
        return defaults.get(agent_name, {})

    def _build_summary(
        self,
        user_input: str,
        intent: str,
        required_agents: list[str],
        steps: list[dict],
        elapsed_ms: int,
    ) -> dict:
        """构建工作流汇总信息。"""
        success_count = sum(1 for s in steps if s.get("status") == "success")
        failed_count = sum(1 for s in steps if s.get("status") == "failed")
        skipped_count = sum(1 for s in steps if s.get("status") == "skipped")

        # 整体状态：全部成功为 success，有失败为 partial，全部失败为 failed
        if not steps:
            overall = "empty"
        elif failed_count == 0 and skipped_count == 0:
            overall = "success"
        elif success_count == 0:
            overall = "failed"
        else:
            overall = "partial"

        return {
            "overall_status": overall,
            "intent": intent,
            "total_agents": len(required_agents),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "elapsed_ms": elapsed_ms,
        }


# ===== 便捷函数 =====

def run_workflow(
    user_input: str,
    agent_inputs: dict[str, dict] | None = None,
    db: Any = None,
) -> dict:
    """便捷函数：创建 workflow 并执行。

    Args:
        user_input: 用户原始输入
        agent_inputs: 各 Agent 输入覆盖
        db: 可选 DB session，透传给需要 DB 的 Agent（如 Reviewer）

    Returns:
        工作流执行结果
    """
    return AgentWorkflow().run(user_input, agent_inputs, db=db)
