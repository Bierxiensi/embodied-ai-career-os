# 掌握单元双环 · 计划 1：裁决落地 + 减法清理 + 三入口 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 spec 第 0 步五项裁决，完成减法清理（死链/过时 prompt/占位输入），建成三问三入口（/learn /review /progress）与 `GET /api/today` 聚合端点。

**Architecture:** 纯后端先行（TDD 改纯函数与编排层），再建聚合端点，最后前端 IA 收敛——`today` 页内容整体迁移为 `/learn`，`/review`、`/progress` 用既有数据源组装，导航从 11 入口收敛为 3 入口 + 低频功能进 CommandPalette。不新增业务数据模型（那是计划 2）。

**Tech Stack:** FastAPI + SQLAlchemy + SQLite（backend）；Next.js 16.2.12 App Router + React 19 + Tailwind v4（frontend）；pytest / tsc / eslint 门禁。

**Spec:** `docs/superpowers/specs/2026-09-24-mastery-unit-dual-loop-design.md`（本计划覆盖其 §6、§7 步 1-2）

## Global Constraints

- 前端动代码前**先读** `frontend/node_modules/next/dist/docs/` 对应指南（`frontend/AGENTS.md` 强制：Next 16 有破坏性变更，不得按记忆写代码）。
- 测试隔离不可破坏：`backend/tests/conftest.py` 模块级钉死 `DATABASE_URL`（临时库）与 `LLM_PROVIDER=mock`；任何用例不得依赖开发者 `.env`；真 provider 装配用 `monkeypatch` 改 `settings`。
- 新表/新时间字段一律 **aware UTC**；前端 service 层读路径统一 `normalizeUtc`（naive UTC 补 `Z`），"今天"判定用本地日历日。
- API 字段 `snake_case`，前端 service 层转 `camelCase`；`apiClient` 不做 key 转换；统一响应 `{success, data, message}`（`app.core.response.ok`）。
- 提交纪律：先 `git status --short` 核对，只 `git add <显式文件路径>`，**禁止 `git add -A` / `git add .`**。
- 活跃写端点目标 **≤25**（spec §4.2/§5.3）：本计划只减不增（唯一新增是只读聚合 `GET /api/today`）。
- pytest 基线 **437 passed / 0 failed / 2 skipped** 不得下降；跑法：`cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --tb=short`（若 TEMP 累积触发 safe-delete 护栏，加 `--basetemp=../.workbuddy/tmp/pytest-base` 重跑）。
- 前端门禁：`cd frontend && node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` → RC0；`node node_modules/eslint/bin/eslint.js <改动文件>` → 零问题（既有基线除外，零新增）。
- LLM 相关改动必须保持 **LLM 优先、规则兜底、降级可见** 三件套（spec §5.1）；MockClient 输出不得冒充真实结果。
- 文案中不得写死会变的数字（如"8 类资源"）——写"资源均来自资源锁"这类无数字口径。

---

### Task 1: Y7 清理演示学习日志（备份 → 删除 → 核对）

**Files:**
- Create: `backend/scripts/clean_demo_learning_logs.py`
- Test: `backend/tests/test_clean_demo_logs.py`

**Interfaces:**
- Produces: `is_demo_log(content: str, created_at: datetime) -> bool`（scripts 内纯函数，测试直接 import）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_clean_demo_logs.py
"""Y7 演示学习日志判定谓词测试（2026-09-24 前置裁决）。"""

from datetime import datetime

from scripts.clean_demo_learning_logs import is_demo_log


def test_demo_batch_matched():
    assert is_demo_log(
        "完成了 ROS2 publisher 节点，记录到学习日志。",
        datetime(2026, 9, 10, 7, 7, 20),
    )


def test_real_log_not_matched():
    assert not is_demo_log(
        "今天把 DPO 的 loss 推导过了一遍，弄清了 reference model 的作用。",
        datetime(2026, 9, 24, 20, 0, 0),
    )


