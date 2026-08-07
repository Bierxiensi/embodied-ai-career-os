"""Embodied AI Career OS · Phase 3 Week 1 Day 3 Paper Knowledge Agent 端到端测试。

覆盖维度（Day 3 验收）：
  1. graph：retrieve → answer 两节点编排正常
  2. retrieve_node：RAG 检索命中相关 chunks + paper_title 富化
  3. answer_node：无命中兜底 + 有命中拼接 + 引用可追溯 + 置信度评估
  4. section 过滤：限定 section 时仅返回对应章节
  5. paper_id 限定：单篇论文内检索
  6. Agent 集成：PaperKnowledgeAgent 注册 + 可被 Registry 查找
  7. 全链路：ingest → index → ask（完整 Day1+Day2+Day3 流程）
  8. API：POST /api/paper/ask 端点

执行方式：
    cd backend && .venv/bin/python tests/test_paper_knowledge_e2e.py

隔离策略：临时 SQLite + HashEmbedder（零依赖）。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ============================================================
# 关键：在 import app.* 之前设置临时 DB
# ============================================================
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_TMP_DB = _BACKEND_DIR / "data" / "test_paper_knowledge_e2e.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
sys.path.insert(0, str(_BACKEND_DIR))

PAPER_PATH = str(
    _BACKEND_DIR / "app" / "research" / "knowledge" / "papers"
    / "ACT_Action_Chunking_with_Transformers.md"
)


# ===== 测试结果收集 =====
class TestResult:
    def __init__(self, suite: str, case_id: str, name: str):
        self.suite = suite
        self.case_id = case_id
        self.name = name
        self.status = "RUN"
        self.detail = ""
        self.elapsed_ms = 0


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
    print("  " + icon + f" [{case_id}] {name}" +
          (f" — {r.detail}" if r.status != "PASS" else ""))
    return r


# 共享状态：论文 ingest + index 后的 paper_id
_setup_done = False
_paper_id = ""


def _ensure_setup():
    """前置：ingest ACT 论文 + 构建索引（Day1 + Day2 流程）。"""
    global _setup_done, _paper_id
    if _setup_done:
        return

    from app.db.base import SessionLocal, init_db
    from app.research.paper_agent.agent import build_paper_graph
    from app.research.paper_agent.rag.indexer import build_index
    from app.research.paper_agent.rag.embedder import HashEmbedder
    from app.research.paper_agent.rag.vector_store import get_vector_store

    init_db()
    db = SessionLocal()
    try:
        # Day 1：ingest
        out = build_paper_graph().invoke({"file_path": PAPER_PATH, "db": db})
        _paper_id = out.get("paper_id", "")
        # Day 2：index（显式用 HashEmbedder，零依赖）
        build_index(db, embedder=HashEmbedder(), store=get_vector_store())
    finally:
        db.close()
    _setup_done = True


# ============================================================
# 套件 1：Knowledge Graph 节点
# ============================================================
def test_graph_nodes():
    suite = "GraphNodes"
    from app.db.base import SessionLocal
    from app.agents.knowledge.nodes import answer_node, retrieve_node

    def t01(r: TestResult):
        """retrieve_node：命中 ACT 相关 chunks。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            out = retrieve_node({
                "question": "ACT transformer action chunking method",
                "top_k": 5,
                "db": db,
            })
            chunks = out["retrieved_chunks"]
            assert chunks, "应检索到 chunks"
            assert "paper_title" in chunks[0], "缺 paper_title 富化字段"
            r.detail = f"hits={len(chunks)}, top_score={chunks[0]['score']:.3f}"
        finally:
            db.close()

    run_case(suite, "GN-01", "retrieve_node 命中 + 富化", t01)

    def t02(r: TestResult):
        """retrieve_node：section 过滤仅返回 method。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            out = retrieve_node({
                "question": "transformer policy",
                "top_k": 5,
                "section": "method",
                "db": db,
            })
            sections = {c["section"] for c in out["retrieved_chunks"]}
            assert sections <= {"method"}, f"应仅 method，实际 {sections}"
            r.detail = f"sections={sections}"
        finally:
            db.close()

    run_case(suite, "GN-02", "retrieve_node section 过滤", t02)

    def t03(r: TestResult):
        """answer_node：无命中返回兜底答案 + low 置信度。"""
        out = answer_node({"question": "test", "retrieved_chunks": []})
        ans = out["answer"]
        assert ans["hit_count"] == 0, "hit_count 应为 0"
        assert ans["confidence"] == "low", f"应 low，实际 {ans['confidence']}"
        assert "未在知识库" in ans["answer"], "应含兜底提示"
        r.detail = f"confidence={ans['confidence']}"

    run_case(suite, "GN-03", "answer_node 无命中兜底", t03)

    def t04(r: TestResult):
        """answer_node：有命中返回拼接答案 + citations 可追溯。"""
        fake_chunks = [{
            "chunk_id": "c1", "paper_id": "p1", "paper_title": "ACT Paper",
            "section": "method", "page": 2, "score": 0.8,
            "text": "We propose ACT, a CVAE transformer for action chunking.",
        }]
        out = answer_node({"question": "what is ACT", "retrieved_chunks": fake_chunks})
        ans = out["answer"]
        assert ans["hit_count"] == 1
        assert ans["confidence"] in ("high", "medium")
        assert len(ans["citations"]) == 1, "应有 1 条引用"
        cite = ans["citations"][0]
        assert cite["chunk_id"] == "c1", "引用 chunk_id 可追溯"
        assert cite["paper_title"] == "ACT Paper"
        assert "ACT" in ans["answer"], "答案应含 ACT"
        r.detail = f"confidence={ans['confidence']}, citations={len(ans['citations'])}"

    run_case(suite, "GN-04", "answer_node 拼接 + 引用可追溯", t04)

    def t05(r: TestResult):
        """answer_node：高分命中 → high 置信度。"""
        fake_chunks = [{
            "chunk_id": "c1", "paper_id": "p1", "paper_title": "T",
            "section": "method", "page": 1, "score": 0.5, "text": "high score chunk",
        }]
        out = answer_node({"question": "q", "retrieved_chunks": fake_chunks})
        assert out["answer"]["confidence"] == "high", "score>=0.35 应 high"
        r.detail = "score=0.5 → high"

    run_case(suite, "GN-05", "answer_node 高分 → high", t05)


# ============================================================
# 套件 2：Knowledge Graph 全流程
# ============================================================
def test_graph_flow():
    suite = "GraphFlow"
    from app.db.base import SessionLocal
    from app.agents.knowledge.graph import build_knowledge_graph

    def t06(r: TestResult):
        """全流程：question → retrieve → answer 返回结构化答案。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            g = build_knowledge_graph()
            out = g.invoke({
                "question": "ACT 用了什么数据集",
                "top_k": 5,
                "db": db,
            })
            ans = out["answer"]
            assert ans["hit_count"] > 0, "应命中"
            assert ans["answer"], "答案不应为空"
            assert ans["model_name"], "应含 model_name"
            r.detail = f"hits={ans['hit_count']}, conf={ans['confidence']}"
        finally:
            db.close()

    run_case(suite, "GF-01", "全流程 retrieve→answer", t06)

    def t07(r: TestResult):
        """paper_id 限定：仅检索指定论文。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            g = build_knowledge_graph()
            out = g.invoke({
                "question": "transformer method",
                "paper_id": _paper_id,
                "top_k": 5,
                "db": db,
            })
            ans = out["answer"]
            for cite in ans["citations"]:
                assert cite["paper_id"] == _paper_id, \
                    f"应限定 paper_id={_paper_id[:8]}，实际 {cite['paper_id'][:8]}"
            r.detail = f"all citations paper_id 匹配"
        finally:
            db.close()

    run_case(suite, "GF-02", "paper_id 限定单篇论文", t07)

    def t08(r: TestResult):
        """section 过滤：仅 method section。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            g = build_knowledge_graph()
            out = g.invoke({
                "question": "policy network",
                "section": "method",
                "top_k": 5,
                "db": db,
            })
            sections = {c["section"] for c in out["answer"]["citations"]}
            assert sections <= {"method"}, f"应仅 method，实际 {sections}"
            r.detail = f"sections={sections}"
        finally:
            db.close()

    run_case(suite, "GF-03", "section 过滤仅 method", t08)


