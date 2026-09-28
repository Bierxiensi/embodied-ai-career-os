"""Y9：编排链子 agent 输入必须来自 user_input / 真实画像，不再是 Isaac 占位。

覆盖两块（spec §4.3 / §5.2）：
1. `_resolve_input` 真传 user_input：意图提取优先，占位显式打标
2. 编排收窄（learn→planner、ask→knowledge，每意图最多 1 个主 Agent）
   + 停止规则（单次 run 最多 2 个 agent）+ 查询类意图零业务写入
"""

from app.agents.orchestrator.workflow import AgentWorkflow


def test_research_topic_extracted_from_input():
    wf = AgentWorkflow()
    state = wf._resolve_input("research", {}, user_input="我想学 DPO 的损失函数")
    assert state["topic"] == "DPO"


def test_planner_skills_come_from_real_profile_not_isaac():
    wf = AgentWorkflow()
    state = wf._resolve_input("planner", {}, user_input="今晚有 60 分钟，学一下 LoRA")
    assert state["available_minutes"] == 60
    skills_text = str(state["skills"])
    assert "Isaac" not in skills_text
    assert skills_text != "[]"


def test_explicit_override_still_wins():
    wf = AgentWorkflow()
    state = wf._resolve_input("research", {"research": {"topic": "GRPO"}}, user_input="DPO")
    assert state["topic"] == "GRPO"


def test_placeholder_marked_when_no_user_input():
    """无 user_input 时占位必须显式打标 `_input_source=placeholder`。

    research 的默认 topic 是占位内容；planner/career 默认走真实画像，
    标 `profile_default`（见 _resolve_input defaults）。
    """
    wf = AgentWorkflow()
    state = wf._resolve_input("research", {}, user_input="")
    assert state.get("_input_source") == "placeholder"
    # 真实画像默认路径同样有痕迹，且不再含 Isaac 占位
    planner_state = wf._resolve_input("planner", {}, user_input="")
    assert planner_state.get("_input_source") == "profile_default"
    assert "Isaac" not in str(planner_state["skills"])


def test_intent_map_narrowed_and_ask_reaches_knowledge():
    from app.agents.supervisor.nodes import INTENT_AGENTS_MAP, analyze_intent

    assert INTENT_AGENTS_MAP["learn"] == ["planner"]
    assert INTENT_AGENTS_MAP["ask"] == ["knowledge"]
    assert all(len(v) <= 1 for v in INTENT_AGENTS_MAP.values())
    # 规则路径（mock LLM 下）：ask 关键词命中
    assert analyze_intent({"user_input": "什么是 DPO"})["intent"] == "ask"


def test_knowledge_receives_question():
    from app.agents.orchestrator.workflow import AgentWorkflow

    wf = AgentWorkflow()
    state = wf._resolve_input("knowledge", {}, user_input="什么是 DPO")
    assert state.get("question") == "什么是 DPO"


def test_ask_keyword_word_boundary_no_task_false_positive():
    from app.agents.supervisor.nodes import analyze_intent

    assert analyze_intent({"user_input": "什么是 self-attention"})["intent"] == "ask"
    assert analyze_intent({"user_input": "完成这个 task"})["intent"] != "ask"


def test_stop_rule_caps_agents_per_run(monkeypatch):
    """停止规则：即使误配 required_agents 很长，单次 run 最多执行 2 个 agent。"""
    wf = AgentWorkflow()

    calls: list[str] = []

    def fake_run_single(agent_name, inputs, db=None):
        calls.append(agent_name)
        return {"agent": agent_name, "status": "success", "output": None}

    monkeypatch.setattr(
        wf, "_run_single_agent", lambda name, inputs, db=None: fake_run_single(name, inputs, db)
    )
    monkeypatch.setattr(
        wf,
        "_run_supervisor",
        lambda text: {
            "intent": "learn",
            "required_agents": ["planner", "reviewer", "career", "research"],
            "execution_plan": {},
        },
    )
    wf.run("测试")
    assert len(calls) <= 2


def test_query_intents_do_not_write():
    """意图门控：查询类（ask）只读零写入（spec §5.2）。

    ask 意图只允许 knowledge 一个 agent；agent_runs 追踪行允许产生，
    但业务表（tasks / learning_logs）计数必须前后不变。
    """
    from fastapi.testclient import TestClient

    from app.agents.registry_setup import setup_default_agents
    from app.db.base import SessionLocal
    from app.main import app
    from app.models.learning_log import LearningLog
    from app.models.task import Task

    # TestClient 不进 with 不触发 lifespan → registry 可能为空（supervisor 未注册
    # 时 run() 会返回 intent=unknown）。此处显式幂等注册，测试不依赖执行顺序。
    setup_default_agents()

    def _counts() -> tuple[int, int]:
        db = SessionLocal()
        try:
            return db.query(Task).count(), db.query(LearningLog).count()
        finally:
            db.close()

    before = _counts()
    client = TestClient(app)
    resp = client.post("/api/agent/run", json={"user_input": "什么是 self-attention"})
    assert resp.status_code == 200
    assert resp.json()["data"]["intent"] == "ask"
    after = _counts()
    assert after == before, f"业务表写入了：{before} → {after}"