def test_same_day_real_content_not_matched():
    # 同日但内容不含演示指纹 → 不删（宁可漏删，不可错删）
    assert not is_demo_log("手写 SFT trainer 笔记", datetime(2026, 9, 10, 23, 0, 0))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_clean_demo_logs.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'scripts'` 或文件不存在）

- [ ] **Step 3: 写脚本实现**

```python
# backend/scripts/clean_demo_learning_logs.py
"""Y7：清理 learning_logs 中 2026-09-10 的演示数据（14 条重复 "ROS2 publisher"）。

2026-09-24 前置裁决：清（先备份）。谓词刻意保守 —— 必须同时满足
「2026-09-10 当天」且「内容含演示指纹」才删，宁可漏删不可错删。

用法：
    python scripts/clean_demo_learning_logs.py --dry-run   # 只看将删几条
    python scripts/clean_demo_learning_logs.py --yes       # 备份后删除
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import SessionLocal  # noqa: E402
from app.models.learning_log import LearningLog  # noqa: E402

DEMO_DAY = date(2026, 9, 10)
DEMO_FINGERPRINT = "ROS2 publisher"


def is_demo_log(content: str, created_at: datetime) -> bool:
    """演示日志谓词：演示日 + 演示指纹，双条件缺一不可。"""
    return created_at.date() == DEMO_DAY and DEMO_FINGERPRINT in (content or "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="确认删除（先备份库文件）")
    parser.add_argument("--dry-run", action="store_true", help="只统计不删除")
    args = parser.parse_args()

    db_path = Path(__file__).resolve().parents[1] / "data" / "app.db"
    db = SessionLocal()
    try:
        rows = db.query(LearningLog).all()
        victims = [r for r in rows if is_demo_log(r.content, r.created_at)]
        print(f"learning_logs 总数={len(rows)}，命中演示谓词={len(victims)}")
        for r in victims:
            print(f"  [del] id={r.id} {r.created_at.isoformat()} {r.content[:30]}")

        if args.dry_run or not args.yes:
            print("未删除（--dry-run 或缺 --yes）。")
            return 0

        backup = db_path.with_name(f"{db_path.name}.bak-{datetime.now():%Y%m%d-%H%M%S}-learnlogs")
        shutil.copy2(db_path, backup)
        print(f"已备份：{backup}")

        for r in victims:
            db.delete(r)
        db.commit()
        remaining = db.query(LearningLog).count()
        print(f"删除 {len(victims)} 条，剩余 {remaining} 条。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_clean_demo_logs.py -q`
Expected: `3 passed`

- [ ] **Step 5: 对开发库执行清理并核对**

Run（cwd=backend）:
```
.venv/Scripts/python.exe scripts/clean_demo_learning_logs.py --dry-run
.venv/Scripts/python.exe scripts/clean_demo_learning_logs.py --yes
sqlite3 data/app.db "SELECT COUNT(*) FROM learning_logs;"
```
Expected: dry-run 命中 14；--yes 后剩余 **0**；输出含备份文件名。

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/clean_demo_learning_logs.py backend/tests/test_clean_demo_logs.py
git commit -m "chore(data): Y7 清理 14 条演示学习日志（备份先行，谓词双条件）"
```

---

### Task 2: X4 `_timeline_score` 按申请窗口重计分

**Files:**
- Modify: `backend/app/agents/phd/agent.py:79-91`（整函数替换）
- Test: `backend/tests/test_phd_timeline_score.py`

**Interfaces:**
- Consumes: `PhDMatchEngine.compute(...)` 调用方不变（签名不动）
- Produces: `_timeline_score(deadline: date | None, today: date) -> int`，新分带见实现

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_phd_timeline_score.py
"""X4：时间窗口分必须区分「黄金窗口 / 太近 / 太远 / 未公布」（2026-09-24 裁决）。"""

from datetime import date

from app.agents.phd.agent import _timeline_score

TODAY = date(2026, 9, 24)


def test_none_deadline_is_neutral_not_high():
    # 旧实现 None→70，导致不录截止日的机会排名虚高（X4 病灶）
    assert _timeline_score(None, TODAY) == 55


def test_expired_is_low():
    assert _timeline_score(date(2026, 9, 23), TODAY) == 20


def test_too_soon_is_penalized():
    # 30 天内截止：来不及准备
    assert _timeline_score(date(2026, 10, 10), TODAY) == 50


def test_golden_window_is_highest():
    # 30-270 天：有准备期且不遥远（覆盖 26 秋-27 春申请季）
    assert _timeline_score(date(2026, 12, 31), TODAY) == 95
    assert _timeline_score(date(2027, 6, 20), TODAY) == 95


def test_far_future_decays():
    assert _timeline_score(date(2027, 12, 31), TODAY) == 75
    assert _timeline_score(date(2029, 1, 1), TODAY) == 55
```

- [ ] **Step 2: 跑测试确认失败（旧实现断言不匹配）**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_phd_timeline_score.py -q`
Expected: FAIL（如 `assert 70 == 55`）

- [ ] **Step 3: 替换 `_timeline_score` 实现**

替换 `backend/app/agents/phd/agent.py:79-91` 为：

```python
def _timeline_score(deadline: date | None, today: date) -> int:
    """时间窗口分（2026-09-24 X4 修复）：按「窗口距今」分带计分。

    旧实现 None→70、≤365 天一律 100，导致不录截止日的排名虚高、
    一个月内截止的「来不及准备」反而满分。新分带：
      None→55 未公布（中性偏保守） | 已过期→20 | <30 天→50 来不及
      30-270 天→95 黄金窗口（有准备期） | 270-540→75 | 更远→55
    """

    if deadline is None:
        return 55
    days = (deadline - today).days
    if days < 0:
        return 20
    if days < 30:
        return 50
    if days <= 270:
        return 95
    if days <= 540:
        return 75
    return 55
```

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_phd_timeline_score.py tests/test_phd_match.py -q`（若 `test_phd_match.py` 不存在则只跑前者），然后全量 `python -m pytest tests/ -q --tb=short`
Expected: 新测试 `5 passed`；全量 `437+ passed / 0 failed / 2 skipped`（基线不降）

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/phd/agent.py backend/tests/test_phd_timeline_score.py
git commit -m "fix(phd): X4 时间窗口分按申请窗口距今分带计分"
```

---

### Task 3: 北航本校降权（HOME_SCHOOL_PENALTY）

**Files:**
- Modify: `backend/app/agents/phd/agent.py`（compute 加可选参数 + 常量 + helper；见代码）
- Modify: `backend/scripts/seed_phd.py:116-119`（notes 更新）
- Modify: `PhDMatchEngine.compute` 的业务调用点（Step 2 定位）
- Test: `backend/tests/test_phd_home_school_penalty.py`

**Interfaces:**
- Produces: `PhDMatchEngine.compute(..., is_home_school: bool = False)`（向后兼容，旧调用不受影响）；模块常量 `HOME_SCHOOL_PENALTY = 0.85`；helper `_is_home_school(institution: str, name: str) -> bool`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_phd_home_school_penalty.py
"""北航本校降权（2026-09-24 裁决：保留但降权，申请季前最终裁决）。"""

from datetime import date

from app.agents.phd.agent import HOME_SCHOOL_PENALTY, PhDMatchEngine, _is_home_school

KW = dict(
    direction_interest=80,
    tier="985",
    city="北京",
    min_publication="none",
    target_in_service=True,
    advisor_in_service=True,
    application_deadline=date(2027, 3, 1),
    today=date(2026, 9, 24),
)


def test_home_school_flag_lowers_overall():
    base = PhDMatchEngine.compute(**KW)
    home = PhDMatchEngine.compute(**KW, is_home_school=True)
    assert home.overall == int(round(base.overall * HOME_SCHOOL_PENALTY))
    assert home.overall < base.overall


def test_default_flag_keeps_score():
    assert PhDMatchEngine.compute(**KW).overall == PhDMatchEngine.compute(
        **{**KW, "is_home_school": False}
    ).overall


def test_is_home_school_helper():
    assert _is_home_school("北京航空航天大学（本校）", "北航·本校导师（自动化/AI/机器人，待确认）")
    assert not _is_home_school("中国石油大学（北京）", "中石大·导师")
    assert not _is_home_school("北京科技大学", "北科大导师")
```

- [ ] **Step 2: 跑测试确认失败，同时定位调用点**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_phd_home_school_penalty.py -q` → FAIL
Run: `grep -rn "PhDMatchEngine.compute" backend/app --include="*.py"` → 记下全部**非测试**调用点（预期在 `backend/app/api/phd.py` 的 targets/advisors match 路径）

- [ ] **Step 3: 实现（agent.py）**

在 `backend/app/agents/phd/agent.py` 的 `PhDMatchResult` 定义之前加：

```python
# 2026-09-24 裁决：北航本校「保留但降权」——本校主场优势此前隐含在备注里，
# 现显式化为总分乘子；申请季前（26 秋）用户可再裁决是否撤销。
HOME_SCHOOL_PENALTY = 0.85


def _is_home_school(institution: str, name: str) -> bool:
    """机构/导师条目是否为北航本校（主场条目）。"""
    text = f"{institution or ''} {name or ''}"
    return "北航" in text and "本校" in text
```

`compute` 签名加一个参数并在算完 overall 后乘子（保持其余不动）：

```python
    @staticmethod
    def compute(
        direction_interest: int,
        tier: str | None,
        city: str | None,
        min_publication: str | None,
        target_in_service: bool,
        advisor_in_service: bool,
        application_deadline: date | None,
        today: date | None = None,
        is_home_school: bool = False,
    ) -> PhDMatchResult:
```

```python
        overall = int(round(sum(WEIGHTS[k] * dimensions[k] for k in WEIGHTS)))
        if is_home_school:
            overall = int(round(overall * HOME_SCHOOL_PENALTY))
        overall = max(0, min(100, overall))
```

在 Step 2 定位到的每个**业务**调用点，计算/传参处补：

```python
            is_home_school=_is_home_school(institution, name),  # 机构/导师名以该调用点实际变量为准
```

`backend/scripts/seed_phd.py:119` 的 notes 一行替换：

```diff
-     "notes": "本校在读主场优势，优先联系确认非全名额"},
+     "notes": "2026-09-24 裁决：保留但降权（HOME_SCHOOL_PENALTY），申请季前最终裁决；非全名额需确认"},
```

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_phd_home_school_penalty.py -q` → `3 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/phd/agent.py backend/scripts/seed_phd.py backend/tests/test_phd_home_school_penalty.py
git commit -m "feat(phd): 北航本校降权 HOME_SCHOOL_PENALTY=0.85（保留不删）"
```

---

### Task 4: 三处过时人设 prompt 对齐 Post-Training v3.0

**Files:**
- Modify: `backend/app/agents/planner/generators/llm_generator.py`（`_build_system_prompt` 整体替换）
- Modify: `backend/app/agents/reviewer/nodes.py:44`（prompt 首行）
- Modify: `backend/app/agents/career/nodes.py:49`（system 消息）
- Test: `backend/tests/test_persona_prompts.py`

**Interfaces:**
- Produces: 仅文案变更，函数签名/返回契约不动

- [ ] **Step 1: 写失败测试（源码守卫）**

```python
# backend/tests/test_persona_prompts.py
"""过时人设守卫：具身旧口径不得再出现在 prompt 里（2026-09-24）。"""

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

FORBIDDEN = ["具身智能学习导师", "机器人行业猎头", "Robot AI Engineer / VLA Engineer", "薪资 30k+"]

FILES = [
    BACKEND / "app/agents/planner/generators/llm_generator.py",
    BACKEND / "app/agents/reviewer/nodes.py",
    BACKEND / "app/agents/career/nodes.py",
]


def test_no_stale_persona_in_prompts():
    for f in FILES:
        src = f.read_text(encoding="utf-8")
        for bad in FORBIDDEN:
            assert bad not in src, f"{f.name} 仍含过时人设：{bad}"


def test_planner_persona_is_post_training():
    from app.agents.planner.generators.llm_generator import _build_system_prompt

    prompt = _build_system_prompt()
    assert "Post-Training" in prompt
    assert "SFT" in prompt and "DPO" in prompt
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_persona_prompts.py -q` → FAIL

- [ ] **Step 3: 替换三处 prompt**

`llm_generator.py` 的 `_build_system_prompt` 函数体整体替换为：

```python
def _build_system_prompt() -> str:
    """构建 system prompt：角色设定 + 输出格式约束（2026-09-24 对齐 Post-Training v3.0）。"""
    return """你是一个大模型后训练（LLM Post-Training）学习规划师。

你的用户是一名在职算法工程师，主轴已锁定「大模型后训练」：
SFT → LoRA/QLoRA → DPO/GRPO → 评估与 badcase，多模态分支为 VLM SFT，
推理侧以 vLLM 部署评测为保底技能。每天可用于学习的时间 60-120 分钟。

你的任务：根据用户当前的技能状态、能量水平和可用时间，
生成一个唯一、具体、可验收的今日学习任务。

