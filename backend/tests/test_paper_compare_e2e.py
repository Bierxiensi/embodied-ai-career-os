"""Embodied AI Career OS · Phase 3 Week 1 Day 4 多论文对比端到端测试。

覆盖维度（Day 4 验收）：
  1. 双论文 ingest：ACT + Diffusion Policy 均入库
  2. 对比器：字段级差异矩阵（method/dataset/contribution/relation）
  3. 共性 / 差异提取：不同 method/dataset 标记为差异
  4. 项目关联对比：ACT 命中 SO101/LeRobot/Isaac，Diffusion 命中 Franka/Robomimic
  5. 边界：单论文 / 不存在的 paper_id 抛 ValueError
  6. API：POST /api/paper/compare 端点

执行方式：
    cd backend && .venv/bin/python tests/test_paper_compare_e2e.py

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
_TMP_DB = _BACKEND_DIR / "data" / "test_paper_compare_e2e.db"
if _TMP_DB.exists():
    _TMP_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
sys.path.insert(0, str(_BACKEND_DIR))

PAPERS_DIR = _BACKEND_DIR / "app" / "research" / "knowledge" / "papers"
PAPER_ACT = str(PAPERS_DIR / "ACT_Action_Chunking_with_Transformers.md")
PAPER_DP = str(PAPERS_DIR / "Diffusion_Policy_Visual_Manipulation.md")


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


# 共享状态：两篇论文 ingest 后的 paper_id
_setup_done = False
_act_id = ""
_dp_id = ""


def _ensure_setup():
    """前置：ingest ACT + Diffusion Policy 两篇论文。"""
    global _setup_done, _act_id, _dp_id
    if _setup_done:
        return

    from app.db.base import SessionLocal, init_db
    from app.research.paper_agent.agent import build_paper_graph

    init_db()
    db = SessionLocal()
    try:
        out_act = build_paper_graph().invoke({"file_path": PAPER_ACT, "db": db})
        _act_id = out_act.get("paper_id", "")
        out_dp = build_paper_graph().invoke({"file_path": PAPER_DP, "db": db})
        _dp_id = out_dp.get("paper_id", "")
    finally:
        db.close()
    _setup_done = True


# ============================================================
# 套件 1：对比器核心
# ============================================================
def test_comparator():
    suite = "Comparator"
    from app.db.base import SessionLocal
    from app.research.paper_agent.comparator import compare_papers

    def t01(r: TestResult):
        """双论文对比：返回 2 篇 + 4 字段差异矩阵。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            result = compare_papers(db, [_act_id, _dp_id])
            assert result.paper_count == 2, f"应 2 篇，实际 {result.paper_count}"
            assert len(result.fields) == 4, f"应 4 字段，实际 {len(result.fields)}"
            r.detail = f"papers={result.paper_count}, fields={len(result.fields)}"
        finally:
            db.close()

    run_case(suite, "CP-01", "双论文对比返回结构", t01)

    def t02(r: TestResult):
        """method 字段差异：ACT(CVAE transformer) vs Diffusion(DDPM U-Net)。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            result = compare_papers(db, [_act_id, _dp_id])
            method_field = next(f for f in result.fields if f.field == "method")
            assert not method_field.is_common, "method 应有差异"
            titles = list(method_field.values.keys())
            assert len(titles) == 2, "method 应含 2 篇值"
            r.detail = f"method 差异确认，titles={len(titles)}"
        finally:
            db.close()

    run_case(suite, "CP-02", "method 字段差异检测", t02)

    def t03(r: TestResult):
        """dataset 字段差异：ACT(SO101/50ep) vs Diffusion(Franka/200ep)。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            result = compare_papers(db, [_act_id, _dp_id])
            dataset_field = next(f for f in result.fields if f.field == "dataset")
            assert not dataset_field.is_common, "dataset 应有差异"
            r.detail = "dataset 差异确认"
        finally:
            db.close()

    run_case(suite, "CP-03", "dataset 字段差异检测", t03)

    def t04(r: TestResult):
        """差异列表非空：至少含 method + dataset 差异。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            result = compare_papers(db, [_act_id, _dp_id])
            assert result.differences, "差异列表不应为空"
            diff_fields = {d.split("]")[0].strip("[") for d in result.differences}
            assert "method" in diff_fields, f"差异应含 method，实际 {diff_fields}"
            assert "dataset" in diff_fields, f"差异应含 dataset，实际 {diff_fields}"
            r.detail = f"diff_fields={diff_fields}"
        finally:
            db.close()

    run_case(suite, "CP-04", "差异列表含 method+dataset", t04)


# ============================================================
# 套件 2：项目关联对比
# ============================================================
def test_project_relations():
    suite = "ProjectRelations"
    from app.db.base import SessionLocal
    from app.research.paper_agent.comparator import compare_papers

    def t05(r: TestResult):
        """ACT 论文命中 SO101/LeRobot/Isaac。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            result = compare_papers(db, [_act_id, _dp_id])
            act_title = next(b.title for b in result.papers if b.paper_id == _act_id)
            act_hits = result.project_relations.get(act_title, [])
            assert "SO101" in act_hits, f"ACT 应命中 SO101，实际 {act_hits}"
            assert "LeRobot" in act_hits, f"ACT 应命中 LeRobot，实际 {act_hits}"
            r.detail = f"ACT 命中: {act_hits}"
        finally:
            db.close()

    run_case(suite, "PR-01", "ACT 命中 SO101/LeRobot", t05)

    def t06(r: TestResult):
        """Diffusion Policy 命中 Franka/Robomimic。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            result = compare_papers(db, [_act_id, _dp_id])
            dp_title = next(b.title for b in result.papers if b.paper_id == _dp_id)
            dp_hits = result.project_relations.get(dp_title, [])
            assert "Franka" in dp_hits, f"DP 应命中 Franka，实际 {dp_hits}"
            assert "Robomimic" in dp_hits, f"DP 应命中 Robomimic，实际 {dp_hits}"
            r.detail = f"DP 命中: {dp_hits}"
        finally:
            db.close()

    run_case(suite, "PR-02", "Diffusion 命中 Franka/Robomimic", t06)

    def t07(r: TestResult):
        """两篇论文项目命中不同（生态差异）。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            result = compare_papers(db, [_act_id, _dp_id])
            titles = list(result.project_relations.keys())
            assert len(titles) == 2
            hits_list = list(result.project_relations.values())
            # 两篇命中集合应有差异（不同生态）
            assert set(hits_list[0]) != set(hits_list[1]), \
                "两篇项目命中应不同"
            r.detail = f"ACT={set(hits_list[0])} vs DP={set(hits_list[1])}"
        finally:
            db.close()

    run_case(suite, "PR-03", "两篇项目命中不同", t07)


