# v3.3 推理优化支再加权 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 v3.0 框架内落地产权再加权——target_roles 主攻描述+40/40/20 单一真源注释、skill_profile 推理支目标提级与护城河钉住，并以源码断言测试锁死口径。

**Architecture:** 纯配置改动（两文件）+ 一个纯断言测试文件分两任务 TDD。`TargetRole` 已有 `note` 字段（策略说明）→ 按 spec 字段解析规则更新 `note`；40/40/20 口径写入 `TARGET_ROLES` 定义上方的模块级注释（紧邻赛道定义）。版本标记一律 **v3.3（2026-10-19）**（文件内部 v3.1/v3.2 编号已被 09-20/09-21 占用）。

**Tech Stack:** Python 3.13 dataclass 配置 + pytest；无新增依赖。

**Spec:** `docs/superpowers/specs/2026-10-19-v33-inference-weighting-design.md`

## Global Constraints

- 主攻赛道 `name` **保持**「大模型后训练 / Post-Training 算法工程师」一字不改；`TARGET_ROLES` keys 恒为 `[llm, vlm, ai-algo, embodied]`（不新增/不删赛道），priority 恒为 `主攻/卡位/保底/暂缓`，embodied `frozen=True` 不变。
- 提级规则：推理支五项（`Attention`、`KV Cache`、`Quantization`、`vLLM`、`FlashAttention`）`target_level = max(现值, 4)`，**只升不降**；实施前先读源确认现值（快照：5 / 5 / 4 / 4 / **3**——只有 FlashAttention 需要动）。
- 护城河三项（`Agent Application`、`RAG`、`Python`）`target_level` 不动（快照 5/5/5，测试钉 **5**）；`SKILL_PROFILE` 总数恒为 **50**（不新增技能项）；任何条目 `level` 不改（level 是实测）。
- `plan_30d`、匹配算法（`agents/match`、`services/readiness`）、匹配分口径、`TECH_BLACKLIST` 零改动。
- `docs/路线调整-Post-Training-v3.0.md` 原文零改动（git diff 核验）。
- pytest 基线 **537 passed / 2 skipped** 不得下降；跑法 `cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --basetemp=../.workbuddy/tmp/pytest-base`。
- 不得修改 `backend/tests/conftest.py`；提交只 `git add <显式路径>`；trailer `Co-Authored-By: Claude Code <noreply@anthropic.com>`；分支 `feature/mastery-plan1`。

## File Structure

| 文件 | 职责 |
|------|------|
| Modify: `backend/app/core/target_roles.py` | 模块级 40/40/20 注释块 + `llm`/`ai-algo` 的 `note` 增补（v3.3） |
| Modify: `backend/app/core/skill_profile.py` | `FlashAttention.target_level` 3→4 + 护城河注释行 |
| Create: `backend/tests/test_v33_weighting.py` | Task 1 断言（赛道结构不变 + note/注释口径） |
| Create: `backend/tests/test_v33_skill_targets.py` | Task 2 断言（五项 ≥4 / 三项 ==5 / 50 项 / level 不动） |

---

### Task 1: target_roles 权重与描述（v3.3 注记）

**Files:**
- Modify: `backend/app/core/target_roles.py`（注释块插入位置：`TARGET_ROLES: list[TargetRole] = [` 之前；`llm`/`ai-algo` 的 `note` 字符串增补）
- Create: `backend/tests/test_v33_weighting.py`

**Interfaces:**
- Produces: `TARGET_ROLES`（结构不变）；`llm.note` 含「推理优化支」与「40/40/20」；`ai-algo.note` 含「承载推理优化支」；模块源含 `40/40/20（v3.3 再加权，2026-10-19）` 注释块——Task 2 与验收段依赖这些口径存在。

- [ ] **Step 1: 写失败测试（完整文件）**

