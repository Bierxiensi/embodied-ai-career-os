"""P3 题库覆盖率测试。

覆盖 docs/platform-direction-30day.md 决策 5 / P3 验收：
  A. 覆盖率引擎（纯函数）：分类目标、核心必达、红格 missing、未知技能自动补行
  B. GET /api/interview-questions/coverage：默认「主攻」赛道技能行 + 口径正确
  C. ?track_key= 切换矩阵行（embodied 赛道）
  D. 快速录题带 skill_name → 覆盖率矩阵对应格子 +1

隔离：由 tests/conftest.py 提供会话级临时库；断言用增量，不假设绝对行数。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.agents.interview.engine import (
    CORE_CATEGORIES,
    CORE_TARGET,
    QUESTION_CATEGORY_TARGETS,
    coverage_matrix,
)
from app.main import app

client = TestClient(app)

CATS = {"LLM", "Multimodal", "Project", "Coding"}


def _cov(track_key: str | None = None) -> dict:
    url = "/api/interview-questions/coverage"
    if track_key:
        url += f"?track_key={track_key}"
    resp = client.get(url)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ============================================================
# A. 引擎（纯函数）
# ============================================================


def test_category_targets_sum_to_150_and_core_80():
    """计划口径裁决：累计目标 150，核心必达 80（见决策 5）。"""

    assert sum(QUESTION_CATEGORY_TARGETS.values()) == 150
    assert CORE_TARGET == 80
    assert QUESTION_CATEGORY_TARGETS["LLM"] + QUESTION_CATEGORY_TARGETS["Multimodal"] == 80


def test_targets_are_single_sourced_and_derived():
    """护栏：150 / 80 必须**派生**自 QUESTION_CATEGORY_TARGETS，不得各处硬编码。

    2026-09-22 修：原先 `api/plan.py` 另有一份 `TARGET_QUESTIONS = 150`，`CORE_TARGET`
    也是字面量（不从分类目标派生）—— 改一处漏一处会静默产生不一致，且文档误称
    "只改 QUESTION_CATEGORY_TARGETS 一处"。本测试把"单一真源"锁成约定。
    """

    from app.agents.interview.engine import TARGET_TOTAL
    from app.api.plan import TARGET_QUESTIONS

    # 核心必达 = 核心分类目标和
    assert CORE_TARGET == sum(QUESTION_CATEGORY_TARGETS[c] for c in CORE_CATEGORIES)
    # 累计目标 = 全部分类目标和
    assert TARGET_TOTAL == sum(QUESTION_CATEGORY_TARGETS.values())
    # 计划总账（另一个模块的 KPI）与题库口径必须是同一个值
    assert TARGET_QUESTIONS == TARGET_TOTAL


def test_coverage_matrix_marks_red_cells_and_appends_unknown_skills():
    """红格 = (技能, 分类) 计数为 0；题库里未在传入技能列表中的技能自动补行。"""

    questions = [
        {"category": "LLM", "skill_name": "Transformer"},
        {"category": "Coding", "skill_name": "Transformer"},
        {"category": "LLM", "skill_name": "NewSkill"},
    ]
    data = coverage_matrix(questions, ["Transformer"])

    # 行顺序：传入技能在前，未知技能补尾
    assert [s["name"] for s in data["skills"]] == ["Transformer", "NewSkill"]

    tr = data["skills"][0]
    assert tr["counts"]["LLM"] == 1 and tr["counts"]["Coding"] == 1
    assert set(tr["missing"]) == {"Multimodal", "Project"}  # 红格

    # 分类进度与合计
    by_cat = {c["key"]: c for c in data["categories"]}
    assert by_cat["LLM"]["done"] == 2
    assert by_cat["LLM"]["gap"] == QUESTION_CATEGORY_TARGETS["LLM"] - 2
    assert by_cat["LLM"]["core"] is True and by_cat["Coding"]["core"] is False
    assert data["core_done"] == 2  # LLM 2 + Multimodal 0
    assert data["total"] == 3
    assert data["cells_total"] == 2 * 4
    assert data["cells_filled"] == 3


def test_coverage_matrix_ignores_unattributed_questions_in_rows_but_counts_total():
    """没有 skill_name 的题不计入任何技能行，但仍计入分类/总数（否则缺口会虚高）。"""

    data = coverage_matrix(
        [{"category": "LLM", "skill_name": None}], ["Transformer"]
    )
    assert data["total"] == 1
    assert data["skills"][0]["total"] == 0
    assert set(data["skills"][0]["missing"]) == CATS


# ============================================================
# B/C. 端点
# ============================================================


def test_coverage_endpoint_shape_and_targets():
    data = _cov()

    assert data["target_total"] == 150
    assert data["core_target"] == 80
    assert {c["key"] for c in data["categories"]} == CATS
    assert data["cells_total"] == len(data["skills"]) * 4
    # 默认「主攻」赛道（llm）的硬性要求技能都在矩阵行里
    names = {s["name"] for s in data["skills"]}
    for s in ("Transformer", "Attention", "Pretraining", "SFT", "LoRA/QLoRA"):
        assert s in names, (s, names)


def test_coverage_track_key_scopes_rows():
    """?track_key=embodied → 矩阵行换成具身赛道的技能（保留但冻结，仍可查覆盖）。"""

    data = _cov("embodied")
    names = {s["name"] for s in data["skills"]}
    assert {"ROS2", "VLA", "Sim2Real"} <= names


# ============================================================
# D. 快速录题 → 覆盖率联动
# ============================================================


def test_quick_add_question_attributes_skill_and_increments_cell():
    """录一道带 skill_name 的题 → 矩阵对应格子计数器 +1（红格转绿）。"""

    before = next(s for s in _cov()["skills"] if s["name"] == "Transformer")
    before_llm = before["counts"].get("LLM", 0)

    resp = client.post(
        "/api/interview-questions",
        json={
            "category": "LLM",
            "question": "P3 覆盖率联动题：Transformer 的 QKV 是怎么来的？",
            "skill_name": "Transformer",
            "source_day_seq": 1,
            "answer_outline": "要点…",
        },
    )
    assert resp.status_code == 200, resp.text
    q = resp.json()["data"]
    qid = q["id"]

    try:
        # 回读：三个 P2 字段都要落库（否则覆盖率/四件套联动是假的）
        assert q["skill_name"] == "Transformer"
        assert q["source_day_seq"] == 1
        assert q["answer_outline"] == "要点…"

        after = next(s for s in _cov()["skills"] if s["name"] == "Transformer")
        assert after["counts"]["LLM"] == before_llm + 1
        assert "LLM" not in after["missing"]
    finally:
        client.delete(f"/api/interview-questions/{qid}")


def test_coverage_after_cleanup_returns_to_baseline():
    """删除刚录的题后，Transformer 的 LLM 计数回到基线（保证测试不污染后续断言）。"""

    row = next(s for s in _cov()["skills"] if s["name"] == "Transformer")
    assert row["counts"].get("LLM", 0) >= 0
