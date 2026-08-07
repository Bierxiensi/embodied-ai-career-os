"""Embodied AI Career OS · Phase 3 Week 1 Day 1 Paper Agent 端到端测试。

覆盖维度（Day 1 验收）：
  1. parser：MD 解析 + H1 标题提取 + frontmatter 剥离
  2. chunker：按 Markdown 章节标题语义分块（## Abstract / ## Method ...）
  3. summarizer：5 个验收字段（title / method / dataset / contribution / relation）
  4. LangGraph 全流程：parse → chunk → summarize → persist，结果入库

执行方式：
    cd backend && python tests/test_paper_agent_e2e.py

隔离策略：
    持久化测试使用临时 SQLite 文件，通过 DATABASE_URL 环境变量注入，
    不污染开发态 data/app.db。脚本结束自动清理临时 DB。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ============================================================
# 关键：在 import app.* 之前设置临时 DB，确保 engine 绑定到隔离库
# ============================================================
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_TMP_DB = _BACKEND_DIR / "data" / "test_paper_e2e.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
# 用绝对路径转 sqlite 标准 URI，确保 engine 绑定到隔离临时库
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"

# 确保 backend 在 sys.path
sys.path.insert(0, str(_BACKEND_DIR))


# ===== 测试结果收集（与 test_phase2_week1.py 风格一致）=====
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
    print("  " + icon + f" [{case_id}] {name}" +
          (f" — {r.detail}" if r.status != "PASS" else ""))
    return r


# 测试样本：真实结构化论文（含 SO101/LeRobot/Isaac/ACT/VLA 全部项目关键词）
PAPER_PATH = str(
    _BACKEND_DIR / "app" / "research" / "knowledge" / "papers"
    / "ACT_Action_Chunking_with_Transformers.md"
)


# ============================================================
# 套件 1：parser
# ============================================================
def test_parser():
    suite = "Parser"

    def t01(r: TestResult):
        """MD 解析：提取 H1 标题作为 title_hint。"""
        from app.research.paper_agent.parser import parse
        _, meta = parse(PAPER_PATH)
        assert meta["file_type"] == "md", f"file_type 应为 md，实际 {meta['file_type']}"
        assert "ACT" in meta["title_hint"], f"title_hint 应含 ACT，实际 {meta['title_hint']!r}"
        r.detail = f"title_hint={meta['title_hint']!r}"

    run_case(suite, "PR-01", "MD 解析：H1 标题提取为 title_hint", t01)

    def t02(r: TestResult):
        """MD 解析：text 含 Abstract / Method 章节标题。"""
        from app.research.paper_agent.parser import parse
        text, _ = parse(PAPER_PATH)
        assert "Abstract" in text, "text 缺 Abstract"
        assert "Method" in text, "text 缺 Method"
        r.detail = f"text_len={len(text)}"

    run_case(suite, "PR-02", "MD 解析：保留章节标题文本", t02)


# ============================================================
# 套件 2：chunker
# ============================================================
def test_chunker():
    suite = "Chunker"

    def t03(r: TestResult):
        """章节识别：非全 unknown，含 method / experiment 等结构化 section。"""
        from app.research.paper_agent.chunker import chunk
        from app.research.paper_agent.parser import parse
        text, meta = parse(PAPER_PATH)
        chunks = chunk(text, meta, "paper-test")
        sections = {c["section"] for c in chunks}
        assert "method" in sections, f"section 缺 method，实际 {sections}"
        assert "abstract" in sections, f"section 缺 abstract，实际 {sections}"
        assert "experiment" in sections, f"section 缺 experiment，实际 {sections}"
        r.detail = f"sections={sorted(sections)}"

    run_case(suite, "CK-01", "章节识别：含 method/abstract/experiment", t03)

    def t04(r: TestResult):
        """chunk 结构：每个 chunk 含必需字段 + 非空文本。"""
        from app.research.paper_agent.chunker import chunk
        from app.research.paper_agent.parser import parse
        text, meta = parse(PAPER_PATH)
        chunks = chunk(text, meta, "paper-test")
        assert len(chunks) >= 5, f"chunk 数应 >=5，实际 {len(chunks)}"
        for c in chunks:
            assert c.get("chunk_id"), "chunk 缺 chunk_id"
            assert c.get("text"), "chunk 文本为空"
            assert c.get("token_count", 0) > 0, "token_count 应 >0"
        r.detail = f"chunk_count={len(chunks)}"

    run_case(suite, "CK-02", "chunk 结构：必需字段完整", t04)


# ============================================================
# 套件 3：summarizer（Day1 验收核心）
# ============================================================
def test_summarizer():
    suite = "Summarizer"

    def _build():
        from app.research.paper_agent.chunker import chunk
        from app.research.paper_agent.parser import parse
        from app.research.paper_agent.summarizer import summarize
        text, meta = parse(PAPER_PATH)
        chunks = chunk(text, meta, "paper-test")
        return summarize(chunks, meta)

    def t05(r: TestResult):
        """title：从 H1 提取，含 ACT。"""
        s = _build()
        assert "ACT" in s["title"], f"title 应含 ACT，实际 {s['title']!r}"
        r.detail = f"title={s['title']!r}"

    run_case(suite, "SM-01", "title 含 ACT（H1 提取）", t05)

    def t06(r: TestResult):
        """method：从 method section 提取，非空。"""
        s = _build()
        assert s["method"], "method 为空"
        assert "ACT" in s["method"] or "transformer" in s["method"].lower(), \
            f"method 应含 ACT/transformer，实际 {s['method']!r}"
        r.detail = f"method={s['method'][:60]!r}..."

    run_case(suite, "SM-02", "method 非空（含 ACT/transformer）", t06)

    def t07(r: TestResult):
        """dataset：非空。"""
        s = _build()
        assert s["dataset"], "dataset 为空"
        r.detail = f"dataset={s['dataset'][:60]!r}..."

    run_case(suite, "SM-03", "dataset 非空", t07)

    def t08(r: TestResult):
        """contribution：非空。"""
        s = _build()
        assert s["contribution"], "contribution 为空"
        r.detail = f"contribution={s['contribution'][:60]!r}..."

    run_case(suite, "SM-04", "contribution 非空", t08)

    def t09(r: TestResult):
        """relation_to_my_project：命中 SO101 / LeRobot / ACT。"""
        s = _build()
        rel = s["relation_to_my_project"]
        assert "SO101" in rel, f"relation 应命中 SO101，实际 {rel!r}"
        assert "LeRobot" in rel, f"relation 应命中 LeRobot，实际 {rel!r}"
        assert "ACT" in rel, f"relation 应命中 ACT，实际 {rel!r}"
        r.detail = rel[:80]

    run_case(suite, "SM-05", "relation 命中 SO101/LeRobot/ACT", t09)

    def t10(r: TestResult):
        """confidence：5 字段齐全应为 high。"""
        s = _build()
        assert s["confidence"] == "high", f"confidence 应 high，实际 {s['confidence']}"
        r.detail = f"confidence={s['confidence']}"

    run_case(suite, "SM-06", "confidence = high", t10)


# ============================================================
# 套件 4：LangGraph 全流程（持久化）
# ============================================================
def test_pipeline():
    suite = "Pipeline"

    def t11(r: TestResult):
        """全流程：parse → chunk → summarize → persist，返回 paper_id。"""
        from app.db.base import Base, init_db
        # 建表（临时 DB 首次运行）
        init_db()
        from app.research.paper_agent.agent import build_paper_graph
        g = build_paper_graph()
        out = g.invoke({"file_path": PAPER_PATH})
        pid = out.get("paper_id")
        assert pid, f"paper_id 为空，out keys={list(out.keys())}"
        r.detail = f"paper_id={pid[:8]}..."
        # 暂存给后续用例
        test_pipeline._paper_id = pid  # type: ignore[attr-defined]

    run_case(suite, "E2E-01", "全流程返回 paper_id", t11)

    def t12(r: TestResult):
        """papers 表：记录已入库，title 含 ACT。"""
        from app.db.base import SessionLocal
        from app.models.paper import Paper
        pid = getattr(test_pipeline, "_paper_id", None)
        assert pid, "前置 E2E-01 未产出 paper_id"
        db = SessionLocal()
        try:
            paper = db.query(Paper).filter(Paper.id == pid).first()
            assert paper is not None, f"papers 表未找到 {pid}"
            assert "ACT" in paper.title, f"title 应含 ACT，实际 {paper.title!r}"
            assert paper.method, "method 字段为空"
            r.detail = f"title={paper.title[:40]!r}, chunks={paper.chunk_count}"
        finally:
            db.close()

    run_case(suite, "E2E-02", "papers 表入库 + title/method 填充", t12)

    def t13(r: TestResult):
        """paper_chunks 表：含 method section 的 chunk。"""
        from app.db.base import SessionLocal
        from app.models.paper_chunk import PaperChunk
        pid = getattr(test_pipeline, "_paper_id", None)
        assert pid, "前置 E2E-01 未产出 paper_id"
        db = SessionLocal()
        try:
            chunks = db.query(PaperChunk).filter(PaperChunk.paper_id == pid).all()
            sections = {c.section for c in chunks}
            assert "method" in sections, f"paper_chunks 缺 method section，实际 {sections}"
            r.detail = f"chunk_count={len(chunks)}, sections={sorted(sections)}"
        finally:
            db.close()

    run_case(suite, "E2E-03", "paper_chunks 含 method section", t13)


# ===== 主入口 =====
def main():
    print("=" * 60)
    print("  Phase 3 Week 1 Day 1 · Paper Agent 端到端测试")
    print("=" * 60)
    print(f"  临时 DB: {_TMP_DB}")
    print(f"  测试论文: {Path(PAPER_PATH).name}")

    print("\n[套件 1] Parser")
    test_parser()
    print("\n[套件 2] Chunker")
    test_chunker()
    print("\n[套件 3] Summarizer")
    test_summarizer()
    print("\n[套件 4] Pipeline")
    test_pipeline()

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
    """清理临时 DB 文件。"""
    try:
        if _TMP_DB.exists():
            _TMP_DB.unlink()
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
