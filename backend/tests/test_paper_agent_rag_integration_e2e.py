"""Embodied AI Career OS · Phase 3 Week 1 Day 5 RAG 接入 Paper Agent 端到端测试。

核心验收：ingest 后无需手动调 /api/paper/index，即可直接 ask/search。

覆盖维度（Day 5 验收）：
  1. PaperAgent 流程含 index 节点：parse→chunk→summarize→persist→index
  2. auto_index=True（默认）：ingest 后 indexed_count > 0
  3. ingest 后直接 ask 能命中（无需手动 index）
  4. ingest 后直接 search 能命中（无需手动 index）
  5. auto_index=False：跳过索引，indexed_count=0
  6. auto_index=False 后手动 index，检索恢复
  7. API ingest 端点返回 indexed_count / index_model
  8. 向后兼容：Day 1-4 测试仍通过

执行方式：
    cd backend && .venv/bin/python tests/test_paper_agent_rag_integration_e2e.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# 关键：在 import app.* 之前设置临时 DB
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_TMP_DB = _BACKEND_DIR / "data" / "test_day5_rag_integration.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
sys.path.insert(0, str(_BACKEND_DIR))

PAPER_PATH = str(
    _BACKEND_DIR / "app" / "research" / "knowledge" / "papers"
    / "ACT_Action_Chunking_with_Transformers.md"
)


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


# ============================================================
# 套件 1：PaperAgent 流程含 index 节点
# ============================================================
def test_graph_flow():
    suite = "GraphFlow"

    def t01(r: TestResult):
        """build_paper_graph 含 index 节点。"""
        from app.research.paper_agent.agent import build_paper_graph
        g = build_paper_graph()
        nodes = list(g.get_graph().nodes.keys())
        assert "index" in nodes, f"graph 缺 index 节点，实际 {nodes}"
        # 顺序：__start__ → parse → chunk → summarize → persist → index → __end__
        assert nodes.index("persist") < nodes.index("index"), "index 应在 persist 之后"
        r.detail = f"nodes={nodes}"

    run_case(suite, "GF-01", "graph 含 index 节点且在 persist 之后", t01)

    def t02(r: TestResult):
        """auto_index=True（默认）：ingest 后 indexed_count > 0。"""
        from app.db.base import SessionLocal, init_db
        from app.research.paper_agent.agent import build_paper_graph

        init_db()
        db = SessionLocal()
        try:
            out = build_paper_graph().invoke({"file_path": PAPER_PATH, "db": db})
            assert out.get("indexed_count", 0) > 0, \
                f"auto_index 默认应索引，indexed_count={out.get('indexed_count')}"
            assert out.get("index_model"), "应返回 index_model"
            r.detail = f"indexed={out['indexed_count']}, model={out['index_model']}"
        finally:
            db.close()

    run_case(suite, "GF-02", "auto_index=True 自动建索引", t02)

    def t03(r: TestResult):
        """auto_index=False：跳过索引，indexed_count=0。"""
        from app.db.base import SessionLocal, init_db
        from app.research.paper_agent.agent import build_paper_graph
        from app.research.paper_agent.rag.vector_store import get_vector_store
        from app.research.paper_agent.rag.embedder import HashEmbedder
        from app.models.paper_chunk import PaperChunk

        init_db()
        db = SessionLocal()
        try:
            out = build_paper_graph().invoke({
                "file_path": PAPER_PATH, "auto_index": False, "db": db,
            })
            paper_id = out["paper_id"]
            assert out.get("indexed_count", 0) == 0, \
                f"auto_index=False 应跳过，indexed_count={out.get('indexed_count')}"
            # 确认本次论文的 chunks 未被索引（其他论文的旧索引可能存在，不查全库）
            store = get_vector_store()
            model_name = HashEmbedder().model_name
            # 取本次论文的 chunk_id，检查向量库是否含这些 chunk 的向量
            chunk_ids = {c.id for c in db.query(PaperChunk).filter(
                PaperChunk.paper_id == paper_id).all()}
            indexed_ids = store.get_indexed_chunk_ids(db, model_name)
            unindexed = chunk_ids - indexed_ids
            assert unindexed == chunk_ids, \
                f"本次论文 chunks 不应有向量，实际已索引 {len(chunk_ids - unindexed)} 条"
            r.detail = f"indexed_count=0, 本次论文 {len(chunk_ids)} chunks 均未索引 ✓"
        finally:
            db.close()

    run_case(suite, "GF-03", "auto_index=False 跳过索引", t03)


# ============================================================
# 套件 2：ingest 即可检索（核心验收）
# ============================================================
def test_ingest_then_retrieval():
    suite = "IngestRetrieval"

    def t04(r: TestResult):
        """ingest 后直接 search 命中（无手动 index）。"""
        from app.db.base import SessionLocal, init_db
        from app.research.paper_agent.agent import build_paper_graph
        from app.research.paper_agent.rag.retriever import search
        from app.research.paper_agent.rag.embedder import HashEmbedder

        init_db()
        db = SessionLocal()
        try:
            # 仅 ingest，不调 build_index
            build_paper_graph().invoke({"file_path": PAPER_PATH, "db": db})
            # 直接 search
            hits = search(db, "ACT transformer method", top_k=5, embedder=HashEmbedder())
            assert hits, "ingest 后应能直接检索到结果"
            assert hits[0]["score"] > 0
            r.detail = f"hits={len(hits)}, top_score={hits[0]['score']:.3f}"
        finally:
            db.close()

    run_case(suite, "IR-01", "ingest 后直接 search 命中", t04)

    def t05(r: TestResult):
        """ingest 后直接 ask 命中（无手动 index）。"""
        from app.db.base import SessionLocal, init_db
        from app.research.paper_agent.agent import build_paper_graph
        from app.agents.knowledge.graph import build_knowledge_graph

        init_db()
        db = SessionLocal()
        try:
            build_paper_graph().invoke({"file_path": PAPER_PATH, "db": db})
            out = build_knowledge_graph().invoke({
                "question": "ACT 用了什么数据集", "top_k": 5, "db": db,
            })
            ans = out["answer"]
            assert ans["hit_count"] > 0, "ingest 后应能直接 ask 命中"
            assert ans["answer"], "答案非空"
            r.detail = f"hits={ans['hit_count']}, conf={ans['confidence']}"
        finally:
            db.close()

    run_case(suite, "IR-02", "ingest 后直接 ask 命中", t05)

    def t06(r: TestResult):
        """auto_index=False 后手动 index，检索恢复。"""
        from app.db.base import SessionLocal, init_db
        from app.research.paper_agent.agent import build_paper_graph
        from app.research.paper_agent.rag.indexer import build_index
        from app.research.paper_agent.rag.retriever import search_by_paper
        from app.research.paper_agent.rag.embedder import HashEmbedder
        from app.research.paper_agent.rag.vector_store import get_vector_store

        init_db()
        db = SessionLocal()
        try:
            # 1. auto_index=False ingest
            out = build_paper_graph().invoke({
                "file_path": PAPER_PATH, "auto_index": False, "db": db,
            })
            paper_id = out["paper_id"]
            # 确认本次论文检索为空（限定 paper_id，避免其他论文旧索引干扰）
            hits_before = search_by_paper(db, "ACT method", paper_id, embedder=HashEmbedder())
            assert not hits_before, "auto_index=False 后本次论文不应有检索结果"

            # 2. 手动 index（仅本次论文）
            build_index(db, paper_id=paper_id, embedder=HashEmbedder(), store=get_vector_store())

            # 3. 检索恢复
            hits_after = search_by_paper(db, "ACT method", paper_id, embedder=HashEmbedder())
            assert hits_after, "手动 index 后应能检索到"
            r.detail = f"手动 index 后 hits={len(hits_after)}"
        finally:
            db.close()

    run_case(suite, "IR-03", "auto_index=False + 手动 index 恢复检索", t06)


# ============================================================
# 套件 3：API 端点
# ============================================================
def test_api():
    suite = "API"

    def t07(r: TestResult):
        """POST /api/paper/ingest 返回 indexed_count + index_model。"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db.base import init_db

        init_db()
        client = TestClient(app)
        resp = client.post("/api/paper/ingest", json={"file_path": PAPER_PATH})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["indexed_count"] > 0, f"应自动索引，indexed_count={data['indexed_count']}"
        assert data["index_model"], "应返回 index_model"
        r.detail = f"indexed={data['indexed_count']}, model={data['index_model']}"

    run_case(suite, "API-01", "ingest 返回 indexed_count + index_model", t07)

    def t08(r: TestResult):
        """POST /api/paper/ingest auto_index=False 返回 indexed_count=0。"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db.base import init_db

        init_db()
        client = TestClient(app)
        resp = client.post("/api/paper/ingest", json={
            "file_path": PAPER_PATH, "auto_index": False,
        })
        data = resp.json()["data"]
        assert data["indexed_count"] == 0, f"应跳过，indexed_count={data['indexed_count']}"
        r.detail = "auto_index=False → indexed_count=0 ✓"

    run_case(suite, "API-02", "ingest auto_index=False 跳过索引", t08)

    def t09(r: TestResult):
        """ingest 后直接调 /api/paper/ask 命中（端到端）。"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.db.base import init_db

        init_db()
        client = TestClient(app)
        # ingest（自动索引）
        client.post("/api/paper/ingest", json={"file_path": PAPER_PATH})
        # 直接 ask
        resp = client.post("/api/paper/ask", json={
            "question": "ACT method transformer", "top_k": 5,
        })
        assert resp.status_code == 200
        ans = resp.json()["data"]
        assert ans["hit_count"] > 0, "ingest 后应能直接 ask 命中"
        r.detail = f"ask hits={ans['hit_count']}, conf={ans['confidence']}"

    run_case(suite, "API-03", "ingest 后直接 ask 命中（端到端）", t09)


# ===== 主入口 =====
def main():
    print("=" * 60)
    print("  Phase 3 Week 1 Day 5 · RAG 接入 Paper Agent 端到端测试")
    print("=" * 60)
    print(f"  临时 DB: {_TMP_DB}")
    print(f"  测试论文: {Path(PAPER_PATH).name}")

    print("\n[套件 1] GraphFlow")
    test_graph_flow()
    print("\n[套件 2] IngestRetrieval")
    test_ingest_then_retrieval()
    print("\n[套件 3] API")
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