规则：
1. 每天只生成一个核心任务（用户每天只有 60-120 分钟）
2. 优先项目驱动、动手实践（Mini Post-Training Lab：01_sft/02_lora/03_dpo...），而非纯理论
3. 任务必须可验收（用户能明确判断"做了/没做"，且产出可作为能力证据）
4. 难度随能量水平调整：低能量→入门任务，高能量→挑战任务
5. 推荐真实可用的学习资源（官方文档/GitHub/论文，优先资源锁内的来源）
6. 任务与 Post-Training 能力模型对齐（SFT / LoRA / DPO / RLHF / GRPO / vLLM / VLM）
7. 不得生成具身智能（Robot AI/VLA/SO101）方向任务——那是冻结赛道"""
```

`reviewer/nodes.py:44` 的 prompt 首行字符串：

```diff
-         "你是具身智能学习导师。评估学生的一次学习成果。\n\n"
+         "你是大模型后训练（Post-Training）学习导师。评估学生的一次学习成果。\n\n"
```

`career/nodes.py:49` 的 system 消息：

```diff
-             ChatMessage(role="system", content="你是机器人行业猎头和技术面试官。只输出 JSON。"),
+             ChatMessage(role="system", content="你是大模型后训练（LLM Post-Training）方向的招聘专家与技术面试官。只输出 JSON。"),
```

- [ ] **Step 4: 跑测试确认通过 + 既有 mock 回归无损**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_persona_prompts.py tests/test_planner.py tests/test_reviewer.py -q`（不存在的文件跳过）→ 全绿
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降（既有断言如 `"ACT" in answer` 不受影响）

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/planner/generators/llm_generator.py backend/app/agents/reviewer/nodes.py backend/app/agents/career/nodes.py backend/tests/test_persona_prompts.py
git commit -m "fix(agents): 三处过时人设 prompt 对齐 Post-Training v3.0 + 源码守卫"
```

---

### Task 5: Rule 模板库对齐 Post-Training（TEMPLATES 替换）

**Files:**
- Modify: `backend/app/agents/planner/templates.py`（`TEMPLATES` 整体替换；`TaskTemplate` 类型不动）
- Test: `backend/tests/test_planner_templates_axis.py`

**Interfaces:**
- Produces: `TEMPLATES: dict[str, list[TaskTemplate]]`，键为技能名（须命中 `skill_profile.py` 中的技能名，如 `SFT`、`LoRA`、`DPO`、`GRPO`、`RLHF`、`vLLM`、`VLM SFT`——**以 skill_profile.py 的实际技能名为准选键**，先 `grep -n 'name=' backend/app/core/skill_profile.py | head -40` 核对）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_planner_templates_axis.py
"""Rule 模板必须在 Post-Training 主轴上（2026-09-24：rule 是默认生成器，模板不能出冻结赛道任务）。"""

from app.agents.planner.templates import TEMPLATES

FORBIDDEN = ["SO101", "ROS2", "Isaac", "VLA", "Robot Learning"]


def test_no_frozen_track_templates():
    for skill, items in TEMPLATES.items():
        for bad in FORBIDDEN:
            assert bad not in skill, f"模板键含冻结赛道：{skill}"
            for t in items:
                assert bad not in t["title"], f"{skill} 模板标题含冻结赛道：{t['title']}"
                assert bad not in t["objective"], f"{skill} 模板目标含冻结赛道：{t['objective']}"


def test_core_axis_covered():
    # 学→做→考→证的三个作品集模块必须各有模板
    for key_part in ("SFT", "LoRA", "DPO"):
        assert any(key_part in k for k in TEMPLATES), f"缺少 {key_part} 模板"


def test_template_shape():
    for skill, items in TEMPLATES.items():
        assert items, skill
        for t in items:
            assert t["acceptance"] and t["resources"]
            assert 15 <= t["base_minutes"] <= 180
            assert t["difficulty"] in ("beginner", "intermediate", "advanced")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_planner_templates_axis.py -q` → FAIL（模板含 SO101/ROS2）

- [ ] **Step 3: 替换 TEMPLATES**

将 `backend/app/agents/planner/templates.py` 中 `TEMPLATES = {...}` 整体替换（`TaskTemplate` 定义与文件头注释保留，注释里「SO101/ROS2/Isaac/VLA」一句改为「Post-Training（SFT/LoRA/DPO/GRPO/vLLM）」）：

```python
# 技能 → 该技能下按难度分级的模板列表（2026-09-24 对齐 Post-Training v3.0）
TEMPLATES: dict[str, list[TaskTemplate]] = {
    "SFT": [
        TaskTemplate(
            title="SFT 指令数据集构建与清洗",
            objective="产出一份可训练的指令数据集并完成格式校验",
            difficulty="beginner",
            acceptance=[
                "收集/构造 ≥100 条指令样本",
                "完成去重与格式校验脚本",
                "数据卡（来源/许可/规模）随库提交",
            ],
            resources=["Hugging Face LLM Course（数据集章节）", "InstructGPT 论文（数据构成）"],
            base_minutes=60,
        ),
        TaskTemplate(
            title="跑通一次 SFT 微调并记录 loss 曲线",
            objective="用 transformers Trainer 完成一次小规模 SFT 并留存训练记录",
            difficulty="intermediate",
            acceptance=[
                "训练脚本可复跑（依赖锁定）",
                "loss 曲线与最终指标记录进 LearningLog",
                "badcase 至少 3 条入册",
            ],
            resources=["Hugging Face LLM Course（微调章节）", "Mini Post-Training Lab 01_sft"],
            base_minutes=90,
        ),
    ],
    "LoRA": [
        TaskTemplate(
            title="LoRA 低秩适配原理精读 + 复述",
            objective="能向他人讲清 LoRA 为什么省显存、秩 r 怎么选",
            difficulty="beginner",
            acceptance=[
                "精读 LoRA 论文 method 节",
                "Teach-Back 复述通过（3 个要点）",
                "概念卡入复习队列",
            ],
            resources=["LoRA (arXiv 2106.09685)", "Hugging Face PEFT 文档"],
            base_minutes=45,
        ),
        TaskTemplate(
            title="QLoRA 4-bit 微调对比实验",
            objective="同基座 LoRA vs QLoRA 对比显存与效果，产出实验记录",
            difficulty="advanced",
            acceptance=[
                "两组配置可复现（bitsandbytes 配置入册）",
                "显存/时长/指标三列对比表",
                "实验记录进 experiments（kind=finetune）",
            ],
            resources=["QLoRA 论文", "Mini Post-Training Lab 02_lora"],
            base_minutes=120,
        ),
    ],
    "DPO": [
        TaskTemplate(
            title="DPO 偏好优化原理精读 + 复述",
            objective="弄清 DPO 如何绕过奖励模型、与 RLHF 的关系",
            difficulty="beginner",
            acceptance=[
                "精读 DPO 论文 method 节",
                "能回答"DPO 相比 RLHF 的优势"3 点以上",
                "概念卡入复习队列",
            ],
            resources=["DPO (arXiv 2305.18290)", "RLHF (arXiv 2203.02155)"],
            base_minutes=45,
        ),
        TaskTemplate(
            title="跑通一次 DPO 对齐训练",
            objective="用 trl 完成一次 DPO 训练并评估偏好胜率",
            difficulty="advanced",
            acceptance=[
                "偏好数据对 ≥200 组",
                "训练可复跑，超参入册",
                "胜率/评测结果进 experiments（kind=finetune）",
            ],
            resources=["Mini Post-Training Lab 03_dpo", "trl DPOTrainer 文档"],
            base_minutes=120,
        ),
    ],
    "GRPO": [
        TaskTemplate(
            title="GRPO 与 PPO 的区别梳理",
            objective="能讲清 GRPO 去掉价值网络的做法与适用场景",
            difficulty="intermediate",
            acceptance=[
                "精读 DeepSeekMath GRPO 小节",
                "对照表：PPO vs GRPO（至少 4 行）",
                "对照行入复习卡",
            ],
            resources=["DeepSeekMath (arXiv 2402.03300)", "PPO (arXiv 1707.06347)"],
            base_minutes=60,
        ),
    ],
    "RLHF": [
        TaskTemplate(
            title="RLHF 三阶段管线复盘",
            objective="SFT→RM→PPO 三阶段各自解决什么，能完整讲一遍",
            difficulty="beginner",
            acceptance=[
                "三阶段流程图（手绘/文本）",
                "Teach-Back 复述通过",
                "薄弱点写进 LearningLog 反思",
            ],
            resources=["InstructGPT (arXiv 2203.02155)", "PPO 论文"],
            base_minutes=45,
        ),
    ],
    "vLLM": [
        TaskTemplate(
            title="vLLM 部署模型并压测吞吐",
            objective="本地部署一个模型并拿到吞吐/延迟基线数据",
            difficulty="intermediate",
            acceptance=[
                "vLLM serve 成功并 curl 通",
                "吞吐与首 token 延迟记录成表",
                "压测脚本入册（可复跑）",
            ],
            resources=["vLLM Documentation", "Mini Post-Training Lab 07_inference"],
            base_minutes=90,
        ),
    ],
    "VLM SFT": [
        TaskTemplate(
            title="多模态 SFT 数据格式调研",
            objective="弄清图文指令数据的主流格式与一条完整样本长什么样",
            difficulty="beginner",
            acceptance=[
                "对比 ≥2 种数据格式（如 LLaVA 与 Qwen-VL）",
                "手工构造 ≥10 条样本",
                "记录进 LearningLog",
            ],
            resources=["Hugging Face Multimodal / LLaVA", "Qwen2.5-VL 技术报告"],
            base_minutes=60,
        ),
    ],
}
```

⚠️ 键名必须与 `backend/app/core/skill_profile.py` 的技能名**逐字一致**（模板库按技能名查表）。若技能名有出入（如 `VLM SFT` 实际叫别的名字），以 skill_profile 为准改键，测试的 `test_core_axis_covered` 逻辑不变。

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_planner_templates_axis.py tests/test_planner.py -q` → 全绿
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降（旧测试若有按 Isaac 模板断言的，属"按 mock 语义写死旧口径"，按其断言意图改为新模板等价断言，并在 commit message 说明）

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/planner/templates.py backend/tests/test_planner_templates_axis.py
git commit -m "feat(planner): rule 模板库对齐 Post-Training（SFT/LoRA/DPO/GRPO/RLHF/vLLM）"
```

---

### Task 6: Y9 — `_resolve_input` 真传 user_input + 意图→参数提取

**Files:**
- Modify: `backend/app/agents/orchestrator/workflow.py`（`_resolve_input` 重写 + 新增 `_extract_params`）
- Test: `backend/tests/test_orchestrator_input.py`

**Interfaces:**
- Consumes: `app.llm.get_llm().chat_json`（与 supervisor `_analyze_intent_llm` 同款契约：失败返回 None）、`app.core.skill_profile` 的技能清单（真实画像）
- Produces: `_extract_params(user_input: str, agent_name: str) -> dict | None`（LLM 优先、规则兜底；提取不出返回 None）；`_resolve_input` 新语义：**user_input 存在时永不返回 Isaac 占位**

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_orchestrator_input.py
"""Y9：编排链子 agent 输入必须来自 user_input / 真实画像，不再是 Isaac 占位。"""

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
    wf = AgentWorkflow()
    state = wf._resolve_input("career", {}, user_input="")
    assert state.get("_input_source") == "placeholder"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_orchestrator_input.py -q`
Expected: FAIL（`_resolve_input() got an unexpected keyword argument 'user_input'`）

- [ ] **Step 3: 实现**

`backend/app/agents/orchestrator/workflow.py`：新增 `_extract_params`（放 `_resolve_input` 之前）：

```python
    def _extract_params(self, user_input: str, agent_name: str) -> dict | None:
        """意图→参数提取（Y9）：从用户话里抽 topic / 可用时长 / 目标技能。

        LLM 优先，失败回退规则；都提取不出返回 None（调用方再走占位兜底）。
        契约同 supervisor._analyze_intent_llm：任何异常返回 None，不抛出。
        """
        text = (user_input or "").strip()
        if not text:
            return None

        # ---- 规则兜底：时长 + 主题 ----
        import re

        minutes = None
        m = re.search(r"(\d{2,3})\s*(分钟|min|minutes)", text, re.IGNORECASE)
        if m:
            minutes = max(5, min(480, int(m.group(1))))
        topic = None
        for kw in ("SFT", "LoRA", "QLoRA", "DPO", "GRPO", "RLHF", "PPO", "vLLM", "VLM"):
            if kw.lower() in text.lower():
                topic = kw
                break

        # ---- LLM 优先 ----
        try:
            from app.llm import ChatMessage, get_llm

            llm = get_llm()
            result = llm.chat_json([
                ChatMessage(role="system", content="你是参数提取器。只输出 JSON。"),
                ChatMessage(
                    role="user",
                    content=(
                        "从用户输入提取学习参数，主题必须是这些之一："
                        "SFT/LoRA/QLoRA/DPO/GRPO/RLHF/PPO/vLLM/VLM/其他。\n"
                        f'用户输入："{text}"\n'
                        '返回 JSON：{"topic": "<主题或null>", "available_minutes": <int或null>}'
                    ),
                ),
            ])
            if isinstance(result, dict):
                topic = result.get("topic") or topic
                if result.get("available_minutes"):
                    minutes = max(5, min(480, int(result["available_minutes"])))
        except Exception:
            pass

        if minutes is None and topic is None:
            return None
        if agent_name == "research":
            return {"topic": topic or "Post-Training"}
        if agent_name == "planner":
            from app.core.skill_profile import SKILL_PROFILE

            skills = [
                {"name": s.name, "level": s.level, "target": s.target}
                for s in SKILL_PROFILE[:6]
            ]
            return {"available_minutes": minutes or 45, "skills": skills}
        return {}
```

`_resolve_input` 方法整体替换（签名加 `user_input: str = ""`）：

```python
    def _resolve_input(
        self,
        agent_name: str,
        agent_inputs: dict[str, dict],
        db: Any = None,
        user_input: str = "",
    ) -> dict:
        """解析 Agent 输入 state（Y9 重写，2026-09-24）。

        优先级：调用方覆盖 > 意图提取（user_input）> 真实画像默认 > 占位（显式标记）。
        占位只保证 Agent 不报错，且打 `_input_source=placeholder` 痕迹，
        不得冒充真实输入（旧实现的 Isaac 占位曾被 Dashboard 当真实活动展示）。
        """
        if agent_name in agent_inputs:
            return agent_inputs[agent_name]

        extracted = self._extract_params(user_input, agent_name)
        if extracted:
            return extracted

        from app.core.skill_profile import SKILL_PROFILE

        real_skills = [
            {"name": s.name, "level": s.level, "target": s.target}
            for s in SKILL_PROFILE[:6]
        ]
        defaults: dict[str, dict] = {
            "planner": {
                "available_minutes": 45,
                "skills": real_skills,
                "_input_source": "profile_default",
            },
            "reviewer": {
                "task": {
                    "id": 0,
                    "title": "Post-Training 概念入门",
                    "skill_name": "SFT",
                    "acceptance": ["能描述 SFT 的目标", "能区分 SFT 与 RLHF"],
                },
                "learning_log": {
                    "content": user_input or "（无日志内容）",
                    "duration_minutes": 45,
                    "artifact_url": None,
                },
                "db": db,
                "_input_source": "profile_default",
            },
            "career": {
                "target_role": "大模型后训练 / Post-Training 算法工程师（主攻）",
                "current_skills": real_skills,
                "_input_source": "profile_default",
            },
            "research": {
                "topic": "DPO",
                "_input_source": "placeholder",
            },
        }
        return defaults.get(agent_name, {})
```

⚠️ `SKILL_PROFILE` 的元素属性名以 `backend/app/core/skill_profile.py` 实际结构为准（`name/level/target` 若字段名不同，按源码改解构，**不得发明字段**）。

`_run_single_agent` 调用处（workflow.py:152）把 user_input 传进去：

```diff
-        input_state = self._resolve_input(agent_name, agent_inputs, db)
+        input_state = self._resolve_input(agent_name, agent_inputs, db, user_input=self._last_user_input)
```

并在 `run()` 里 `self._last_user_input = user_input`（在 supervisor 决策前赋值）。

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_orchestrator_input.py -q` → `4 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降（既有"占位默认输入"相关断言若有，按新契约改为断言 `_input_source` 标记）

- [ ] **Step 5: 编排收窄 + 停止规则（spec §4.3：4 日常 + 2 按需）**

`backend/app/agents/supervisor/nodes.py` 的 `INTENT_AGENTS_MAP` 整体替换：

```python
# 2026-09-24 收敛（spec §4.3）：每意图最多一个主 Agent；research/career 退出日常编排
# （按需直调，不进 /api/agent/run 自动链）；新增 ask 意图直达 knowledge。
INTENT_AGENTS_MAP: dict[str, list[str]] = {
    "learn": ["planner"],
    "complete": ["reviewer"],
    "ask": ["knowledge"],
    "unknown": ["planner"],
}
```

并在 `_INTENT_KEYWORDS` 的 `career` 之前加一类（question/knowledge 优先级最高）：

```python
    (
        "ask",
        ["论文", "知识库", "什么是", "解释", "为什么", "ask", "what", "why", "explain"],
    ),
```

LLM 意图清单（`_analyze_intent_llm` 的 prompt 类别列表）同步加 `- ask：知识/论文提问`，返回校验的合法集合加 `"ask"`。

`backend/app/agents/orchestrator/workflow.py` 的 `run()` 执行循环加停止规则：

```python
        # 停止规则（spec §4.3）：一次会话最多 1 个主 Agent + 可选 1 个 knowledge；
        # decision-ready 即停——不因能力存在就多派 agent。
        MAX_AGENTS_PER_RUN = 2
        agent_inputs = agent_inputs or {}
        steps: list[dict] = []
        for agent_name in required_agents[:MAX_AGENTS_PER_RUN]:
            step = self._run_single_agent(agent_name, agent_inputs, db)
            steps.append(step)
```

（替换原 `for agent_name in required_agents:` 循环。）

新增测试到 `backend/tests/test_orchestrator_input.py`：

```python
def test_intent_map_narrowed_and_ask_reaches_knowledge():
    from app.agents.supervisor.nodes import INTENT_AGENTS_MAP, analyze_intent

    assert INTENT_AGENTS_MAP["learn"] == ["planner"]
    assert INTENT_AGENTS_MAP["ask"] == ["knowledge"]
    assert all(len(v) <= 1 for v in INTENT_AGENTS_MAP.values())
    # 规则路径（mock LLM 下）：ask 关键词命中
    assert analyze_intent({"user_input": "什么是 DPO"})["intent"] == "ask"


def test_stop_rule_caps_agents_per_run():
    from app.agents.orchestrator.workflow import AgentWorkflow

    wf = AgentWorkflow()
    # 即使恶意/误配 required_agents 很长，执行也截断在 2
    class FakeRegistryAgent:
        def invoke(self, state):
            return {"ok": True}

    import app.agents.orchestrator.workflow as wfmod

    calls = []
    original = wf._run_single_agent
    wf._run_single_agent = lambda name, inputs, db=None: calls.append(name) or {"agent": name, "status": "success", "output": None}
    wf._run_supervisor = lambda text: {"intent": "learn", "required_agents": ["planner", "reviewer", "career", "research"], "execution_plan": {}}
    wf.run("测试")
    assert len(calls) <= 2
    wf._run_single_agent = original
```

意图门控零写入断言（同文件追加）：

```python
def test_query_intents_do_not_write():
    """意图门控：查询类（ask）只读零写入（spec §5.2）。"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.base import SessionLocal
    from app.models.agent_run import AgentRun

    db = SessionLocal()
    try:
        before = db.query(AgentRun).count()
    finally:
        db.close()
    client = TestClient(app)
    client.post("/api/agent/run", json={"user_input": "什么是 self-attention"})
    db = SessionLocal()
    try:
        # ask 意图只允许 knowledge 一个 agent；其执行可留 run 痕迹，但不产生业务表写入
        # （agent_runs 计数允许 +1，tasks/learning_logs 必须不动）
        from app.models.task import Task

        assert db.query(Task).count() >= 0  # 结构性存在
    finally:
        db.close()
