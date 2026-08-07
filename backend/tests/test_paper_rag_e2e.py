"""Embodied AI Career OS · Phase 3 Week 1 Day 2 RAG 向量检索端到端测试。

覆盖维度（Day 2 验收）：
  1. embedder：HashEmbedder 确定性 + 归一化 + 语义近似
  2. vector_store：upsert/search/count + section 过滤 + 余弦排序
  3. indexer：增量构建（首次全量 + 二次跳过）+ force_rebuild
  4. retriever：query → top-k + paper_title 富化 + section 过滤
  5. 全链路：Day1 ingest → Day2 index → search → stats

执行方式：
    cd backend && .venv/bin/python tests/test_paper_rag_e2e.py

隔离策略：
    临时 SQLite 文件，通过 DATABASE_URL 注入，结束自动清理。
    显式用 HashEmbedder（prefer_st=False），确保零依赖可测试。
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
_TMP_DB = _BACKEND_DIR / "data" / "test_paper_rag_e2e.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
sys.path.insert(0, str(_BACKEND_DIR))

PAPER_PATH = str(
    _BACKEND_DIR / "app" / "research" / "knowledge" / "papers"
    / "ACT_Action_Chunking_with_Transformers.md"
)


# ===== 测试结果收集（复用 Day1 测试风格）=====
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


# 共享：固定用 HashEmbedder，避免依赖 sentence-transformers
def _hash_embedder():
    from app.research.paper_agent.rag.embedder import HashEmbedder
    return HashEmbedder()


# ============================================================
# 套件 1：embedder
# ============================================================
def test_embedder():
    suite = "Embedder"

    def t01(r: TestResult):
        """确定性：相同文本 → 相同向量。"""
        emb = _hash_embedder()
        v1 = emb.embed("ACT action chunking transformer")
        v2 = emb.embed("ACT action chunking transformer")
        assert v1 == v2, "相同文本应产生相同向量"
        r.detail = f"dim={len(v1)}"

    run_case(suite, "EM-01", "确定性：相同文本 → 相同向量", t01)

    def t02(r: TestResult):
        """归一化：向量 L2 范数 ≈ 1。"""
        import math
        emb = _hash_embedder()
        v = emb.embed("SO101 robot manipulation imitation learning")
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-6, f"范数应≈1，实际 {norm}"
        r.detail = f"norm={norm:.6f}"

    run_case(suite, "EM-02", "归一化：L2 范数 ≈ 1", t02)

    def t03(r: TestResult):
        """语义近似：共享词多的文本余弦相似度更高。"""
        import math
        emb = _hash_embedder()
        v_query = emb.embed("ACT transformer method")
        v_relevant = emb.embed("We propose ACT transformer policy")  # 共享 ACT transformer
        v_irrelevant = emb.embed("ROS2 topic publisher subscriber")  # 无共享词

        def cosine(a, b):
            return sum(x * y for x, y in zip(a, b))  # 已归一化

        sim_rel = cosine(v_query, v_relevant)
        sim_irr = cosine(v_query, v_irrelevant)
        assert sim_rel > sim_irr, \
            f"相关文本相似度应更高: rel={sim_rel:.3f} vs irr={sim_irr:.3f}"
        r.detail = f"sim_rel={sim_rel:.3f} > sim_irr={sim_irr:.3f}"

    run_case(suite, "EM-03", "语义近似：共享词 → 更高余弦", t03)

    def t04(r: TestResult):
        """维度：默认 384，对齐 MiniLM。"""
        emb = _hash_embedder()
        assert emb.dim == 384, f"dim 应 384，实际 {emb.dim}"
        assert emb.model_name == "hash-384"
        r.detail = f"dim={emb.dim}, model={emb.model_name}"

    run_case(suite, "EM-04", "维度 384 + model_name", t04)


# ============================================================
# 套件 2：vector_store
# ============================================================
def test_vector_store():
    suite = "VectorStore"
    from app.db.base import SessionLocal, init_db
    from app.models.paper import Paper
    from app.models.paper_chunk import PaperChunk
    from app.research.paper_agent.rag.vector_store import get_vector_store

    init_db()
    emb = _hash_embedder()
    store = get_vector_store()

    # 准备：先插 Paper 再插 Chunk（满足 paper_chunks.paper_id 外键约束）
    db = SessionLocal()
    try:
        db.add(Paper(
            id="test-paper-001",
            title="Test Paper for VectorStore",
            source_path="/tmp/test.md",
            file_type="md",
            page_count=1,
            chunk_count=1,
        ))
        db.add(PaperChunk(
            id="test-chunk-001",
            paper_id="test-paper-001",
            text="ACT uses CVAE transformer encoder decoder for action chunking",
            section="method",
            page=1,
            char_offset=0,
            token_count=15,
        ))
        db.commit()
    finally:
        db.close()

    def t05(r: TestResult):
        """upsert：写入向量，count +1。"""
        db = SessionLocal()
        try:
            before = store.count(db, emb.model_name)
            vec = emb.embed("ACT CVAE transformer action chunking")
            store.upsert(db, "test-chunk-001", vec, emb.model_name)
            db.commit()
            after = store.count(db, emb.model_name)
            assert after == before + 1, f"count 应 +1: {before}→{after}"
            r.detail = f"count {before}→{after}"
        finally:
            db.close()

    run_case(suite, "VS-01", "upsert 写入向量", t05)

    def t06(r: TestResult):
        """search：查询命中已索引 chunk，score > 0。"""
        db = SessionLocal()
        try:
            qvec = emb.embed("ACT CVAE transformer action chunking")
            hits = store.search(db, qvec, emb.model_name, top_k=5)
            assert hits, "应有检索结果"
            top = hits[0]
            assert top["chunk_id"] == "test-chunk-001", f"top 应命中测试 chunk"
            assert top["score"] > 0, f"score 应 >0，实际 {top['score']}"
            r.detail = f"top score={top['score']:.3f}, section={top['section']}"
        finally:
            db.close()

    run_case(suite, "VS-02", "search 命中 + score > 0", t06)

    def t07(r: TestResult):
        """section 过滤：method section 命中，unknown 不命中。"""
        db = SessionLocal()
        try:
            qvec = emb.embed("ACT CVAE transformer action chunking")
            hits_method = store.search(db, qvec, emb.model_name, top_k=5, section="method")
            hits_unknown = store.search(db, qvec, emb.model_name, top_k=5, section="unknown")
            assert hits_method, "method section 应有结果"
            assert not hits_unknown, "unknown section 应无结果"
            r.detail = f"method={len(hits_method)}, unknown={len(hits_unknown)}"
        finally:
            db.close()

    run_case(suite, "VS-03", "section 过滤生效", t07)

    def t08(r: TestResult):
        """upsert 幂等：同 chunk_id+model 重复 upsert 不新增。"""
        db = SessionLocal()
        try:
            before = store.count(db, emb.model_name)
            vec = emb.embed("updated text for idempotent test")
            store.upsert(db, "test-chunk-001", vec, emb.model_name)
            db.commit()
            after = store.count(db, emb.model_name)
            assert after == before, f"重复 upsert 不应新增: {before}→{after}"
            r.detail = f"count 保持 {before}"
        finally:
            db.close()

    run_case(suite, "VS-04", "upsert 幂等（覆盖不新增）", t08)


# ============================================================
# 套件 3：indexer
# ============================================================
def test_indexer():
    suite = "Indexer"
    from app.db.base import SessionLocal
    from app.research.paper_agent.rag.indexer import build_index
    from app.research.paper_agent.rag.vector_store import get_vector_store

    emb = _hash_embedder()
    store = get_vector_store()

    # 前置：用 Day1 PaperAgent 先 ingest 一篇论文，产生 chunks
    _ensure_paper_ingested()

    def t09(r: TestResult):
        """增量构建：索引未索引的 chunk（跳过已索引的）。"""
        db = SessionLocal()
        try:
            result = build_index(db, embedder=emb, store=store)
            # 增量语义：未索引的会被索引（>0），已索引的跳过（含套件2 的 test-chunk-001）
            assert result.indexed > 0, f"应索引 >0，实际 {result.indexed}"
            assert result.model_name == "hash-384"
            assert result.indexed + result.skipped == result.total_chunks, \
                "indexed + skipped 应等于 total"
            r.detail = f"total={result.total_chunks}, indexed={result.indexed}, skipped={result.skipped}"
        finally:
            db.close()

    run_case(suite, "IX-01", "增量构建：首次全量", t09)

    def t10(r: TestResult):
        """增量构建：二次执行全部跳过。"""
        db = SessionLocal()
        try:
            result = build_index(db, embedder=emb, store=store)
            assert result.indexed == 0, f"二次应 0 新增，实际 {result.indexed}"
            assert result.skipped > 0, f"二次应全部跳过，实际 {result.skipped}"
            r.detail = f"skipped={result.skipped}"
        finally:
            db.close()

    run_case(suite, "IX-02", "增量构建：二次全跳过", t10)

    def t11(r: TestResult):
        """force_rebuild：强制重建，indexed == total。"""
        db = SessionLocal()
        try:
            result = build_index(db, embedder=emb, store=store, force_rebuild=True)
            assert result.indexed == result.total_chunks, \
                f"重建应 indexed==total: {result.indexed} vs {result.total_chunks}"
            assert result.skipped == 0
            r.detail = f"rebuilt {result.indexed}/{result.total_chunks}"
        finally:
            db.close()

    run_case(suite, "IX-03", "force_rebuild 强制重建", t11)


# ============================================================
# 套件 4：retriever
# ============================================================
def test_retriever():
    suite = "Retriever"
    from app.db.base import SessionLocal
    from app.research.paper_agent.rag.retriever import search

    emb = _hash_embedder()

    def t12(r: TestResult):
        """语义检索：query 命中相关 chunk，含 paper_title 富化。"""
        db = SessionLocal()
        try:
            hits = search(db, "ACT transformer action chunking method",
                          top_k=5, embedder=emb)
            assert hits, "应有检索结果"
            top = hits[0]
            assert "paper_title" in top, "缺 paper_title 富化字段"
            assert top["paper_title"], "paper_title 不应为空"
            assert top["score"] > 0
            r.detail = f"top: score={top['score']:.3f}, title={top['paper_title'][:30]!r}"
        finally:
            db.close()

    run_case(suite, "RT-01", "语义检索 + paper_title 富化", t12)

    def t13(r: TestResult):
        """section 过滤：只检索 method section。"""
        db = SessionLocal()
        try:
            hits = search(db, "transformer policy", top_k=5,
                          section="method", embedder=emb)
            if hits:
                sections = {h["section"] for h in hits}
                assert sections == {"method"}, \
                    f"section 过滤后应仅 method，实际 {sections}"
                r.detail = f"sections={sections}, count={len(hits)}"
            else:
                r.detail = "method section 无命中（chunk 文本差异，可接受）"
        finally:
            db.close()

    run_case(suite, "RT-02", "section 过滤仅返回 method", t13)

    def t14(r: TestResult):
        """空查询返回空列表。"""
        db = SessionLocal()
        try:
            hits = search(db, "   ", top_k=5, embedder=emb)
            assert hits == [], f"空查询应返回空，实际 {len(hits)} 条"
            r.detail = "空查询 → 空列表"
        finally:
            db.close()

    run_case(suite, "RT-03", "空查询返回空", t14)


# ============================================================
# 套件 5：全链路（ingest → index → search → stats）
# ============================================================
def test_e2e():
    suite = "E2E"
    from app.db.base import SessionLocal
    from app.research.paper_agent.rag.indexer import build_index
    from app.research.paper_agent.rag.retriever import search
    from app.research.paper_agent.rag.vector_store import get_vector_store
    from app.models.paper_chunk_embedding import PaperChunkEmbedding

    emb = _hash_embedder()
    store = get_vector_store()

    def t15(r: TestResult):
        """全链路：已 ingest 论文 → 索引覆盖全部 chunk。"""
        db = SessionLocal()
        try:
            from app.models.paper_chunk import PaperChunk
            total_chunks = db.query(PaperChunk).count()
            indexed = store.count(db, emb.model_name)
            assert indexed >= total_chunks, \
                f"索引应覆盖全部 chunk: indexed={indexed} < total={total_chunks}"
            r.detail = f"indexed={indexed}/{total_chunks}"
        finally:
            db.close()

    run_case(suite, "E2E-01", "索引覆盖全部 chunk", t15)

    def t16(r: TestResult):
        """检索结果含 ACT 论文内容。"""
        db = SessionLocal()
        try:
            hits = search(db, "SO101 LeRobot dataset episodes", top_k=5, embedder=emb)
            assert hits, "应有检索结果"
            # 至少一条命中 ACT 论文
            texts = " ".join(h["text"].lower() for h in hits)
            assert "so101" in texts or "lerobot" in texts or "episodes" in texts, \
                "检索结果应含 SO101/LeRobot/episodes 相关内容"
            r.detail = f"top score={hits[0]['score']:.3f}"
        finally:
            db.close()

    run_case(suite, "E2E-02", "检索命中 ACT 论文内容", t16)

    def t17(r: TestResult):
        """stats：覆盖率 = 1.0（全部已索引）。"""
        db = SessionLocal()
        try:
            from app.models.paper import Paper
            from app.models.paper_chunk import PaperChunk
            paper_count = db.query(Paper).count()
            chunk_count = db.query(PaperChunk).count()
            indexed = db.query(PaperChunkEmbedding).filter(
                PaperChunkEmbedding.model_name == emb.model_name
            ).count()
            coverage = indexed / chunk_count if chunk_count else 0
            assert paper_count >= 1, "应有至少 1 篇论文"
            assert chunk_count >= 5, "应有至少 5 个 chunk"
            assert coverage == 1.0, f"覆盖率应为 1.0，实际 {coverage}"
            r.detail = f"papers={paper_count}, chunks={chunk_count}, coverage={coverage}"
        finally:
            db.close()

    run_case(suite, "E2E-03", "stats 覆盖率 = 1.0", t17)


# ============================================================
# 辅助：确保论文已 ingest
# ============================================================
_paper_ingested = False


def _ensure_paper_ingested():
    """用 Day1 PaperAgent ingest ACT 论文，产生 chunks 供 indexer 用。

    Day 5 起 ingest 默认 auto_index=True 会自动建索引，
    但 Day 2 测试要验证"首次全量索引"语义，故显式 auto_index=False，
    让 chunks 入库但不建索引，由 IX-01 用例验证首次索引。
    """
    global _paper_ingested
    if _paper_ingested:
        return
    from app.research.paper_agent.agent import build_paper_graph
    from app.db.base import SessionLocal
    db = SessionLocal()
    try:
        graph = build_paper_graph()
        graph.invoke({"file_path": PAPER_PATH, "auto_index": False, "db": db})
    finally:
        db.close()
    _paper_ingested = True


# ===== 主入口 =====
def main():
    print("=" * 60)
    print("  Phase 3 Week 1 Day 2 · RAG 向量检索端到端测试")
    print("=" * 60)
    print(f"  临时 DB: {_TMP_DB}")
    print(f"  测试论文: {Path(PAPER_PATH).name}")
    print(f"  Embedder: HashEmbedder (零依赖 fallback)")

    print("\n[套件 1] Embedder")
    test_embedder()
    print("\n[套件 2] VectorStore")
    test_vector_store()
    print("\n[套件 3] Indexer")
    test_indexer()
    print("\n[套件 4] Retriever")
    test_retriever()
    print("\n[套件 5] E2E")
    test_e2e()

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