# ============================================================
# 套件 3：Agent 集成
# ============================================================
def test_agent_integration():
    suite = "AgentIntegration"

    def t09(r: TestResult):
        """PaperKnowledgeAgent 可注册到 Registry。"""
        from app.agents.core.registry import AgentRegistry
        from app.agents.registry_setup import setup_default_agents

        setup_default_agents()
        agent = AgentRegistry.get("knowledge")
        assert agent is not None, "knowledge Agent 未注册"
        assert agent.name == "knowledge"
        r.detail = f"name={agent.name}"

    run_case(suite, "AI-01", "Registry 含 knowledge Agent", t09)

    def t10(r: TestResult):
        """PaperKnowledgeAgent.invoke 执行问答。"""
        _ensure_setup()
        from app.agents.knowledge.agent import PaperKnowledgeAgent
        from app.db.base import SessionLocal

        db = SessionLocal()
        try:
            agent = PaperKnowledgeAgent()
            out = agent.invoke({
                "question": "SO101 LeRobot",
                "top_k": 3,
                "db": db,
            })
            assert "answer" in out, "应返回 answer"
            assert out["answer"]["hit_count"] >= 0
            r.detail = f"hits={out['answer']['hit_count']}"
        finally:
            db.close()

    run_case(suite, "AI-02", "Agent.invoke 执行问答", t10)