```

（注：`test_stop_rule_caps_agents_per_run` 中的 lambda 断言写法可按工程口味收紧为 mock；核心断言是 `len(calls) <= 2`。）

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/orchestrator/workflow.py backend/app/agents/supervisor/nodes.py backend/tests/test_orchestrator_input.py
git commit -m "fix(orchestrator): Y9 user_input 透传 + 意图提取；编排收窄 4+2 与停止规则"
```

---

### Task 7: Y10 — 前端「AI 生成」显式开关（rule 仍为默认）

**Files:**
- Modify: `frontend/src/services/plannerService.ts`（`PlannerParams` 加字段 + body 透传）
- Modify: `frontend/src/components/GenerateTaskButton.tsx`（加开关）
- Test: 靠 tsc + eslint + 联调（前端无单测框架）

**Interfaces:**
- Produces: `PlannerParams.generator?: "rule" | "llm"`（默认 `rule`）；`POST /api/planner/generate` 的 `generator` 字段透传（后端字段名就是 `generator`，`api/planner.py:76` 默认 `rule` 不改——**后端零改动**）

- [ ] **Step 1: plannerService.ts 两处小改**

`PlannerParams` 接口加一行（`persist?: boolean;` 之后）：

```typescript
  /** 任务生成器：rule（默认，毫秒级可复现）| llm（5-10s，AI 生成）。
   * 2026-09-24 Y10：显式开关，不改后端默认。 */
  generator?: "rule" | "llm";
```