```python
# backend/tests/test_v33_weighting.py
"""v3.3 推理优化支再加权钉（spec 2026-10-19-v33）：结构不变 + 口径进单一真源。"""

from pathlib import Path

from app.core.target_roles import TARGET_ROLES

_ROLES_SRC = Path(__file__).resolve().parents[1] / "app" / "core" / "target_roles.py"


def test_track_structure_unchanged():
    # spec 边界：不新增/不删赛道，priority 序不变
    assert [r.key for r in TARGET_ROLES] == ["llm", "vlm", "ai-algo", "embodied"]
    assert [r.priority for r in TARGET_ROLES] == ["主攻", "卡位", "保底", "暂缓"]
    frozen = {r.key: r.frozen for r in TARGET_ROLES}
    assert frozen == {"llm": False, "vlm": False, "ai-algo": False, "embodied": True}


def test_main_track_name_unchanged():
    llm = next(r for r in TARGET_ROLES if r.key == "llm")
    assert llm.name == "大模型后训练 / Post-Training 算法工程师"


def test_llm_note_carries_new_focus_and_ratio():
    llm = next(r for r in TARGET_ROLES if r.key == "llm")
    assert "推理优化支" in llm.note
    assert "40/40/20" in llm.note


def test_ai_algo_note_hooks_inference_branch():
    ai = next(r for r in TARGET_ROLES if r.key == "ai-algo")
    assert "承载推理优化支" in ai.note


def test_embodied_note_and_freeze_preserved():
    emb = next(r for r in TARGET_ROLES if r.key == "embodied")
    assert emb.frozen is True
    assert "长期观察" in emb.note


def test_module_carries_v33_ratio_comment():
    src = _ROLES_SRC.read_text(encoding="utf-8")
    assert "40/40/20（v3.3 再加权，2026-10-19）" in src
    for line in ("40% 推理优化支主攻", "40% Agent/RAG 护城河维持", "20% 观察带"):
        assert line in src, line


def test_llm_required_skills_still_include_moat():
    # 护城河技能必须仍在匹配要求里（40% 护城河兑现的机制前提）
    llm = next(r for r in TARGET_ROLES if r.key == "llm")
    assert "RAG" in llm.required_skills and "Agent Application" in llm.required_skills
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v33_weighting.py -q`
Expected: FAIL（`test_module_carries_v33_ratio_comment` 找不到注释；`test_llm_note...` 找不到「推理优化支」）

- [ ] **Step 3: 实现**

**3a. 模块注释块**——插入 `TARGET_ROLES: list[TargetRole] = [` 上方（紧跟既有四赛道说明注释之后）：

```python
# ================================================================================
# 2026-10-19 推理优化支再加权 v3.3（spec: docs/superpowers/specs/2026-10-19-v33-inference-weighting-design.md）
# ================================================================================
# v3.0 框架内的重心加权，不是 reframe。主攻内部的学习与 artifact 重心 = 推理优化支
# （vLLM / KV Cache / 量化 / FlashAttention 语义层），直接对冲 09-08 技术面内核层失分。
# 40/40/20（v3.3 再加权，2026-10-19）：
#   40% 推理优化支主攻（治内核层失分，挂 Mini Lab 07_inference 的 artifact）
#   40% Agent/RAG 护城河维持（应用层 3.75，求职筹码，不降权）
#   20% 观察带（DeepSeek×TileLang×昇腾 信号核实；国产算力生态跟踪）
# 提级细则见 skill_profile 侧：推理支五项 target=max(现值,4)，护城河三项不动。
```

**3b. `llm` 赛道 note 增补**——`note=` 现值（v3.2 文本）**末尾追加**（保留原文）：

```python
        note="v3.2：Post-Training 横向能力（SFT→DPO→RL），VLM 是其模型分支；"
             "Transformer→SFT→LoRA/QLoRA→DPO/GRPO→Eval 必须能讲透并做过实验；"
             "补 RAG/Agent Application（真实 JD 要求且是本人强项，见 v3.2 注记）；"
             "v3.3：学习与 artifact 重心=推理优化支（vLLM/KV Cache/量化/FlashAttention），"
             "权重口径 40/40/20 见文件头 v3.3 注释",
```

**3c. `ai-algo` 赛道 note 增补**——现值末尾追加：

```python
        note="进入模型团队的入口岗：推理优化与工程交付是现有强项，可快速拿面试；"
             "v3.3：承载推理优化支（priority=保底不变）",
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v33_weighting.py -q`
Expected: PASS（7 个用例）

- [ ] **Step 5: 全量回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --basetemp=../.workbuddy/tmp/pytest-base`
Expected: **537 + 7 = 544 passed / 2 skipped / 0 failed**

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/target_roles.py backend/tests/test_v33_weighting.py
git commit -m "feat(target_roles): v3.3 主攻重心=推理优化支 + 40/40/20 单一真源注释"
```

（commit message 末尾带 trailer `Co-Authored-By: Claude Code <noreply@anthropic.com>`）

---

### Task 2: skill_profile 提级与护城河钉住

**Files:**
- Modify: `backend/app/core/skill_profile.py`
- Create: `backend/tests/test_v33_skill_targets.py`

**Interfaces:**
- Consumes: Task 1 的口径注释（不依赖其代码符号）
- Produces: `SKILL_PROFILE` 中五项 `target_level >= 4`、三项护城河 `target_level == 5`、总数 50、五项 `level` 原值不变、源含护城河注释行——验收段读这些断言作为通过证据。

- [ ] **Step 1: 写失败测试（完整文件）**

