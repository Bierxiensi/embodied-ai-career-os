"""P4 求职包装测试（README 骨架 + 简历技能行）。

覆盖 docs/platform-direction-30day.md §七 P4 三项要求与验收：

  A. 引擎（纯函数）
     - README 骨架在任何数据量下都含全部 13 节（plan_30d Day 24 结构）
     - Failure Cases / Lessons Learned 标为必填（Day 24 验收：不得空着）
     - 证据链与实验记录要真的落进正文
     - 简历技能行只收录有证据（gate>=1）的技能；自评强但无证据 → pending
  B. 项目 README 端点
     - GET  /api/projects/{id}/readme  预览（不落库）
     - POST /api/projects/{id}/readme  一键导出 / 润色回存
     - PATCH 标记 completed 仍自动生成（回归：改走共享构建器后行为不变）
  C. GET /api/resume/skill-lines
     - 形状正确
     - 出现真实证据（录一道带 skill_name 的面试题）→ ready 增长且附 refs

隔离：由 tests/conftest.py 提供会话级临时库；断言用增量，不假设绝对行数。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.packaging.engine import (
    README_SECTIONS,
    REQUIRED_SECTIONS,
    build_readme_skeleton,
    build_skill_lines,
)

client = TestClient(app)


# ============================================================
# 辅助
# ============================================================


def _new_project(name: str) -> int:
    resp = client.post("/api/projects", json={"name": name, "goal": "P4 测试目标"})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _add_milestone(pid: int, title: str = "基线跑通") -> int:
    resp = client.post(
        f"/api/projects/{pid}/milestones",
        json={"version": "V1", "title": title, "goal": "跑通基线", "status": "completed", "sort_order": 0},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["id"]


def _get_readme(pid: int) -> dict:
    resp = client.get(f"/api/projects/{pid}/readme")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _skill_lines() -> dict:
    resp = client.get("/api/resume/skill-lines")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ============================================================
# A. 引擎（纯函数）
# ============================================================


def test_readme_skeleton_has_all_sections_even_with_no_data():
    """空数据也必须产出完整骨架 —— 这才是"不从空白开始写"。"""

    md = build_readme_skeleton(name="空项目", goal="没有里程碑也没有技能")

    assert md.startswith("# 空项目")
    assert "没有里程碑也没有技能" in md
    for section in README_SECTIONS:
        assert f"## {section}" in md, section
    # 无数据时给出"怎么才会有数据"的指引，而不是留白
    assert "尚未录入里程碑" in md
    assert "尚无实验记录" in md


def test_readme_skeleton_marks_required_sections():
    """Failure Cases / Lessons Learned 必须显式标为必填（Day 24 验收）。"""

    md = build_readme_skeleton(name="P", goal="G")
    for section in REQUIRED_SECTIONS:
        assert f"## {section}" in md
    assert md.count("⚠️ **必填**") == len(REQUIRED_SECTIONS)
    # 其余章节用普通待补提示，不与必填混淆
    assert "📝 待补" in md


def test_readme_skeleton_embeds_evidence_milestones_and_experiments():
    """数据能填的部分要真的填进去（里程碑 / 技能证据 / 实验对比表）。"""

    md = build_readme_skeleton(
        name="LoRA Lab",
        goal="跑通 LoRA vs QLoRA",
        github_url="https://github.com/x/lora",
        status="completed",
        current_version="V2",
        milestones=[
            {"version": "V1", "title": "基线跑通", "goal": "跑通", "status": "completed"},
            {"version": "V2", "title": "微调对比", "goal": "四组对比", "status": "in_progress"},
        ],
        skills=["LoRA/QLoRA", "Neck 层"],
        evidence_by_skill={
            "LoRA/QLoRA": {
                "gate_level": 3,
                "evidence": [
                    {"level": 2, "kind": "code", "label": "能实现/修改", "ref": "Day 12 的代码 + commit"},
                    {"level": 3, "kind": "experiment", "label": "能做实验", "ref": "实验：LoRA vs QLoRA"},
                ],
            }
        },
        experiments=[
            {
                "name": "LoRA vs QLoRA",
                "kind": "finetune",
                "variant_count": 3,
                "conclusion": "QLoRA 省 62% 显存",
            }
        ],
    )

    assert "https://github.com/x/lora" in md
    assert "**状态**：completed" in md
    # 里程碑进度
    assert "进度 **1/2**（50%）" in md
    assert "**V1** 基线跑通" in md
    assert "🔄" in md and "✅" in md
    # 技能证据（含 gate 等级与具体证据文案）
    assert "**LoRA/QLoRA**（证据 L3）" in md
    assert "Day 12 的代码 + commit" in md
    # 有证据 / 无证据要分开点名，避免把没证据的技能也说得像有
    assert "尚无自动可核验证据" in md
    assert "Neck 层" in md
    # 实验对比表
    assert "| LoRA vs QLoRA | finetune | 3 | QLoRA 省 62% 显存 |" in md


def test_skill_lines_include_only_gated_skills():
    """ready 只收 gate>=1；自评 >=3 无证据进 pending；自评低的无证据两边都不进。"""

    result = build_skill_lines(
        skills=[
            {"name": "有证据的", "level": 4, "category": "Strong"},
            {"name": "自评强没证据", "level": 4, "category": "Strong"},
            {"name": "自评弱没证据", "level": 1, "category": "Weak"},
        ],
        evidence_by_skill={
            "有证据的": {
                "gate_level": 2,
                "evidence": [{"level": 2, "kind": "code", "label": "能实现/修改", "ref": "代码 X"}],
            }
        },
    )

    assert [r["skill"] for r in result["ready"]] == ["有证据的"]
    assert [p["skill"] for p in result["pending"]] == ["自评强没证据"]
    assert result["summary"] == {
        "total": 3,
        "ready": 1,
        "pending": 1,
        "pending_min_level": 3,
    }
    # 行文里要带上等级与最高一级证据的出处
    assert result["ready"][0]["line"] == "有证据的（L4）：代码 X"
    assert result["ready"][0]["refs"][0]["ref"] == "代码 X"
    assert "L1" in result["pending"][0]["missing"]


def test_skill_lines_sorts_by_gate_then_level():
    """排序稳定：证据硬的在前，同级按名称。"""

    result = build_skill_lines(
        skills=[
            {"name": "B", "level": 5},
            {"name": "A", "level": 2},
            {"name": "C", "level": 5},
        ],
        evidence_by_skill={
            "A": {"gate_level": 4, "evidence": [{"level": 4, "label": "能研究", "ref": "r"}]},
            "B": {"gate_level": 4, "evidence": [{"level": 4, "label": "能研究", "ref": "r"}]},
            "C": {"gate_level": 2, "evidence": [{"level": 2, "label": "能实现/修改", "ref": "r"}]},
        },
    )
    assert [r["skill"] for r in result["ready"]] == ["B", "A", "C"]


# ============================================================
# B. 项目 README 端点
# ============================================================


def test_get_readme_previews_without_persisting():
    pid = _new_project("P4 预览项目")
    _add_milestone(pid)

    data = _get_readme(pid)

    assert data["project_id"] == pid
    assert data["name"] == "P4 预览项目"
    assert data["saved_readme"] is None  # 预览不落库
    assert data["draft"].startswith("# P4 预览项目")
    assert "## Failure Cases" in data["draft"]
    assert data["counts"]["milestones"] == 1
    assert data["counts"]["chars"] > 0

    # 回读项目：readme 仍为空 —— 证明 GET 没有副作用
    proj = client.get(f"/api/projects/{pid}").json()["data"]
    assert proj["readme"] is None


def test_post_readme_without_content_exports_generated_draft():
    pid = _new_project("P4 一键导出项目")
    _add_milestone(pid, title="导出里程碑")

    resp = client.post(f"/api/projects/{pid}/readme", json={})
    assert resp.status_code == 200, resp.text
    saved = resp.json()["data"]["saved_readme"]

    assert "导出里程碑" in saved
    assert "## Motivation" in saved

    proj = client.get(f"/api/projects/{pid}").json()["data"]
    assert proj["readme"] == saved


def test_post_readme_with_content_persists_polished_text():
    """润色后回存：存的必须是传入文本，不被重新生成覆盖。"""

    pid = _new_project("P4 回存项目")
    _add_milestone(pid)

    polished = "# 我润色过的 README\n\n## Failure Cases\n\nQLoRA 4bit 在 7B 上 loss 不收敛。\n"
    resp = client.post(f"/api/projects/{pid}/readme", json={"content": polished})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["saved_readme"] == polished

    # 此时 GET 应同时给出 saved（润色版）与 draft（重新生成版），两者不同
    data = _get_readme(pid)
    assert data["saved_readme"] == polished
    assert data["draft"] != polished


def test_post_readme_rejects_blank_content():
    pid = _new_project("P4 空内容项目")

    resp = client.post(f"/api/projects/{pid}/readme", json={"content": "   \n "})
    assert resp.status_code == 400
    assert "空" in resp.json()["detail"]


def test_readme_endpoints_404_for_missing_project():
    assert client.get("/api/projects/999999/readme").status_code == 404
    assert client.post("/api/projects/999999/readme", json={}).status_code == 404


def test_patch_completed_still_generates_readme_skeleton():
    """回归：标记 completed 自动生成 README（现走共享构建器，行为与旧内联实现等价）。"""

    pid = _new_project("P4 完成自动生成")
    _add_milestone(pid, title="完成即生成")

    resp = client.patch(f"/api/projects/{pid}", json={"status": "completed"})
    assert resp.status_code == 200, resp.text
    readme = resp.json()["data"]["readme"]

    assert readme is not None
    assert "P4 完成自动生成" in readme
    assert "完成即生成" in readme
    # 新构建器多出来的骨架标记，证明不再走旧的内联拼接
    assert "## Failure Cases" in readme


# ============================================================
# C. /api/resume/skill-lines
# ============================================================


def test_skill_lines_endpoint_shape():
    data = _skill_lines()

    assert data["summary"]["total"] > 0
    assert data["summary"]["pending_min_level"] == 3
    assert isinstance(data["ready"], list) and isinstance(data["pending"], list)
    # summary 必须与返回列表长度一致 —— 曾经 pending 截断到 12 但 summary 报 16，
    # 前端会显示"16 项却只有 12 个"。冒烟测试抓到，这里钉死。
    assert data["summary"]["ready"] == len(data["ready"])
    assert data["summary"]["pending"] == len(data["pending"])
    assert data["note"]
    # pending 里的技能自评必须达到门槛，且都还缺 L1 证据
    for p in data["pending"]:
        assert p["level"] >= 3
        assert p["gate_level"] < 1
        assert p["missing"]


def test_skill_lines_ready_grows_when_real_evidence_appears():
    """证据→简历行的闭环：给一个尚未有证据的技能录一道面试题（L1），它应进入 ready。"""

    ready_before = {r["skill"] for r in _skill_lines()["ready"]}

    skills = client.get("/api/skills").json()["data"]
    target = next((s for s in skills if s["name"] not in ready_before), None)
    assert target is not None, "临时库里所有技能都已有证据，用例失去意义"

    name = target["name"]
    resp = client.post(
        "/api/interview-questions",
        json={
            "category": "LLM",
            "question": "P4 证据链联动题：请解释该技能的核心机制？",
            "skill_name": name,
            "answer_outline": "要点…",
        },
    )
    assert resp.status_code == 200, resp.text
    qid = resp.json()["data"]["id"]

    try:
        row = next((r for r in _skill_lines()["ready"] if r["skill"] == name), None)
        assert row is not None, f"{name} 未因面试题进入 ready"
        assert row["gate_level"] >= 1
        assert row["refs"], "ready 行必须附带证据清单"
        assert any("题" in r["ref"] for r in row["refs"])
    finally:
        client.delete(f"/api/interview-questions/{qid}")