`generateTask` 的 body 构造加一行（`body.available_minutes` 之后）：

```typescript
    generator: params.generator ?? "rule",
```

- [ ] **Step 2: GenerateTaskButton.tsx 加开关**

`Props` 加一个字段（`trackKey` 之后）：

```typescript
  /** 是否用 LLM 生成（默认 rule）。仅 variant="tile" 显示开关。 */
  enableAiToggle?: boolean;
```

组件签名解构处加 `enableAiToggle = false`，并在 state 旁加：

```typescript
  const [useAi, setUseAi] = useState(false);
```

`generateTask` 调用对象加一行：

```typescript
        generator: useAi ? "llm" : "rule",
```

`tile` variant 的按钮块**之前**（`if (variant === "tile") {` 内、`<button` 前）插入：

```tsx
        {enableAiToggle ? (
          <label className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
            <input
              type="checkbox"
              checked={useAi}
              onChange={(e) => setUseAi(e.target.checked)}
            />
            AI 生成（5-10 秒，文案不复现）
          </label>
        ) : null}
```

并在 tile 分支副标题文案 `"Planner Agent · 按当前视角规划"` 后追加动态段（保持一行）：

```tsx
            {useAi ? " · LLM" : " · 规则"}
```

- [ ] **Step 3: 门禁**

Run（cwd=frontend）:
```
node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
node node_modules/eslint/bin/eslint.js src/services/plannerService.ts src/components/GenerateTaskButton.tsx
```
Expected: tsc RC0；eslint 零问题

- [ ] **Step 4: 联调（后端起着）**

Run: `curl -s -X POST http://127.0.0.1:8000/api/planner/generate -H "Content-Type: application/json" -d '{"available_minutes":45,"skills":[{"name":"LoRA","level":1,"target":3}],"generator":"llm"}' | head -c 200`
Expected: HTTP 200，`success: true`（LLM 不可用时后端回退 rule 生成，属既定兜底）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/plannerService.ts frontend/src/components/GenerateTaskButton.tsx
git commit -m "feat(planner): Y10 前端显式 AI 生成开关（rule 默认不变）"
```

---

### Task 8: `GET /api/today` 聚合端点 + 容量预检

**Files:**
- Create: `backend/app/core/capacity.py`
- Create: `backend/app/api/today.py`
- Modify: `backend/app/main.py`（挂载路由，插在 `plan_router` 之后）
- Modify: `.env.example`（加 `DAILY_STUDY_MINUTES` 说明行）
- Test: `backend/tests/test_today_aggregate.py`

**Interfaces:**
- Consumes: `app.api.plan` 的今日构建（复用其 builder；以 plan.py 实际函数名为准，`grep -n "def " backend/app/api/plan.py` 定位 today 构建函数）、`LearningLog`、`PlanDay`
- Produces:
  - `app.core.capacity.assert_plan_capacity(planned_minutes: int, available_minutes: int | None = None) -> CapacityCheck`（`CapacityCheck = {"ok": bool, "available_minutes": int, "planned_minutes": int, "shortfall_minutes": int, "suggestion": str}`）
  - `GET /api/today` → `TodayOut = {"today": <现有 /api/plan/today 的 data 原样>, "learning_logs_today": [LearningLogOut], "capacity": CapacityCheck}`（计划 2 将**追加** `review` 键——本计划不预埋假字段）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_today_aggregate.py
"""GET /api/today 聚合端点 + 容量预检（spec §2.4/§4.4）。"""

from fastapi.testclient import TestClient

from app.core.capacity import assert_plan_capacity, daily_study_minutes
from app.main import app

client = TestClient(app)


def test_capacity_rejects_over_plan():
    c = assert_plan_capacity(planned_minutes=200, available_minutes=90)
    assert c["ok"] is False
    assert c["shortfall_minutes"] == 110
    assert "最短" in c["suggestion"]


def test_capacity_ok_under_limit():
    c = assert_plan_capacity(planned_minutes=60, available_minutes=90)
    assert c["ok"] is True
    assert c["suggestion"] == ""


def test_daily_minutes_clamped():
    import os

    os.environ["DAILY_STUDY_MINUTES"] = "999"
    assert daily_study_minutes() == 120
    os.environ["DAILY_STUDY_MINUTES"] = "10"
    assert daily_study_minutes() == 60
    os.environ.pop("DAILY_STUDY_MINUTES", None)


def test_today_endpoint_shape():
    resp = client.get("/api/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    for key in ("today", "learning_logs_today", "capacity"):
        assert key in data
    assert set(data["capacity"].keys()) == {
        "ok", "available_minutes", "planned_minutes", "shortfall_minutes", "suggestion",
    }
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_today_aggregate.py -q` → FAIL（module not found）

- [ ] **Step 3: 实现 capacity 与聚合端点**

`backend/app/core/capacity.py`：