```python
# backend/tests/test_v33_skill_targets.py
"""v3.3 提级钉（spec §3.2）：五项 target≥4、护城河三项==5、50 项不增、level 不动。"""

from pathlib import Path

from app.core.skill_profile import SKILL_PROFILE

_SRC = Path(__file__).resolve().parents[1] / "app" / "core" / "skill_profile.py"

INFERENCE_FIVE = ["Attention", "KV Cache", "Quantization", "vLLM", "FlashAttention"]
MOAT_THREE = ["Agent Application", "RAG", "Python"]
# level 快照（level=实测，spec 禁止改动）
LEVEL_SNAPSHOT = {
    "Attention": 3, "KV Cache": 2, "Quantization": 2, "vLLM": 2, "FlashAttention": 1,
}


def _of(name: str):
    return next(s for s in SKILL_PROFILE if s.name == name)


def test_inference_five_targets_at_least_4():
    for name in INFERENCE_FIVE:
        s = _of(name)
        assert 4 <= s.target_level <= 5, f"{name}.target_level={s.target_level}"


def test_moat_three_targets_pinned_at_5():
    for name in MOAT_THREE:
        assert _of(name).target_level == 5, name


def test_levels_untouched():
    for name, level in LEVEL_SNAPSHOT.items():
        assert _of(name).level == level, f"{name}.level 被改动（spec：level=实测不改）"


def test_skill_count_stays_50():
    assert len(SKILL_PROFILE) == 50  # 不新增技能项


def test_source_has_v33_moat_comment():
    src = _SRC.read_text(encoding="utf-8")
    assert "# v3.3：护城河维持，不因推理支加权降权" in src
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v33_skill_targets.py -q`
Expected: FAIL（`FlashAttention.target_level=3 < 4`；源缺护城河注释）——其余 3 条（护城河==5 / level 快照 / 50 项）是既有真相的守护性通过，属预期

- [ ] **Step 3: 实现（先读源复核，再动两处）**

**3a. 提级（按 `max(现值, 4)` 规则）**——先 `grep -n 'name="FlashAttention"' backend/app/core/skill_profile.py` 确认现值 3，然后仅此一行：

```diff
-        name="FlashAttention", domain="llm_foundation", category="Weak", level=1, target_level=3, evidence=["仅概念层"],
+        name="FlashAttention", domain="llm_foundation", category="Weak", level=1, target_level=4, evidence=["仅概念层"],
```

（其余四项 grep 复核后应为 Attention=5 / KV Cache=5 / Quantization=4 / vLLM=4——**已 ≥4 不动**；若复核发现与快照不符，按 `max(现值,4)` 执行并在报告记录实际值。）

**3b. 护城河注释**——加在 `name="Agent Application"` 那条 `SkillProfile(` 定义行的**紧上方**：

```python
        # v3.3：护城河维持，不因推理支加权降权（Agent Application / RAG / Python 三项 target 不动）
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_v33_skill_targets.py -q`
Expected: PASS（5 个用例）

- [ ] **Step 5: 全量回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --basetemp=../.workbuddy/tmp/pytest-base`
Expected: **544 + 5 = 549 passed / 2 skipped / 0 failed**

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/skill_profile.py backend/tests/test_v33_skill_targets.py
git commit -m "feat(skill_profile): v3.3 推理支五项 target≥4 + 护城河三项钉住"
```

（trailer `Co-Authored-By: Claude Code <noreply@anthropic.com>`）

---

## 验收（本计划整体，对应 spec §六）

- [ ] **配置种子重跑**（spec §六.1）：
  Run: `cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/seed_job_hunt.py`
  Expected: 正常退出无异常；随后断言口径可读：
  ```
  PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "from app.core.target_roles import TARGET_ROLES; llm=next(r for r in TARGET_ROLES if r.key=='llm'); print(llm.note); assert '推理优化支' in llm.note"
  ```
  Expected: 打印含 v3.3 重心的 note，无 AssertionError
- [ ] **v3.0 文档零改动**：`git diff 8a9c6be..HEAD --name-only -- "docs/路线调整-Post-Training-v3.0.md"` → 空输出
- [ ] **改动面核对**：`git diff c655e54..HEAD --name-only` 仅含两配置 + 两测试文件（基线=计划提交点；用 8a9c6be 会把计划文档自身计入）
- [ ] **全量**：549 passed / 2 skipped / 0 failed
- [ ] **（plan 期间已改）spec 文件名与文内自称均为 v3.3**：`grep -n "v3\.1" docs/superpowers/specs/2026-10-19-v33-inference-weighting-design.md` → **仅"血缘"说明那一行命中**（标题、注释块、护城河注释、reframe 自查均须为 v3.3；多出任何一行即失败）

## 明确不做（spec §四回执）

不动 `plan_30d` · 不动匹配算法/匹配口径（方案 B 留触发条件）· 不新增赛道/技能 · 不救试用期 · 不开展 TileLang 学习（观察带核实为用户待办）