# ============================================================
# 套件 3：边界与异常
# ============================================================
def test_edge_cases():
    suite = "EdgeCases"
    from app.db.base import SessionLocal
    from app.research.paper_agent.comparator import compare_papers

    def t08(r: TestResult):
        """单论文对比抛 ValueError。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            try:
                compare_papers(db, [_act_id])
                assert False, "应抛 ValueError"
            except ValueError as e:
                assert "至少需要 2 篇" in str(e), f"错误信息不符: {e}"
            r.detail = "单论文 → ValueError ✓"
        finally:
            db.close()

    run_case(suite, "EC-01", "单论文抛 ValueError", t08)

    def t09(r: TestResult):
        """不存在的 paper_id 抛 ValueError。"""
        _ensure_setup()
        db = SessionLocal()
        try:
            try:
                compare_papers(db, ["fake-id-1", "fake-id-2"])
                assert False, "应抛 ValueError"
            except ValueError as e:
                assert "仅找到" in str(e) or "2 篇" in str(e), f"错误信息不符: {e}"
            r.detail = "不存在 ID → ValueError ✓"
        finally:
            db.close()

    run_case(suite, "EC-02", "不存在 paper_id 抛 ValueError", t09)


# ============================================================
# 套件 4：API 端点
# ============================================================
def test_api():
    suite = "API"

    def t10(r: TestResult):
        """POST /api/paper/compare 返回差异矩阵。"""
        _ensure_setup()
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/api/paper/compare", json={
            "paper_ids": [_act_id, _dp_id],
        })
        assert resp.status_code == 200, f"状态码 {resp.status_code}"
        data = resp.json()
        assert data["success"], f"应成功：{data}"
        result = data["data"]
        assert result["paper_count"] == 2
        assert result["differences"], "差异列表非空"
        assert result["project_relations"], "项目关联非空"
        r.detail = f"papers={result['paper_count']}, diffs={len(result['differences'])}"

    run_case(suite, "API-01", "POST /api/paper/compare 端点", t10)

    def t11(r: TestResult):
        """单论文请求 422 校验。"""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/api/paper/compare", json={"paper_ids": [_act_id]})
        assert resp.status_code == 422, f"单论文应 422，实际 {resp.status_code}"
        r.detail = "422 校验通过"

    run_case(suite, "API-02", "单论文 422 校验", t11)


# ===== 主入口 =====
def main():
    print("=" * 60)
    print("  Phase 3 Week 1 Day 4 · 多论文对比端到端测试")
    print("=" * 60)
    print(f"  临时 DB: {_TMP_DB}")
    print(f"  论文 1: {Path(PAPER_ACT).name}")
    print(f"  论文 2: {Path(PAPER_DP).name}")

    print("\n[套件 1] Comparator")
    test_comparator()
    print("\n[套件 2] ProjectRelations")
    test_project_relations()
    print("\n[套件 3] EdgeCases")
    test_edge_cases()
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