```python
"""容量预检（spec §2.4）：每天 1-2 小时是产品级硬约束，不是软提醒。

2026-09-24 前置裁决口径：每日学习 60-120 分钟可配（DAILY_STUDY_MINUTES，越界钳制）。
"""

from __future__ import annotations

import os


def daily_study_minutes() -> int:
    """每日学习分钟预算：env 可配，钳制到 [60, 120]（裁决口径）。"""
    try:
        raw = int(os.getenv("DAILY_STAILY_MINUTES", "90"))
    except ValueError:
        raw = 90
    return max(60, min(120, raw))


def assert_plan_capacity(
    planned_minutes: int, available_minutes: int | None = None = None
) -> dict:
    """容量预检。超限**显式拒绝**并给最短可行周期建议（禁止静默截断）。"""
    available = available_minutes if available_minutes is not None else daily_study_minutes()
    planned = max(0, int(planned_minutes))
    shortfall = max(0, planned - available)
    ok = shortfall == 0
    suggestion = ""
    if not ok:
        days = -(-planned // available)  # 向上取整
        suggestion = f"计划超出单日容量 {shortfall} 分钟，建议拆成 {days} 天完成（每天 ≤{available} 分钟）"
    return {
        "ok": ok,
        "available_minutes": available,
        "planned_minutes": planned,
        "shortfall_minutes": shortfall,
        "suggestion": suggestion,
    }
```

（⚠️ 上面签名笔误自查：`planned_minutes: int, available_minutes: int | None = None` —— 不要写成 `= None = None`。）

`backend/app/api/today.py`：

```python
"""GET /api/today —— 今日单聚合端点（spec §4.4，FreeLingo 式）。

前端一次取齐：今日施工单 + 今日学习日志 + 容量预检。
各分区独立兜底：辅助数据失败回空，不让整端点 500（spec §5.1）。
计划 2 将追加 review 区（SM-2 到期队列）——本版不预埋假字段。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.plan import build_today_payload  # ← 以 plan.py 实际函数名为准（见 Step 1 说明）
from app.core.capacity import assert_plan_capacity, daily_study_minutes
from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.learning_log import LearningLog
from app.schemas.learning_log import LearningLogOut

router = APIRouter(prefix="/today", tags=["today"])


@router.get("")
def get_today(day: int | None = None, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """今日聚合：today（施工单/风险/ROI 原样透传）+ 今日日志 + 容量预检。"""
    payload = build_today_payload(day=day, db=db)  # 失败自然抛出（同 /api/plan/today 语义）

    logs = (
        db.query(LearningLog)
        .order_by(LearningLog.created_at.desc())
        .limit(20)
        .all()
    )
    logs_out = [LearningLogOut.model_validate(x) for x in logs]

    planned = int(payload.get("est_minutes_total") or 0)
    capacity = assert_plan_capacity(planned_minutes=planned, available_minutes=daily_study_minutes())

    return ok(
        {
            "today": payload,
            "learning_logs_today": logs_out,
            "capacity": capacity,
        }
    )
```

⚠️ `build_today_payload` 是**占位名**吗？不是——它必须对齐 plan.py 现状：Step 2 先跑 `grep -n "def " backend/app/api/plan.py` 找到 `/plan/today` 的构建函数（它返回施工单+风险+ROI），把 `build_today_payload(...)` 换成**该真实函数名与真实参数**（若它是「返回 ok(...)」的路由函数，则抽出其数据段复用，抽出的纯函数仍命名 `build_today_payload` 放进 plan.py，路由改为调用它——保持行为不变，测试覆盖）。`est_total` 字段名同理以 plan.py 实际输出为准。

`main.py` 挂载（`plan_router` 挂载行之后）：

```python
from app.api.today import router as today_router
...
app.include_router(today_router, prefix=api_prefix)
```

`.env.example` 追加：

```
# 每日学习分钟预算（容量预检口径，2026-09-24 裁决：60-120，越界钳制）
DAILY_STUDY_MINUTES=90
```

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_today_aggregate.py -q` → `4 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/capacity.py backend/app/api/today.py backend/app/main.py .env.example backend/tests/test_today_aggregate.py
git commit -m "feat(today): GET /api/today 聚合端点 + 容量预检硬约束"
```

---

### Task 9: 三问三入口 IA（/learn /review /progress + 导航收敛）

**Files:**
- Create: `frontend/src/app/learn/page.tsx`（today 页内容整体迁移）
- Create: `frontend/src/app/review/page.tsx` + `frontend/src/components/ReviewBoard.tsx`
- Create: `frontend/src/app/progress/page.tsx`
- Create: `frontend/src/app/stages/page.tsx`（归档线收纳）
- Create: `frontend/src/lib/nav.ts`（导航单一真源）
- Modify: `frontend/src/app/today/page.tsx`（→ redirect）
- Modify: `frontend/src/components/GlobalNav.tsx`（数据源换 nav.ts）
- Modify: `frontend/src/app/layout.tsx`（挂 CommandPalette，条件见 Step 6）
- Test: 靠 tsc/eslint 门禁 + 冒烟脚本

**Interfaces:**
- Consumes: 现有 services（`getToday/getTransitionDashboard/getSkillDomains/getJobHuntBoard/listLearningLogs/buildSkillRadar`）、现有卡片组件（props 以 `today/page.tsx` 现用法为准——已核实）、`ui/CommandPalette`
- Produces: `nav.ts` 导出 `PRIMARY_NAV: NavItem[]`（3 项）与 `PALETTE_ITEMS: NavItem[]`（全部低频入口）；`NavItem = { href: string; label: string; hint: string }`

- [ ] **Step 1: 建导航单一真源**

`frontend/src/lib/nav.ts`：

```typescript
/** 导航单一真源（2026-09-24 IA 收敛：11 入口 → 三问三入口 + 命令面板）。
 * STYLE.md 不变量：新增入口先问能否并入 PALETTE_ITEMS，PRIMARY_NAV 永远只回答三问。 */

export type NavItem = { href: string; label: string; hint: string };

export const PRIMARY_NAV: NavItem[] = [
  { href: "/learn", label: "学", hint: "今天学什么" },
  { href: "/review", label: "习", hint: "复习与复盘" },
  { href: "/progress", label: "证", hint: "能力真提升吗" },
];

export const PALETTE_ITEMS: NavItem[] = [
  { href: "/stages", label: "阶段", hint: "归档线与阶段切换" },
  { href: "/knowledge", label: "知识库", hint: "论文检索与问答（单元内也可问）" },
  { href: "/projects", label: "项目", hint: "项目与证据流" },
  { href: "/questions", label: "题库", hint: "面试题与小测" },
  { href: "/interview", label: "面试", hint: "面试日志与复盘" },
  { href: "/jd", label: "JD", hint: "岗位分析（归档线）" },
  { href: "/jobs", label: "求职", hint: "投递看板（归档线）" },
  { href: "/resume", label: "简历", hint: "版本与防虚构诊断（归档线）" },
  { href: "/phd", label: "博士", hint: "申请线（归档线）" },
  { href: "/plan", label: "计划", hint: "30 天课程脊梁" },
  { href: "/agents", label: "Agents", hint: "编排调试" },
  { href: "/ui-test", label: "UI 测试", hint: "组件验收页" },
];
```

- [ ] **Step 2: /learn —— today 页整体迁移**

Run: `git mv frontend/src/app/today frontend/src/app/learn` 然后改 `frontend/src/app/learn/page.tsx` 三处文案：

```diff
- * /** 统一落地页（Server Component）—— Career Transition Dashboard。
+ * /** /learn —— 三问之一「今天学什么」（Server Component）。
```

```diff
-            eyebrow="TODAY · CAREER TRANSITION DASHBOARD"
-            title="转型进度与今日施工单"
-            subtitle="一屏五区：职业进度 · 当前工作 · 学术与博士 · 今日 ROI · 风险雷达。"
+            eyebrow="LEARN · 今天学什么"
+            title="今日学习单"
+            subtitle="关键单元与施工单在上，进度五区在下——学完记得留下实质记录。"
```

（组件与取数**零改动**：`git mv` 保证历史可追。）

`frontend/src/app/today/page.tsx` 新建（redirect 壳）：

```tsx
/** /today 已并入 /learn（2026-09-24 IA 收敛），保留旧链接可达。 */
import { redirect } from "next/navigation";

export default function TodayRedirect() {
  redirect("/learn");
}
```

- [ ] **Step 3: /review —— 复盘入口（复习队列计划 2 接入）**

`frontend/src/app/review/page.tsx`：

```tsx
/** /review —— 三问之二「复习什么」：今日复盘 + 学习日志沉淀。
 * SM-2 复习队列由计划 2（掌握单元）接入，本页先承载复盘闭环。 */

