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
        # 允许注入自定义 executor（如测试 mock），默认用 AgentExecutor
        self._executor = executor or OrchestratorExecutor()

    def run(
        self,
        user_input: str,
        agent_inputs: dict[str, dict] | None = None,
    ) -> dict:
        """执行完整工作流：Supervisor 决策 → 按 plan 执行各 Agent。

        Args:
            user_input: 用户原始输入文本
            agent_inputs: 各 Agent 的输入 state 覆盖。
                          key 为 agent name，value 为输入 dict。
                          未提供时用默认输入（Day 5 用最小可用输入）。

        Returns:
            工作流执行结果（含 supervisor 结果 + 各 agent 步骤 + 汇总）。
        """
        start_ms = time.perf_counter()

        # 1. Supervisor 决策
        supervisor_result = self._run_supervisor(user_input)

        required_agents: list[str] = supervisor_result.get("required_agents", [])
        execution_plan: dict = supervisor_result.get("execution_plan", {})
        intent: str = supervisor_result.get("intent", "unknown")

        # 2. 按 plan 顺序执行各 Agent
        agent_inputs = agent_inputs or {}
        steps: list[dict] = []
        for agent_name in required_agents:
            step = self._run_single_agent(agent_name, agent_inputs)
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

        # 取输入 state：优先用调用方提供的覆盖，否则用默认最小输入
        input_state = self._resolve_input(agent_name, agent_inputs)

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

    def _resolve_input(
        self,
        agent_name: str,
        agent_inputs: dict[str, dict],
    ) -> dict:
        """解析 Agent 输入 state。

        优先用调用方提供的覆盖；未提供时用默认最小输入。
        Day 5 默认输入仅保证 Agent 不报错，业务质量由后续迭代优化。
        """
        if agent_name in agent_inputs:
            return agent_inputs[agent_name]

        # 默认最小输入（各 Agent 的必需字段）
        # reviewer：不提供 db 则用 None，节点内会安全降级（不写库，仅内存评估）
        # task 用合理示例内容（不依赖存在的 task_id），仅触发证据打分逻辑
        defaults: dict[str, dict] = {
            "planner": {
                "available_minutes": 45,
                "skills": [{"name": "Isaac", "level": 0, "target": 4}],
                "persist": False,
            },
            "reviewer": {
                "task": {
                    "id": 0,
                    "title": "Robot Learning 基础概念入门",
                    "skill_name": "Isaac",
                    "acceptance": [
                        "能描述 Robot Learning 核心问题",
                        "能区分 Imitation Learning 与 RL",
                    ],
                },
                "learning_log": {
                    "content": "学习了 Robot Learning 基础概念，阅读了 Imitation "
                               "Learning 与 Reinforcement Learning 的差异，理解了 "
                               "State/Action/Reward 基本定义。",
                    "duration_minutes": 45,
                    "artifact_url": None,
                },
                "db": None,  # orchestrator 内默认不写库，真实场景由调用方注入
            },
            "career": {
                "target_role": "Robot AI Engineer",
                "current_skills": [
                    {"name": "Isaac", "level": 0, "target": 4},
                    {"name": "ROS2", "level": 1, "target": 4},
                ],
            },
            "research": {
                "topic": "ACT",
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
) -> dict:
    """便捷函数：创建 workflow 并执行。

    Args:
        user_input: 用户原始输入
        agent_inputs: 各 Agent 输入覆盖

    Returns:
        工作流执行结果
    """
    return AgentWorkflow().run(user_input, agent_inputs)
