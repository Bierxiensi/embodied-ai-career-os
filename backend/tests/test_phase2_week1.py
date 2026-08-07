"""Embodied AI Career OS · Phase 2 Week 1 全量集成测试。

覆盖维度（Day 1-7 所有模块）：
  1. Agent Runtime（core/）：BaseAgent / AgentState / AgentExecutor / AgentRegistry
  2. Supervisor Agent：4 种意图路由（learn/complete/career/unknown）
  3. Career Agent：Gap 分析 + 优先级排序 + 推荐路线
  4. Research Agent：模板匹配 + fallback + 任务拆解
  5. Planner/Reviewer 适配类：与现有业务零改动兼容
  6. Agent Orchestrator：执行链 + 失败隔离 + agent_runs 持久化
  7. Agent Observability：GET /api/agent/runs + status/duration_ms/trace_id 字段

执行方式：
    cd backend && python tests/test_phase2_week1.py

前置条件：
    - 后端运行在 localhost:8000
    - 数据库已执行 0001 迁移（agent_runs 含 status/duration_ms/trace_id）
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import datetime

import requests

# ===== 配置 =====
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
DB_PATH = "/workspace/embodied-ai-career-os/backend/data/app.db"


# ===== 测试结果收集 =====
class TestResult:
    def __init__(self, suite: str, case_id: str, name: str):
        self.suite = suite
        self.case_id = case_id
        self.name = name
        self.status = "RUN"
        self.detail = ""
        self.elapsed_ms = 0

    def to_dict(self) -> dict:
        return {
            "suite": self.suite,
            "case_id": self.case_id,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "elapsed_ms": self.elapsed_ms,
        }


results: list[TestResult] = []


def run_case(suite: str, case_id: str, name: str, fn):
    r = TestResult(suite, case_id, name)
    start = time.perf_counter()
    try:
        fn(r)
        if r.status == "RUN":
            r.status = "PASS"
    except AssertionError as e:
        r.status = "FAIL"
        r.detail = f"AssertionError: {e}"
    except Exception as e:  # noqa: BLE001
        r.status = "FAIL"
        r.detail = f"{type(e).__name__}: {e}"
    r.elapsed_ms = int((time.perf_counter() - start) * 1000)
    results.append(r)
    icon = "✓" if r.status == "PASS" else "✗"
    print(f"  {icon} [{case_id}] {name}" +
          (f" — {r.detail}" if r.status != "PASS" else ""))
    return r


# ===== 工具函数 =====
def db_query(sql: str, params: tuple = ()) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.cursor().execute(sql, params).fetchall()
    finally:
        conn.close()


def wait_backend(timeout: int = 30) -> bool:
    for _ in range(timeout):
        try:
            if requests.get(f"{BACKEND_URL}/health", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


# ============================================================
# 测试套件 1：Agent Runtime（core/）
# ============================================================
def test_agent_runtime():
    suite = "Agent Runtime"

    def t01(r: TestResult):
        """AgentRegistry 注册 5 个 Agent。"""
        from app.agents.registry_setup import setup_default_agents
        from app.agents.core.registry import AgentRegistry
        names = setup_default_agents()
        expected = {"supervisor", "planner", "reviewer", "career", "research"}
        assert set(names) == expected, f"期望 {expected}，实际 {set(names)}"
        r.detail = f"agents={names}"

    run_case(suite, "RT-01", "AgentRegistry 注册 5 个 Agent", t01)

    def t02(r: TestResult):
        """BaseAgent 契约：name/state_class/build_graph。"""
        from app.agents.core.registry import AgentRegistry
        for name in ["supervisor", "planner", "reviewer", "career", "research"]:
            agent = AgentRegistry.get(name)
            assert agent is not None, f"{name} 未注册"
            assert agent.name == name, f"{name}.name 不匹配"
            assert agent.state_class is not None, f"{name} 缺 state_class"
            graph = agent.build_graph()
            assert graph is not None, f"{name} build_graph 返回 None"
        r.detail = "5 agents 契约校验通过"

    run_case(suite, "RT-02", "BaseAgent 契约（name/state_class/build_graph）", t02)

    def t03(r: TestResult):
        """AgentExecutor 执行 + tracing 持久化。"""
        from app.agents.core.executor import AgentExecutor
        from app.agents.core.registry import AgentRegistry
        from app.db.base import SessionLocal
        from app.models.agent_run import AgentRun

        before = db_query("SELECT COUNT(*) FROM agent_runs")[0][0]
        agent = AgentRegistry.get("research")
        executor = AgentExecutor(agent)
        out = executor.run({"topic": "ACT"}, persist=True)
        after = db_query("SELECT COUNT(*) FROM agent_runs")[0][0]

        assert after == before + 1, f"agent_runs 应 +1，{before}→{after}"
        assert "_trace" in out, "输出缺 _trace"
        assert out["_trace"]["status"] == "success"
        r.detail = f"trace: status={out['_trace']['status']}, " \
                   f"duration={out['_trace']['duration_ms']}ms"

    run_case(suite, "RT-03", "AgentExecutor 执行 + tracing 持久化", t03)


# ============================================================
# 测试套件 2：Supervisor Agent
# ============================================================
def test_supervisor():
    suite = "Supervisor"

    def make_case(inp, expected_intent, expected_agents, case_id, name):
        def fn(r: TestResult):
            from app.agents.supervisor.graph import build_supervisor_graph
            g = build_supervisor_graph()
            out = g.invoke({"user_input": inp})
            assert out["intent"] == expected_intent, \
                f"intent 期望 {expected_intent}，实际 {out['intent']}"
            assert set(out["required_agents"]) == set(expected_agents), \
                f"agents 期望 {expected_agents}，实际 {out['required_agents']}"
            r.detail = f"intent={out['intent']}, agents={out['required_agents']}"
        run_case(suite, case_id, name, fn)

    make_case("我要学习 VLA", "learn", ["research", "planner"], "SV-01", "学习意图 → research+planner")
    make_case("完成今天的任务", "complete", ["reviewer"], "SV-02", "完成意图 → reviewer")
    make_case("我要成为 Robot AI Engineer", "career", ["career"], "SV-03", "职业意图 → career")
    make_case("你好", "unknown", ["planner"], "SV-04", "未知意图 → planner fallback")


# ============================================================
# 测试套件 3：Career Agent
# ============================================================
def test_career():
    suite = "Career Agent"

    def t01(r: TestResult):
        """Gap 分析 + 优先级排序。"""
        from app.agents.career.graph import build_career_graph
        g = build_career_graph()
        out = g.invoke({
            "target_role": "Robot AI Engineer",
            "current_skills": [
                {"name": "ROS2", "level": 1, "target": 4},
                {"name": "Isaac", "level": 0, "target": 4},
                {"name": "PyTorch", "level": 3, "target": 4},
            ],
        })
        priority = out.get("priority", [])
        assert priority[0] == "Isaac", f"首应 Isaac，实际 {priority[0]}"
        assert priority[1] == "ROS2", f"次应 ROS2，实际 {priority[1]}"
        r.detail = f"priority={priority}"

    run_case(suite, "CA-01", "Gap 分析 + 优先级排序", t01)

    def t02(r: TestResult):
        """已达标技能过滤。"""
        from app.agents.career.graph import build_career_graph
        g = build_career_graph()
        out = g.invoke({
            "target_role": "Robot AI Engineer",
            "current_skills": [
                {"name": "PyTorch", "level": 5, "target": 4},  # gap=0
            ],
        })
        priority = out.get("priority", [])
        assert "PyTorch" not in priority, "已达标技能不应进 priority"
        r.detail = "PyTorch gap=0 已过滤"

    run_case(suite, "CA-02", "已达标技能过滤", t02)


# ============================================================
# 测试套件 4：Research Agent
# ============================================================
def test_research():
    suite = "Research Agent"

    def t01(r: TestResult):
        """预设模板匹配（ACT）。"""
        from app.agents.research.graph import build_research_graph
        g = build_research_graph()
        out = g.invoke({"topic": "ACT"})
        plan = out["plan"]
        assert plan["topic"] == "ACT"
        tasks = plan["tasks"]
        assert len(tasks) == 4, f"应有 4 项任务，实际 {len(tasks)}"
        cats = [t["category"] for t in tasks]
        assert cats == ["paper", "code", "experiment", "verification"]
        assert "ACT" in tasks[0]["title"]
        r.detail = f"topic={plan['topic']}, tasks={len(tasks)}"

    run_case(suite, "RS-01", "预设模板匹配（ACT）", t01)

    def t02(r: TestResult):
        """别名匹配（小写输入 → 标准 topic）。"""
        from app.agents.research.graph import build_research_graph
        g = build_research_graph()
        out = g.invoke({"topic": "isaac lab"})
        assert out["plan"]["topic"] == "Isaac Lab", \
            f"别名应映射 Isaac Lab，实际 {out['plan']['topic']}"
        r.detail = f"isaac lab → {out['plan']['topic']}"

    run_case(suite, "RS-02", "别名匹配", t02)

    def t03(r: TestResult):
        """未知主题 fallback。"""
        from app.agents.research.graph import build_research_graph
        g = build_research_graph()
        out = g.invoke({"topic": "Diffusion Policy"})
        plan = out["plan"]
        assert plan["topic"] == "Diffusion Policy"
        assert len(plan["tasks"]) == 4, "fallback 应仍生成 4 项任务"
        r.detail = f"fallback topic={plan['topic']}"

    run_case(suite, "RS-03", "未知主题 fallback", t03)


# ============================================================
# 测试套件 5：Orchestrator（执行链）
# ============================================================
def test_orchestrator():
    suite = "Orchestrator"

    def t01(r: TestResult):
        """学习意图执行链：research + planner。"""
        resp = requests.post(
            f"{BACKEND_URL}/api/agent/run",
            json={
                "user_input": "学习 Isaac Lab",
                "agent_inputs": {"research": {"topic": "Isaac Lab"}},
            },
            timeout=15,
        )
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        data = resp.json()["data"]
        assert data["intent"] == "learn"
        agents_executed = [s["agent"] for s in data["steps"]]
        assert "research" in agents_executed
        assert "planner" in agents_executed
        assert data["summary"]["overall_status"] == "success"
        r.detail = f"agents={agents_executed}, status={data['summary']['overall_status']}"

    run_case(suite, "OR-01", "学习意图执行链（research+planner）", t01)

    def t02(r: TestResult):
        """职业意图执行链：career。"""
        resp = requests.post(
            f"{BACKEND_URL}/api/agent/run",
            json={"user_input": "我要成为 Robot AI Engineer"},
            timeout=15,
        )
        data = resp.json()["data"]
        assert data["intent"] == "career"
        agents_executed = [s["agent"] for s in data["steps"]]
        assert "career" in agents_executed
        r.detail = f"agents={agents_executed}"

    run_case(suite, "OR-02", "职业意图执行链（career）", t02)

    def t03(r: TestResult):
        """空输入校验（422）。"""
        resp = requests.post(
            f"{BACKEND_URL}/api/agent/run",
            json={"user_input": ""},
            timeout=5,
        )
        assert resp.status_code == 422, f"期望 422，实际 {resp.status_code}"
        r.detail = f"HTTP {resp.status_code}"

    run_case(suite, "OR-03", "空输入校验（422）", t03)


# ============================================================
# 测试套件 6：Observability
# ============================================================
def test_observability():
    suite = "Observability"

    def t01(r: TestResult):
        """GET /api/agent/runs 返回执行历史。"""
        resp = requests.get(
            f"{BACKEND_URL}/api/agent/runs?limit=10",
            timeout=5,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] > 0, "应有历史记录"
        assert len(data["runs"]) <= 10
        run = data["runs"][0]
        # 验证新字段存在
        assert "status" in run, "缺 status 字段"
        assert "duration_ms" in run, "缺 duration_ms 字段"
        assert "trace_id" in run, "缺 trace_id 字段"
        assert "output_summary" in run, "缺 output_summary 字段"
        r.detail = f"total={data['total']}, fields OK"

    run_case(suite, "OB-01", "GET /api/agent/runs 返回历史 + 新字段", t01)

    def t02(r: TestResult):
        """agent_name 过滤生效。"""
        resp = requests.get(
            f"{BACKEND_URL}/api/agent/runs?agent_name=planner&limit=5",
            timeout=5,
        )
        data = resp.json()["data"]
        agents = set(r["agent_name"] for r in data["runs"])
        assert agents == {"planner"}, f"应只含 planner，实际 {agents}"
        r.detail = f"planner total={data['total']}"

    run_case(suite, "OB-02", "agent_name 过滤生效", t02)

    def t03(r: TestResult):
        """新记录含 duration_ms > 0（通过 orchestrator 触发）。"""
        before = db_query("SELECT COUNT(*) FROM agent_runs")[0][0]
        requests.post(
            f"{BACKEND_URL}/api/agent/run",
            json={"user_input": "学习 VLA", "agent_inputs": {"research": {"topic": "VLA"}}},
            timeout=15,
        )
        # 查最新 research 记录
        rows = db_query(
            "SELECT duration_ms, trace_id FROM agent_runs "
            "WHERE agent_name='research' ORDER BY created_at DESC LIMIT 1"
        )
        assert rows, "未找到新 research 记录"
        assert rows[0]["duration_ms"] > 0, f"duration_ms 应 >0，实际 {rows[0]['duration_ms']}"
        assert rows[0]["trace_id"] is not None, "trace_id 不应为 None"
        r.detail = f"duration_ms={rows[0]['duration_ms']}, trace_id={rows[0]['trace_id'][:8]}"

    run_case(suite, "OB-03", "新记录含 duration_ms + trace_id", t03)

    def t04(r: TestResult):
        """limit 边界校验（422）。"""
        resp = requests.get(
            f"{BACKEND_URL}/api/agent/runs?limit=0",
            timeout=5,
        )
        assert resp.status_code == 422
        r.detail = f"limit=0 → HTTP {resp.status_code}"

    run_case(suite, "OB-04", "limit 边界校验", t04)


# ============================================================
# 测试套件 7：现有业务零改动
# ============================================================
def test_backward_compat():
    suite = "向后兼容"

    def t01(r: TestResult):
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        assert resp.status_code == 200
        r.detail = "HTTP 200"

    run_case(suite, "BC-01", "/health 可用", t01)

    def t02(r: TestResult):
        resp = requests.get(f"{BACKEND_URL}/api/skills", timeout=5)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        r.detail = f"skills count={len(body['data'])}"

    run_case(suite, "BC-02", "/api/skills 可用", t02)

    def t03(r: TestResult):
        resp = requests.post(
            f"{BACKEND_URL}/api/planner/generate",
            json={
                "available_minutes": 30,
                "skills": [{"name": "ROS2", "level": 1, "target": 4}],
                "persist": False,
            },
            timeout=10,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        r.detail = f"skill={body['data']['skill']}"

    run_case(suite, "BC-03", "POST /api/planner/generate 可用", t03)


# ===== 主入口 =====
def main():
    print("=" * 60)
    print("  Phase 2 Week 1 全量集成测试")
    print("=" * 60)

    if not wait_backend(30):
        print("✗ 后端不可达，请启动: uvicorn app.main:app --port 8000")
        sys.exit(1)

    # 确保注册
    from app.agents.registry_setup import setup_default_agents
    setup_default_agents()

    print("\n[套件 1] Agent Runtime")
    test_agent_runtime()
    print("\n[套件 2] Supervisor")
    test_supervisor()
    print("\n[套件 3] Career Agent")
    test_career()
    print("\n[套件 4] Research Agent")
    test_research()
    print("\n[套件 5] Orchestrator")
    test_orchestrator()
    print("\n[套件 6] Observability")
    test_observability()
    print("\n[套件 7] 向后兼容")
    test_backward_compat()

    # 汇总
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")

    print("\n" + "=" * 60)
    print(f"  总计 {total} | 通过 {passed} | 失败 {failed}")
    print("=" * 60)

    if failed:
        print("\n失败用例:")
        for r in results:
            if r.status == "FAIL":
                print(f"  ✗ [{r.case_id}] {r.name}: {r.detail}")
        sys.exit(1)
    else:
        print("\n✓ 全部通过")


if __name__ == "__main__":
    main()