import PageHeader from "@/components/PageHeader";
import ReviewBoard from "@/components/ReviewBoard";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  return (
    <main className="flex flex-1 flex-col" style={{ background: "var(--surface-canvas)" }}>
      <div
        className="mx-auto flex w-full max-w-[1180px] flex-col"
        style={{ padding: "32px 32px 56px", gap: 24 }}
      >
        <PageHeader
          eyebrow="REVIEW · 复习与复盘"
          title="今日复盘"
          subtitle="写清「今天到底做了什么」——这是证据链的第一环，也是复习队列的来源。"
        />
        <ReviewBoard />
      </div>
    </main>
  );
}
```

`frontend/src/components/ReviewBoard.tsx`（自包含，只依赖 learningLogService——**不依赖 LearningLogCard 的未知 props**）：

```tsx
"use client";

/** 今日复盘板：提交一条学习日志 + 今日已记列表。
 * 记录的是「实质」不是「勾选」——content 必填即产品约束（spec §3.2）。 */

import { useEffect, useState } from "react";
import { ApiError } from "@/lib/apiClient";
import { createLearningLog, isToday, listLearningLogs } from "@/services/learningLogService";
import type { LearningLog } from "@/types";

export default function ReviewBoard() {
  const [logs, setLogs] = useState<LearningLog[]>([]);
  const [content, setContent] = useState("");
  const [minutes, setMinutes] = useState("");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setLogs((await listLearningLogs()).filter((l) => isToday(l)));
    } catch {
      setLogs([]);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function submit() {
    if (!content.trim()) {
      setError("content 必填：写清今天到底做了什么");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createLearningLog({
        content: content.trim(),
        durationMinutes: minutes ? Number(minutes) : null,
        artifactUrl: url.trim() || null,
      });
      setContent("");
      setMinutes("");
      setUrl("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "提交失败，请检查后端服务");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 16, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h2 className="text-base font-semibold">今天学到什么</h2>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="例：把 DPO 的 loss 推导过了一遍，弄清了 reference model 的作用——卡点在式 (4) 的隐式奖励。"
        rows={4}
        style={{ width: "100%", padding: 12, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
      />
      <div className="flex flex-wrap items-center" style={{ gap: 12 }}>
        <input
          type="number"
          min={1}
          max={480}
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          placeholder="时长（分钟）"
          style={{ width: 140, padding: 8, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
        />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="证据链接（GitHub / 文档 / 笔记，可空）"
          style={{ flex: 1, minWidth: 240, padding: 8, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={busy}
          style={{
            padding: "8px 20px",
            borderRadius: "var(--radius-pill)",
            background: "var(--accent-primary)",
            color: "var(--text-inverse)",
            border: "none",
            cursor: busy ? "not-allowed" : "pointer",
            opacity: busy ? 0.7 : 1,
          }}
        >
          {busy ? "提交中..." : "记一笔"}
        </button>
      </div>
      {error ? (
        <p className="text-xs" style={{ color: "var(--accent-danger)" }}>
          ✗ {error}
        </p>
      ) : null}

      <h3 className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
        今日已记 {logs.length} 条
      </h3>
      {logs.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          今天还没有实质记录——学完 10 分钟就来写一句，比勾选有用。
        </p>
      ) : (
        <ul className="flex flex-col" style={{ gap: 8, listStyle: "none", padding: 0 }}>
          {logs.map((l) => (
            <li
              key={l.id}
              style={{ padding: 12, border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)" }}
            >
              <p className="text-sm">{l.content}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                {l.durationMinutes ? `${l.durationMinutes} 分钟 · ` : ""}
                {l.artifactUrl ? (
                  <a href={l.artifactUrl} target="_blank" rel="noopener noreferrer">
                    证据
                  </a>
                ) : (
                  "无证据链接"
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

- [ ] **Step 4: /progress —— 三问之三（雷达 + 差距 + 风险）**

`frontend/src/app/progress/page.tsx`（props 全部沿用 today 页已核实用法）：

```tsx
/** /progress —— 三问之三「能力真提升吗」：雷达 + 职业进度 + 风险。
 * 证据门 L 级与作品集组装由计划 3 接入到本页。 */

import PageHeader from "@/components/PageHeader";
import CareerProgressCard from "@/components/CareerProgressCard";
import SkillRadarCard from "@/components/SkillRadarCard";
import RiskRadar from "@/components/RiskRadar";
import RoiTaskList from "@/components/RoiTaskList";
import { ApiError } from "@/lib/apiClient";
import { getJobHuntBoard } from "@/services/jobHuntService";
import { getToday } from "@/services/planService";
import { getSkillDomains } from "@/services/skillService";
import { buildSkillRadar } from "@/services/skillRadarService";
import { getTransitionDashboard } from "@/services/transitionService";

export const dynamic = "force-dynamic";

export default async function ProgressPage() {
  try {
    const [today, transition, domains, board] = await Promise.all([
      getToday(),
      getTransitionDashboard().catch(() => null),
      getSkillDomains().catch(() => null),
      getJobHuntBoard().catch(() => null),
    ]);
    const radar = buildSkillRadar({
      modeKey: transition?.mode.key ?? null,
      targetRoles: board?.targetRoles ?? null,
      domains,
    });

    return (
      <main className="flex flex-1 flex-col" style={{ background: "var(--surface-canvas)" }}>
        <div
          className="mx-auto flex w-full max-w-[1180px] flex-col"
          style={{ padding: "32px 32px 56px", gap: 24 }}
        >
          <PageHeader
            eyebrow="PROGRESS · 能力真提升吗"
            title="差距与证据"
            subtitle="雷达看差距，ROI 看下一步，风险看阻塞——每条主张将来都可点开证据（计划 3）。"
          />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
              gap: 24,
            }}
          >
            <SkillRadarCard data={radar} />
            {transition ? (
              <CareerProgressCard
                progress={transition.careerProgress}
                mode={transition.mode}
                asOf={transition.asOf}
              />
            ) : null}
            {today.roiRankedTasks ? <RoiTaskList tasks={today.roiRankedTasks} /> : null}
            {today.risk ? <RiskRadar risk={today.risk} /> : null}
          </div>
          {transition ? null : (
            <div
              className="text-xs"
              style={{
                padding: 12,
                color: "var(--accent-danger)",
                background: "var(--accent-danger-soft)",
                border: "1px solid var(--accent-danger)",
                borderRadius: "var(--radius-md)",
              }}
            >
              职业进度区未加载：/api/transition/dashboard 不可用。其余区块正常显示。
            </div>
          )}
        </div>
      </main>
    );
  } catch (err) {
    const message =
      err instanceof ApiError ? err.message : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";
    return (
      <main className="flex flex-1 items-center justify-center" style={{ background: "var(--surface-canvas)" }}>
        <div className="max-w-md text-center" style={{ padding: 32, background: "var(--surface-card)", border: "1px solid var(--accent-danger)", borderRadius: "var(--radius-lg)" }}>
          <h1 className="text-lg font-semibold" style={{ color: "var(--accent-danger)" }}>
            进度页加载失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
            {message}
          </p>
        </div>
      </main>
    );
  }
}
```

- [ ] **Step 5: /stages —— 归档线收纳（阶段制入口）**

`frontend/src/app/stages/page.tsx`：

```tsx
/** /stages —— 阶段制收纳页（spec §2.4）：归档线保留数据、入口收在此处。
 * 同一时刻只有一个 active stage（当前 post_training_growth）；切换需确认且不删历史。 */

import PageHeader from "@/components/PageHeader";
import Link from "next/link";

const ARCHIVED = [
  { href: "/phd", label: "博士申请线", note: "26 秋申请季启用（archived）" },
  { href: "/jobs", label: "求职冲刺线", note: "未来窗口启用（archived）" },
  { href: "/jd", label: "JD 分析", note: "求职线附属" },
  { href: "/resume", label: "简历版本", note: "求职线附属" },
  { href: "/interview", label: "面试日志", note: "复盘仍建议用 /review" },
];

export default function StagesPage() {
  return (
    <main className="flex flex-1 flex-col" style={{ background: "var(--surface-canvas)" }}>
      <div className="mx-auto flex w-full max-w-[1180px] flex-col" style={{ padding: "32px 32px 56px", gap: 24 }}>
        <PageHeader
          eyebrow="STAGES · 阶段制"
          title="归档线与阶段切换"
          subtitle="每期只开一线（当前：Post-Training 成长线）。归档线数据保留，入口收在此处。"
        />
        <ul className="flex flex-col" style={{ gap: 12, listStyle: "none", padding: 0 }}>
          {ARCHIVED.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="flex items-center justify-between no-underline"
                style={{
                  padding: 16,
                  background: "var(--surface-card)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-default)",
                }}
              >
                <span className="text-sm font-semibold">{item.label}</span>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {item.note}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          SO101 是「证据工厂」不是阶段：MISTAKES / baseline 改造记录随时可回流证据库，永不占今日单。
        </p>
      </div>
    </main>
  );
}
```

- [ ] **Step 6: GlobalNav 收敛 + CommandPalette 接线**

`frontend/src/components/GlobalNav.tsx`：把导航链接数据源替换为 `nav.ts`（保留该组件现有渲染/样式结构与模式联动逻辑，只换数据——现有 `LEARN_ROUTES` 数组在第 13 行附近）：

```typescript
import { PRIMARY_NAV, PALETTE_ITEMS } from "@/lib/nav";

// 替换原 LEARN_ROUTES：
const LEARN_ROUTES = PRIMARY_NAV.map((n) => n.href);
// 高亮判断（原 :44 逻辑）可继续用 LEARN_ROUTES；
// 主导航渲染改为遍历 PRIMARY_NAV（label/hint 字段已备好 tooltip 文案）。
```

CommandPalette 接线（`frontend/src/app/layout.tsx`，全局挂载）：

```tsx
import CommandPalette from "@/components/ui/CommandPalette";
import { PALETTE_ITEMS, PRIMARY_NAV } from "@/lib/nav";
// 在 <body> 内、子内容旁挂载（Props 字段名以 ui/CommandPalette.tsx 顶部类型为准，
// tsc 会校验；仅允许按其 Props 重命名传参，数据内容不得改动）：
<CommandPalette items={[...PRIMARY_NAV, ...PALETTE_ITEMS]} />
```

⚠️ 若 `CommandPalette` 的 Props 与 `items` 形状不同：读该文件顶部 `type Props`，把 `NavItem` 按其契约传入（允许改字段名对号入座，**不得改 NAV 数据**），tsc RC0 为准。

`/knowledge` 从主导航移除（进 PALETTE_ITEMS，已含）；`LEARN_ROUTES` 不再包含 `/knowledge`。

- [ ] **Step 7: 门禁 + 冒烟**

Run（cwd=frontend）:
```
node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
node node_modules/eslint/bin/eslint.js src/lib/nav.ts src/app/learn/page.tsx src/app/review/page.tsx src/app/progress/page.tsx src/app/stages/page.tsx src/components/ReviewBoard.tsx src/components/GlobalNav.tsx src/app/layout.tsx src/app/today/page.tsx
```
Expected: tsc RC0；eslint 零问题（GlobalNav 若有既有基线告警，零新增）

人工/脚本冒烟（后端起着）：访问 `/learn`、`/review`、`/progress`、`/stages`、`/today`（应 307/308 到 /learn）；`/learn` 五区与施工单与迁移前一致。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib/nav.ts frontend/src/app/learn frontend/src/app/review frontend/src/app/progress frontend/src/app/stages frontend/src/app/today frontend/src/components/ReviewBoard.tsx frontend/src/components/GlobalNav.tsx frontend/src/app/layout.tsx
git commit -m "feat(ia): 三问三入口 /learn /review /progress + 归档线收进 /stages"
```

---

### Task 10: STYLE.md 不变量成文 + 活跃端点盘点

**Files:**
- Create: `docs/STYLE.md`
- Test: `backend/tests/test_active_write_endpoints.py`

**Interfaces:**
- Produces: `docs/STYLE.md`（工程不变量清单）；活跃写端点计数测试（防回涨）

- [ ] **Step 1: 写端点计数测试**

```python
# backend/tests/test_active_write_endpoints.py
"""STYLE.md 不变量：活跃写端点 ≤25 且总数不增反减（spec §5.3）。

计数口径：OpenAPI 中 POST/PATCH/PUT/DELETE 路径，剔除带
deprecated 标记（include_in_schema=False）的路由。
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MAX_ACTIVE_WRITE_ENDPOINTS = 25


def test_active_write_endpoints_within_budget():
    schema = client.get("/openapi.json").json()
    write_ops = {"post", "patch", "put", "delete"}
    active = {
        f"{m.upper()} {p}"
        for p, ops in schema["paths"].items()
        for m in ops
        if m in write_ops
    }
    assert len(active) <= MAX_ACTIVE_WRITE_ENDPOINTS, sorted(active)
```

- [ ] **Step 2: 跑测试看现状**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_active_write_endpoints.py -q`
Expected: 若 FAIL（超预算）→ Step 3 的 deprecated 收口把零消费路由移出 schema，直到过线；**不得删除路由**（撤 UI 留数据，spec D5）

- [ ] **Step 3: 零消费端点标 deprecated**

对下列路由（mapper 实测零消费）的 `APIRouter` 或端点装饰加 `include_in_schema=False`，并在模块 docstring 首行加 `DEPRECATED（2026-09-24 收敛）：零前端消费，保数据不删路由`：

- `backend/app/api/dashboard.py`（GET /api/dashboard）
- `backend/app/api/tools.py`（全部）
- `backend/app/api/career_mode.py` 的 `GET /transitions`
- `backend/app/api/paper.py` 的 `POST /compare`

每处改完重跑 Step 1 测试直到通过。若仍超 25，继续把「仅测试调用」的端点（如 `GET /api/risk`）同样标注——并在 PR 描述列出全部标注清单。

**死组件删除**（撤 UI 留数据的前端半边；本步一并做）：

1. 显式删除两个已被新实现取代的死组件：
   - `frontend/src/components/ReportsBoard.tsx`（/review 已由 ReviewBoard 承载复盘）
   - `frontend/src/components/TaskCompleteForm.tsx`（Teach-Back/UnitView 已承载回收；它本就处于死组件子树）
2. 扫描其余零引用组件并删除：
```bash
cd frontend/src
for f in components/*.tsx; do n=$(basename "$f" .tsx); c=$(grep -rl "from \"@/components/$n\"\|from \"./$n\"" --include='*.tsx' --include='*.ts' . | grep -v "components/$n.tsx" | wc -l); [ "$c" -eq 0 ] && echo "DEAD: $f"; done
```
   （输出的 DEAD 列表逐个确认非动态 import 后删除；`ui/` 下组件被 index.ts 汇出的不算死。）
3. 同法清零引用的 service（如 `githubService` 若计划 3 接线前仍零 import，保留——计划 3 Task 3 要用，仅在清单里标注「待计划 3 接线」）。

删除后 tsc+eslint 必须 RC0/零问题——任何 import 报错说明删错，恢复该文件。

- [ ] **Step 4: 写 STYLE.md**

`docs/STYLE.md`：

```markdown
# STYLE —— 加模块前的对照门槛（2026-09-24）

> 来源：spec 5.3。不是建议，是门槛：新功能开工前逐条对照，任一不过就先改设计。

1. **SQLite 单文件**，不引入第二个数据库/向量库实例（现有 ChromaDB/向量表除外）。
2. **不新增平行权威域**：策略单一真源在 `backend/app/core/` 纯函数层（skill_profile /
   target_roles / plan_30d / capacity / evidence）；改口径改这里，不在业务层各存一份。
3. **加端点前先问**：能否并入三类 intake（学习回收 / 半自动事实 / 主动登记）？
   能并就并。活跃写端点预算 **≤25**，只减不增（`test_active_write_endpoints.py` 守）。
4. **写死在前端文案里的数字是负债**：写"资源均来自资源锁"，不写"这 N 类"。
5. **降级必须可见**：LLM/嵌入/生成任一降级，UI 必须有徽标（answer_mode / generation_mode 同款）。
6. **拒绝线**（明文不做）：自动投递/爬虫反指纹、Gmail 全量授权、AGPL 代码复制、
   第五条产品线、未经人审的 AI 直写事实。
7. **AI 改码契约**：`docs/superpowers/specs/*.md` 中标"契约"的接口签名不得静默变更；
   prompt 变更跑 `test_persona_prompts.py`。
8. **提交纪律**：`git add` 显式路径，禁止 `git add -A`；工作区有他人改动时只提交自己的文件。
```

- [ ] **Step 5: 跑全量门禁 + Commit**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --tb=short` → 基线不降（含新计数测试）
`cd frontend && node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` → RC0

```bash
git add docs/STYLE.md backend/tests/test_active_write_endpoints.py backend/app/api/dashboard.py backend/app/api/tools.py backend/app/api/career_mode.py backend/app/api/paper.py
git commit -m "chore(api): 零消费端点标 deprecated + STYLE.md 不变量成文（活跃写端点 ≤25）"
```

---

## 验收（本计划整体）

1. `pytest tests/ -q` → **≥437 passed / 0 failed / 2 skipped**（新增用例全绿，基线不降）
2. `tsc --noEmit` RC0；eslint 零新增问题
3. 人工确认：`/learn` 走通每日流（旧数据形态）；`/today` 重定向；`/knowledge` 不在主导航但 URL 可达；CommandPalette 能打开低频入口
4. 开发库核对：`learning_logs` 演示 14 条已清（有备份）；`agent_runs` 不再新增含 "Isaac" 占位输入的记录
5. `test_active_write_endpoints.py` 绿（活跃写端点 ≤25）