# ============================================================
# 套件 4：API 端点
# ============================================================
def test_api():
    suite = "API"

    def t11(r: TestResult):
        """POST /api/paper/ask 返回结构化答案。"""
        _ensure_setup()
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/api/paper/ask", json={
            "question": "ACT 用了什么数据集",
            "top_k": 5,
        })
        assert resp.status_code == 200, f"状态码 {resp.status_code}"
        data = resp.json()
        assert data["success"], f"应成功：{data}"
        ans = data["data"]
        assert ans["hit_count"] > 0, "应命中"
        assert ans["answer"], "答案非空"
        assert ans["citations"], "应有引用"
        cite = ans["citations"][0]
        assert "chunk_id" in cite and "paper_title" in cite
        r.detail = f"hits={ans['hit_count']}, conf={ans['confidence']}"

    run_case(suite, "API-01", "POST /api/paper/ask 端点", t11)

    def t12(r: TestResult):
        """POST /api/paper/ask 带 section 过滤。"""
        _ensure_setup()
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/api/paper/ask", json={
            "question": "policy",
            "section": "method",
            "top_k": 5,
        })
        data = resp.json()["data"]
        sections = {c["section"] for c in data["citations"]}
        if data["citations"]:
            assert sections <= {"method"}, f"应仅 method，实际 {sections}"
        r.detail = f"sections={sections}"

    run_case(suite, "API-02", "ask 带 section 过滤", t12)

    def t13(r: TestResult):
        """POST /api/paper/ask 空问题返回校验错误。"""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/api/paper/ask", json={"question": ""})
        assert resp.status_code == 422, f"空问题应 422，实际 {resp.status_code}"
        r.detail = f"422 校验通过"

    run_case(suite, "API-03", "空问题 422 校验", t13)


# ===== 主入口 =====
def main():
    print("=" * 60)
    print("  Phase 3 Week 1 Day 3 · Paper Knowledge Agent 端到端测试")
    print("=" * 60)
    print(f"  临时 DB: {_TMP_DB}")
    print(f"  测试论文: {Path(PAPER_PATH).name}")
    print(f"  Embedder: HashEmbedder (零依赖 fallback)")

    print("\n[套件 1] GraphNodes")
    test_graph_nodes()
    print("\n[套件 2] GraphFlow")
    test_graph_flow()
    print("\n[套件 3] AgentIntegration")
    test_agent_integration()
    print("\n[套件 4] API")
    test_api()

    total = len(results)
    passed = sum(1 for x in results if x.status == "PASS")
    failed = sum(1 for x in results if x.status == "FAIL")

    print("\n" + "=" * 60)
    print(f"  总计 {total} | 通过 {passed} | 失败 {failed}")
    print("=" * 60)

    if failed:
        print("\n失败用例:")
        for x in results:
            if x.status == "FAIL":
                print(f"  ✗ [{x.case_id}] {x.name}: {x.detail}")
        _cleanup()
        sys.exit(1)
    else:
        print("\n✓ 全部通过")
        _cleanup()


def _cleanup():
    try:
        if _TMP_DB.exists():
            _TMP_DB.unlink()
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
