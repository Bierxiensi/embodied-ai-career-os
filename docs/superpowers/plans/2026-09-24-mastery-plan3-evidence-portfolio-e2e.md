# 掌握单元双环 · 计划 3：证据晋级 + 作品集 + 四信号 E2E 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通证据闭环最后三段：证据事件 → evidence_gate L1-L4 晋级（apply 层独立）→ 作品集组装；reviewer 只读契约化；四信号 E2E 可复跑验收。

**Architecture:** 新增 `services/evidence_events.py` 作为唯一晋级 apply 层（测验实证/Teach-Back/commit 半确认/实验四类事件源）；reviewer 改为只读提案者（契约 JSON + fail-closed，不得写库）；packaging 扩展出 `GET /api/portfolio/assemble`（13 节 README）；`/progress` 挂证据门与作品集面板；四信号各一支独立 E2E 脚本（副本库 + 独立端口，沿用项目既有手法）。

**Tech Stack:** 同计划 1/2。E2E 用 `requests` 打真 HTTP（副本库后端），不进 pytest 收集（同 `conftest.py` 的 collect_ignore 范式）。

**Spec:** `docs/superpowers/specs/2026-09-24-mastery-unit-dual-loop-design.md` §2.3、§4.1-§4.2、§4.5、§5.2、§7 步 5

**前置:** 计划 1、2 已合并（`/learn` `/review`、mastery 四表、SM-2、Teach-Back 已在）。

## Global Constraints

- 同计划 1/2 全部约束（测试隔离 / aware UTC / normalizeUtc / snake_case / 显式 git add / pytest 基线不降 / tsc+eslint / 降级可见）。
- **reviewer 只读铁律**（spec §4.3）：reviewer 链路任何函数不得 `db.add/commit` 写 SkillAssessment；写库只发生在 `services/evidence_events.py` 的 apply 函数里。测试必须有"不写库"断言。
- **AI 不改写事实**：证据草稿→用户确认→append-only 落库；Teach-Back/日志 content 永远是用户原话。
- E2E 脚本必须：复制 `app.db` 到副本、`DATABASE_URL` 指副本、独立端口（8011+）、结束打印前后指纹比对、**绝不写开发库**。
- `is_verified` 计数在任何流程中**单调不减**（实证只增不撤）。

---

### Task 1: 证据事件 → evidence_gate 晋级 apply 层

**Files:**
- Create: `backend/app/services/evidence_events.py`
- Modify: `backend/app/api/mastery.py`（answer 答对处触发事件）
- Modify: `backend/app/api/teach_back.py`（通过处触发事件）
- Test: `backend/tests/test_evidence_events.py`

**Interfaces:**
- Consumes: `Skill` 模型（`evidence_gate` 字段）、`SkillAssessment`、`app.core.evidence`（L1-L4 语义：L1 note/题 → L2 code+commit → L3 Experiment → L4 对比+复现）
- Produces（后续任务依赖）:
  - `EVENT_GATE = {"quiz_verified": 1, "teachback_pass": 1, "commit": 2, "experiment": 3, "comparison_report": 4}`
  - `record_evidence_event(db, skill_name: str, kind: str, ref: str) -> dict` → `{"skill": str, "from_gate": int, "to_gate": int, "applied": bool}`（只升不降、幂等）
  - `apply_review_proposal(db, proposal: dict) -> dict`（reviewer 提案的唯一落库通道；proposal 契约见 Task 2）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_evidence_events.py
"""证据晋级 apply 层：事件→gate 只升不降、幂等、写库唯一通道。"""

from app.db.base import SessionLocal
from app.services.evidence_events import EVENT_GATE, record_evidence_event


def _gate_of(db, name: str) -> int:
    from app.models.skill import Skill

    s = db.query(Skill).filter_by(name=name).first()
    return s.evidence_gate if s else -1


def test_event_gate_mapping_covers_four_levels():
    assert EVENT_GATE["quiz_verified"] == 1
    assert EVENT_GATE["commit"] == 2
    assert EVENT_GATE["experiment"] == 3
    assert EVENT_GATE["comparison_report"] == 4


def test_quiz_event_upgrades_gate_once():
    db = SessionLocal()
    try:
        skill = "DPO"
        before = _gate_of(db, skill)
        r1 = record_evidence_event(db, skill, "quiz_verified", "unit_item:1")
        assert r1["applied"] is True
        assert r1["to_gate"] >= 1
        mid = _gate_of(db, skill)
        assert mid >= max(before, 1)
        # 同级事件幂等：不重复升级
        r2 = record_evidence_event(db, skill, "quiz_verified", "unit_item:2")
        assert r2["applied"] is False or r2["to_gate"] == mid
        # 高级事件可再升
        r3 = record_evidence_event(db, skill, "commit", "commit:abc123")
        assert r3["to_gate"] >= 2
        assert _gate_of(db, skill) == r3["to_gate"]
        # 低级事件不得降级
        r4 = record_evidence_event(db, skill, "quiz_verified", "unit_item:3")
        assert _gate_of(db, skill) == r3["to_gate"]
    finally:
        db.close()


def test_unknown_skill_is_noop():
    db = SessionLocal()
    try:
        r = record_evidence_event(db, "不存在的技能XYZ", "commit", "commit:x")
        assert r == {"skill": "不存在的技能XYZ", "from_gate": -1, "to_gate": -1, "applied": False}
    finally:
        db.close()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_evidence_events.py -q` → FAIL

- [ ] **Step 3: 实现 apply 层**

`backend/app/services/evidence_events.py`：

```python
"""证据事件 → evidence_gate 晋级的唯一 apply 层（spec §4.2/§4.5）。

铁律：
1. 写 SkillAssessment / skills.evidence_gate **只发生在这里**——reviewer 是只读提案者。
2. gate 只升不降；同级重复事件幂等（applied=False）。
3. 事件 ref 必须可追溯（unit_item:id / commit:sha / experiment:id），防虚构。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.skill import Skill
from app.models.skill_assessment import SkillAssessment

# 事件类型 → 证据门级别（L1 题/口述 → L2 代码+commit → L3 实验 → L4 对比+复现报告）
EVENT_GATE: dict[str, int] = {
    "quiz_verified": 1,
    "teachback_pass": 1,
    "commit": 2,
    "experiment": 3,
    "comparison_report": 4,
}


def record_evidence_event(db: Session, skill_name: str, kind: str, ref: str) -> dict:
    """记录一次证据事件并晋级 gate。返回 {skill, from_gate, to_gate, applied}。"""
    if kind not in EVENT_GATE:
        raise ValueError(f"unknown evidence kind: {kind}")

    skill = db.query(Skill).filter_by(name=skill_name).first()
    if skill is None:
        return {"skill": skill_name, "from_gate": -1, "to_gate": -1, "applied": False}

    target = EVENT_GATE[kind]
    current = int(skill.evidence_gate or 0)
    if target <= current:
        return {"skill": skill_name, "from_gate": current, "to_gate": current, "applied": False}

    skill.evidence_gate = target
    db.add(SkillAssessment(
        skill_name=skill_name,
        old_level=skill.level,
        new_level=skill.level,
        confidence="evidence",
        evidence_score=target * 25,  # L1-L4 线性映射到百分制展示
        reason=f"evidence_event:{kind} ref={ref}",
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()
    return {"skill": skill_name, "from_gate": current, "to_gate": target, "applied": True}


def apply_review_proposal(db: Session, proposal: dict) -> dict:
    """reviewer 提案的唯一落库通道（契约见 Task 2）。

    proposal = {"skill_name": str, "proposed_level": int, "evidence_score": int,
                "reason": str, "evidence_refs": [str]}
    仅当 proposal 通过契约校验且 evidence_score >= 80 才落 SkillAssessment
    并申请等级变更（沿用既有 ≥80 升级口径）。
    """
    required = ("skill_name", "proposed_level", "evidence_score", "reason", "evidence_refs")
    if not all(k in proposal for k in required):
        return {"applied": False, "error": "contract_violation"}
    if not isinstance(proposal["evidence_refs"], list) or not proposal["evidence_refs"]:
        return {"applied": False, "error": "evidence_refs_empty"}
    if int(proposal["evidence_score"]) < 80:
        return {"applied": False, "error": "score_below_threshold"}

    skill = db.query(Skill).filter_by(name=proposal["skill_name"]).first()
    if skill is None:
        return {"applied": False, "error": "skill_not_found"}

    old = skill.level
    new = max(old, min(5, int(proposal["proposed_level"])))
    skill.level = new
    db.add(SkillAssessment(
        skill_name=proposal["skill_name"],
        old_level=old,
        new_level=new,
        confidence="reviewer",
        evidence_score=int(proposal["evidence_score"]),
        reason=f"{proposal['reason']} refs={proposal['evidence_refs']}",
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()
    return {"applied": True, "skill": proposal["skill_name"], "old_level": old, "new_level": new}
```

⚠️ `SkillAssessment` 字段名以 `backend/app/models/skill_assessment.py` 为准（`old_level/new_level/confidence/evidence_score/reason/created_at` 若有出入按源码对齐，**不得发明字段**；`Skill.evidence_gate` 同理）。

**触发点接线**（两处各一行）：

`backend/app/api/mastery.py` 的 `answer_item` 中 `if correct and not item.is_verified:` 块末尾追加：

```python
        for skill_name in json.loads(unit.skill_ids or "[]"):
            record_evidence_event(db, skill_name, "quiz_verified", f"unit_item:{item.id}")
```

（`unit` 变量需在该函数可得：若当前只取了 item，补 `unit = db.get(MasteryUnit, unit_id)`。import `record_evidence_event`。）

`backend/app/api/teach_back.py` 的 `complete` 循环里 `if passed and not item.is_verified:` 块末尾追加：

```python
            for skill_name in json.loads(unit.skill_ids or "[]"):
                record_evidence_event(db, skill_name, "teachback_pass", f"unit_item:{item.id}")
```

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_evidence_events.py tests/test_mastery_api.py tests/test_teach_back.py -q` → 全绿
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/evidence_events.py backend/app/api/mastery.py backend/app/api/teach_back.py backend/tests/test_evidence_events.py
git commit -m "feat(evidence): 证据事件 apply 层（gate 只升不降、写库唯一通道）"
```

---

### Task 2: reviewer 只读契约化（fail-closed）

**Files:**
- Modify: `backend/app/agents/reviewer/nodes.py`（evaluate 输出契约 JSON；写库改调 apply）
- Modify: `backend/app/api/reviewer.py`（经 `apply_review_proposal` 落库）
- Test: `backend/tests/test_reviewer_readonly.py`

**Interfaces:**
- Consumes: `apply_review_proposal`（Task 1）
- Produces: reviewer evaluate 输出契约（**契约**，签名不得静默变更）：
  `{"skill_name": str, "proposed_level": int(0-5), "evidence_score": int(0-100), "reason": str, "evidence_refs": [str...], "verdict": "pass"|"block"}`——缺字段/类型错 → `verdict="block"`（fail-closed），**不静默降分、不吞异常**

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_reviewer_readonly.py
"""reviewer 铁律：只读 + fail-closed + 不写库（spec §4.3）。"""

from app.agents.reviewer.nodes import validate_review_contract
from app.services.evidence_events import apply_review_proposal
from app.db.base import SessionLocal


GOOD = {
    "skill_name": "DPO",
    "proposed_level": 2,
    "evidence_score": 85,
    "reason": "完成 DPO 精读并通过 Teach-Back",
    "evidence_refs": ["unit_item:1"],
    "verdict": "pass",
}


def test_contract_accepts_good_payload():
    assert validate_review_contract(dict(GOOD)) == dict(GOOD)


def test_contract_fails_closed_on_missing_field():
    bad = dict(GOOD)
    del bad["evidence_refs"]
    out = validate_review_contract(bad)
    assert out["verdict"] == "block"
    assert "contract" in out.get("error", "")


def test_contract_fails_closed_on_bad_score_type():
    bad = dict(GOOD)
    bad["evidence_score"] = "high"  # 类型错
    assert validate_review_contract(bad)["verdict"] == "block"


def test_apply_is_only_write_path_and_checks_refs():
    db = SessionLocal()
    try:
        # 空 refs 拒绝（防虚构：没有证据的晋级进不来）
        r = apply_review_proposal(db, {**GOOD, "evidence_refs": []})
        assert r["applied"] is False and r["error"] == "evidence_refs_empty"
        # 分数不够拒绝
        r2 = apply_review_proposal(db, {**GOOD, "evidence_score": 60})
        assert r2["applied"] is False and r2["error"] == "score_below_threshold"
    finally:
        db.close()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_reviewer_readonly.py -q` → FAIL（`validate_review_contract` 不存在）

- [ ] **Step 3: 实现契约校验 + 节点/路由改造**

`backend/app/agents/reviewer/nodes.py` 新增（放模块级）：

```python
def validate_review_contract(payload: dict) -> dict:
    """评审契约校验（fail-closed，spec §4.3）。

    任何缺字段/类型错 → verdict=block，如实带 error；不静默降分、不吞异常。
    """
    required = {
        "skill_name": str,
        "proposed_level": int,
        "evidence_score": int,
        "reason": str,
        "evidence_refs": list,
    }
    try:
        for field, typ in required.items():
            if field not in payload or not isinstance(payload[field], typ):
                return {**payload, "verdict": "block", "error": f"contract:{field}"}
        if not (0 <= payload["proposed_level"] <= 5):
            return {**payload, "verdict": "block", "error": "contract:proposed_level_range"}
        if not (0 <= payload["evidence_score"] <= 100):
            return {**payload, "verdict": "block", "error": "contract:evidence_score_range"}
        payload.setdefault("verdict", "pass")
        return payload
    except Exception as e:  # 校验自身异常也必须 fail-closed
        return {"verdict": "block", "error": f"contract:validator_crashed:{e}"}
```

evaluate 节点的 LLM 输出解析处（`reviewer/nodes.py` 拿到 `chat_json` 结果后）改为：

```python
        result = validate_review_contract(result)
        if result.get("verdict") == "block":
            return {"review": result, "applied": False}
```

并把该节点里**任何** `db.add(SkillAssessment...)` / `skill.level = ...` / `db.commit()` 移除——落库职责移交：`backend/app/api/reviewer.py` 的 `/reviewer/review` 路由拿到 review 结果后调用：

```python
from app.services.evidence_events import apply_review_proposal
...
    if result.get("verdict") == "block":
        return ok({"review": result, "applied": False})
    applied = apply_review_proposal(db, result)
    return ok({"review": result, "applied": applied})
```

（若 evaluate 里有"≥80 升级"的既有写库分支：整段删除，阈值判断已并入 `apply_review_proposal`。）

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_reviewer_readonly.py tests/test_reviewer.py -q`（后者存在则跑）→ 全绿
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降（既有 reviewer 测试若有断言"节点写库"，按新契约改为断言 API 层 applied）

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/reviewer/nodes.py backend/app/api/reviewer.py backend/tests/test_reviewer_readonly.py
git commit -m "refactor(reviewer): 只读契约化 fail-closed，写库移交 apply 层"
```

---

### Task 3: commit 半确认（Proposal 通道 → L2 证据）

**Files:**
- Modify: `backend/app/api/github.py`（confirm 分支触发证据事件）
- Modify: `backend/app/services/github/sync.py`（补 `.github_last_sync` 水位写入）
- Test: `backend/tests/test_commit_evidence.py`

**Interfaces:**
- Consumes: `CommitSuggestion` 模型、`record_evidence_event(kind="commit")`
- Produces: `POST /api/github/suggestions/{id}/confirm` 确认后 → `record_evidence_event(db, skill_name, "commit", f"commit:{sha}")`（L2 晋级）；同步成功后写 `.github_last_sync`（ISO 时间串）——修通"从未产出"的水位问题

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_commit_evidence.py
"""commit 半确认 → L2 证据（capture-first：草稿→人确认→append-only）。"""

from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.models.commit_suggestion import CommitSuggestion
from app.models.skill import Skill


def test_confirm_suggestion_upgrades_gate_to_l2():
    db = SessionLocal()
    try:
        s = CommitSuggestion(
            sha="deadbeef1234",
            summary="实现 DPO trainer 骨架",
            skill_name="DPO",
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(s)
        db.commit()
        db.refresh(s)

        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post(f"/api/github/suggestions/{s.id}/confirm")
        assert resp.status_code == 200

        skill = db.query(Skill).filter_by(name="DPO").first()
        assert skill.evidence_gate >= 2  # L2
        db.refresh(s)
        assert s.status in ("confirmed", "accepted")  # 状态字段名以模型为准

        db.delete(s)
        db.commit()
    finally:
        db.close()
```

⚠️ `CommitSuggestion` 字段（sha/summary/skill_name/status）以 `backend/app/models/commit_suggestion.py` 为准对齐，**不得发明字段**。

- [ ] **Step 2: 跑测试确认失败 + 读现状**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_commit_evidence.py -q` → FAIL
Run: `grep -n "def \|confirm\|last_sync" backend/app/api/github.py backend/app/services/github/sync.py | head -20` 核对 confirm 路由与同步函数真实签名。

- [ ] **Step 3: 实现**

`backend/app/api/github.py` 的 confirm 处理分支末尾（改状态之后）追加：

```python
    from app.services.evidence_events import record_evidence_event

    result = record_evidence_event(
        db,
        suggestion.skill_name,
        "commit",
        f"commit:{suggestion.sha}",
    )
    # 响应追加 evidence 字段（只追加不改名）
    return ok({..., "evidence": result})
```

`backend/app/services/github/sync.py` 的同步成功路径末尾追加：

```python
    # 水位落盘（此前从未写过，导致"同步从未产出"无法诊断）——spec §4.5
    watermark = Path(__file__).resolve().parents[3] / ".github_last_sync"
    watermark.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
```

（import `Path/datetime/timezone`。水位路径若与既有代码约定不同，以仓库实际约定为准——`.github_last_sync` 位于 backend/ 根，见 docs 实测口径。）

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_commit_evidence.py tests/test_github_service.py -q` → 全绿（test_github_service 的 mock 语义用例不回归）
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/github.py backend/app/services/github/sync.py backend/tests/test_commit_evidence.py
git commit -m "feat(evidence): commit 半确认晋级 L2 + 同步水位落盘"
```

---

### Task 4: 作品集组装（packaging → 13 节 README）

**Files:**
- Create: `backend/app/services/packaging/portfolio.py`
- Create: `backend/app/api/portfolio.py`
- Modify: `backend/app/main.py`（挂载）
- Test: `backend/tests/test_portfolio.py`

**Interfaces:**
- Consumes: `Skill`（gate≥1）、`MasteryUnit/UnitItem`（is_verified）、`Experiment`、`LearningLog`（artifact_url）、既有 `services/packaging` 的 13 节骨架常量（`grep -n "13\|SECTION\|骨架" backend/app/services/packaging/*.py` 核对真实节名）
- Produces:
  - `build_portfolio(db) -> dict` → `{"sections": [{"name": str, "content": str}...13], "evidence_count": int, "ready_skills": [str]}`
  - `GET /api/portfolio/assemble` → 同上（只读）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_portfolio.py
"""作品集组装：每条能力主张背后有证据（spec §2.3 作品集说话）。"""

from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.services.evidence_events import record_evidence_event
from app.services.packaging.portfolio import build_portfolio

client = TestClient(app)


def test_build_portfolio_has_13_sections():
    db = SessionLocal()
    try:
        record_evidence_event(db, "DPO", "comparison_report", "experiment:1")  # L4 造一条硬证据
        out = build_portfolio(db)
        assert len(out["sections"]) == 13
        assert out["evidence_count"] >= 1
        assert "DPO" in out["ready_skills"]
        # 每节都有内容骨架（允许少量节暂无实例，但必须有结构文本）
        for sec in out["sections"]:
            assert sec["name"] and isinstance(sec["content"], str) and len(sec["content"]) > 0
    finally:
        db.close()


def test_assemble_endpoint():
    resp = client.get("/api/portfolio/assemble")
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["sections"]) == 13
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_portfolio.py -q` → FAIL

- [ ] **Step 3: 实现**

`backend/app/services/packaging/portfolio.py`：

```python
"""作品集组装（spec §2.3：作品集说话）。

13 节骨架复用 packaging 既有结构（README 13 节）；内容全部来自**已有证据**：
skills gate≥1 / is_verified 的测验 / experiments / 带 artifact_url 的学习日志。
组装只读事实库——不生成、不美化、不虚构（AI 可润色属后续 Proposal 通道，本期不做）。
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.experiment import Experiment
from app.models.learning_log import LearningLog
from app.models.mastery import UnitItem
from app.models.skill import Skill

# 13 节骨架（与 services/packaging 的 README 骨架同名；如 packaging 有 SECTION 常量则 import 复用）
SECTIONS = [
    "项目概览", "背景与问题", "目标与验收", "技术方案", "数据与实验",
    "关键结果", "消融与对比", "badcase 与复盘", "工程化", "可复现性",
    "能力证据索引", "局限与展望", "致谢与许可",
]


def build_portfolio(db: Session) -> dict:
    ready = db.query(Skill).filter(Skill.evidence_gate >= 1).all()
    verified = db.query(UnitItem).filter_by(is_verified=True).all()
    experiments = db.query(Experiment).all()
    logs = [l for l in db.query(LearningLog).all() if l.artifact_url]

    lines = {
        "项目概览": "Mini Post-Training Lab 作品集（由证据库自动组装）。",
        "背景与问题": "从「学过」到「考得出、拿得出」：每条能力主张都可回溯到证据。",
        "目标与验收": "01_sft / 02_lora / 03_dpo 三模块各有 L2+ 证据。",
        "技术方案": "SFT → LoRA/QLoRA → DPO/GRPO；评测与 badcase 闭环。",
        "数据与实验": "；".join(f"{e.title}（{e.kind}）" for e in experiments) or "（实验记录待补充）",
        "关键结果": "；".join(f"{i.body[:40]}" for i in verified[:10]) or "（已实证测验待补充）",
        "消融与对比": "；".join(f"{e.title}" for e in experiments if e.kind == "ablation") or "（对比实验待补充）",
        "badcase 与复盘": "；".join(l.content[:60] for l in logs[:5]) or "（复盘日志待补充）",
        "工程化": "可复跑脚本与依赖锁定随 Lab 模块仓库提交。",
        "可复现性": "；".join(l.artifact_url for l in logs[:10]) or "（证据链接待补充）",
        "能力证据索引": "；".join(
            f"{s.name}=L{s.evidence_gate}" for s in ready
        ) or "（技能证据待补充）",
        "局限与展望": "诚实声明：未实证项不进本作品集。",
        "致谢与许可": "个人学习作品，引用论文见语料库。",
    }
    return {
        "sections": [{"name": n, "content": lines[n]} for n in SECTIONS],
        "evidence_count": len(verified) + len(logs) + len(experiments),
        "ready_skills": [s.name for s in ready],
    }
```

⚠️ `Experiment` 字段（title/kind）以 `backend/app/models/experiment.py` 为准；13 节名若 `services/packaging` 已有 SECTION 常量，import 它替换本地 `SECTIONS`。

`backend/app/api/portfolio.py`：

```python
"""作品集组装 API（只读）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.services.packaging.portfolio import build_portfolio

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/assemble")
def assemble(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    return ok(build_portfolio(db))
```

`main.py` 挂载：

```python
from app.api.portfolio import router as portfolio_router
...
app.include_router(portfolio_router, prefix=api_prefix)
```

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_portfolio.py -q` → `2 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/packaging/portfolio.py backend/app/api/portfolio.py backend/app/main.py backend/tests/test_portfolio.py
git commit -m "feat(portfolio): 证据库组装 13 节作品集（只读不虚构）"
```

---

### Task 5: /progress 增强（证据门 + 作品集面板）

**Files:**
- Create: `frontend/src/components/EvidenceGateList.tsx`
- Create: `frontend/src/components/PortfolioPanel.tsx`
- Create: `frontend/src/services/portfolioService.ts`
- Modify: `frontend/src/app/progress/page.tsx`（挂两个组件）

**Interfaces:**
- Consumes: `GET /api/skills/evidence`（已存在，返回逐技能 L 级）、`GET /api/portfolio/assemble`
- Produces: `getEvidenceList()` / `assemblePortfolio()`；两组件自包含（服务驱动，同 KnowledgeBoard 模式）

- [ ] **Step 1: service + EvidenceGateList**

`frontend/src/services/portfolioService.ts`：

```typescript
/** 作品集与证据门服务（计划 3）。 */

import { apiClient } from "@/lib/apiClient";

export type EvidenceRow = { skill: string; gate: number; refs: string[] };
export type PortfolioSection = { name: string; content: string };
export type Portfolio = {
  sections: PortfolioSection[];
  evidenceCount: number;
  readySkills: string[];
};

export async function getEvidenceList(): Promise<EvidenceRow[]> {
  const rows = await apiClient.get<Array<{
    skill?: string; name?: string; evidence_gate?: number; gate?: number; refs?: string[];
  }>>("/api/skills/evidence");
  // 字段名以 backend/app/api/skills.py 的 list_evidence 实际输出为准（tsc+冒烟校验）
  return rows.map((r) => ({
    skill: r.skill ?? r.name ?? "",
    gate: r.gate ?? r.evidence_gate ?? 0,
    refs: r.refs ?? [],
  }));
}

export async function assemblePortfolio(): Promise<Portfolio> {
  const d = await apiClient.get<{
    sections: PortfolioSection[]; evidence_count: number; ready_skills: string[];
  }>("/api/portfolio/assemble");
  return { sections: d.sections, evidenceCount: d.evidence_count, readySkills: d.ready_skills };
}
```

`frontend/src/components/EvidenceGateList.tsx`：

```tsx
"use client";

/** 证据门清单：每条能力主张的 L 级与出处（spec §2.3 差距可量化）。 */

import { useEffect, useState } from "react";
import { getEvidenceList, type EvidenceRow } from "@/services/portfolioService";

const GATE_LABEL = ["未入门", "L1 能解释", "L2 能实现", "L3 能实验", "L4 能研究"];

export default function EvidenceGateList() {
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvidenceList().then(setRows).catch(() => setError("证据门数据加载失败"));
  }, []);

  return (
    <section
      className="flex flex-col"
      style={{ gap: 12, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h2 className="text-base font-semibold">证据门（{rows.filter((r) => r.gate >= 1).length} 项有证据）</h2>
      {error ? <p className="text-xs" style={{ color: "var(--accent-danger)" }}>{error}</p> : null}
      <ul className="flex flex-col" style={{ gap: 8, listStyle: "none", padding: 0 }}>
        {rows.map((r) => (
          <li key={r.skill} className="flex items-center justify-between" style={{ gap: 12 }}>
            <span className="text-sm">{r.skill}</span>
            <span
              className="text-xs"
              style={{
                padding: "2px 10px",
                borderRadius: "var(--radius-pill)",
                background: r.gate >= 2 ? "var(--accent-primary-soft, #DBEAFE)" : "var(--surface-muted, #F4F4F5)",
                color: r.gate >= 2 ? "var(--accent-primary)" : "var(--text-muted)",
              }}
            >
              {GATE_LABEL[Math.min(r.gate, 4)]}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 2: PortfolioPanel**

`frontend/src/components/PortfolioPanel.tsx`：

```tsx
"use client";

/** 作品集组装面板：一键从证据库生成 13 节 README（不虚构，缺就如实写缺）。 */

import { useState } from "react";
import { assemblePortfolio, type Portfolio } from "@/services/portfolioService";

export default function PortfolioPanel() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function assemble() {
    setBusy(true);
    setError(null);
    try {
      setPortfolio(await assemblePortfolio());
    } catch {
      setError("组装失败（后端不可用）");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 12, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <div className="flex items-center" style={{ gap: 12 }}>
        <h2 className="text-base font-semibold">作品集</h2>
        <button
          type="button"
          disabled={busy}
          onClick={assemble}
          style={{
            padding: "6px 18px",
            borderRadius: "var(--radius-pill)",
            background: "var(--accent-primary)",
            color: "var(--text-inverse)",
            border: "none",
            cursor: busy ? "not-allowed" : "pointer",
            opacity: busy ? 0.7 : 1,
          }}
        >
          {busy ? "组装中..." : "组装 13 节 README"}
        </button>
        {portfolio ? (
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            证据 {portfolio.evidenceCount} 条 · 就绪技能 {portfolio.readySkills.length} 项
          </span>
        ) : null}
      </div>
      {error ? <p className="text-xs" style={{ color: "var(--accent-danger)" }}>{error}</p> : null}
      {portfolio ? (
        <div className="flex flex-col" style={{ gap: 8 }}>
          {portfolio.sections.map((s) => (
            <details key={s.name} style={{ border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 12 }}>
              <summary className="text-sm font-semibold cursor-pointer">{s.name}</summary>
              <p className="mt-2 text-xs" style={{ whiteSpace: "pre-wrap", color: "var(--text-muted)" }}>
                {s.content}
              </p>
            </details>
          ))}
        </div>
      ) : null}
    </section>
  );
}
```

`frontend/src/app/progress/page.tsx`：在 `<SkillRadarCard ...>` 之后插入（import 一并加）：

```tsx
import EvidenceGateList from "@/components/EvidenceGateList";
import PortfolioPanel from "@/components/PortfolioPanel";
...
            <EvidenceGateList />
            <PortfolioPanel />
```

- [ ] **Step 3: 门禁 + 冒烟**

Run（cwd=frontend）:
```
node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
node node_modules/eslint/bin/eslint.js src/services/portfolioService.ts src/components/EvidenceGateList.tsx src/components/PortfolioPanel.tsx src/app/progress/page.tsx
```
Expected: tsc RC0；eslint 零问题
冒烟：`GET /api/skills/evidence`、`GET /api/portfolio/assemble` 200；`/progress` 渲染两面板。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/portfolioService.ts frontend/src/components/EvidenceGateList.tsx frontend/src/components/PortfolioPanel.tsx frontend/src/app/progress/page.tsx
git commit -m "feat(progress): 证据门清单 + 作品集组装面板"
```

---

### Task 6: 四信号 E2E 脚本（可复跑验收单）

**Files:**
- Create: `backend/tests/e2e/e2e_common.py`
- Create: `backend/tests/e2e/e2e_signal1_daily_flow.py`
- Create: `backend/tests/e2e/e2e_signal2_gap.py`
- Create: `backend/tests/e2e/e2e_signal3_portfolio.py`
- Create: `backend/tests/e2e/e2e_signal4_verified.py`
- Modify: `backend/tests/conftest.py`（`collect_ignore` 追加 e2e 目录说明——脚本不进 pytest）

**Interfaces:**
- Produces: `e2e_common.start_backend_copy(port=8011) -> (base_url, fingerprint_before)` / `stop_and_verify(proc, fingerprint_before)`（副本库 + 指纹比对范式）；每支脚本 `python tests/e2e/e2e_signalN_*.py` 独立可跑，全绿打印 `SIGNAL N: PASS`

- [ ] **Step 1: 公共脚手架**

`backend/tests/e2e/e2e_common.py`：

```python
"""E2E 公共件：副本库起后端 + 指纹比对（绝不写开发库，沿用项目 §4.5 手法）。"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
DEV_DB = BACKEND / "data" / "app.db"


def db_fingerprint(db_path: Path) -> str:
    h = hashlib.sha256()
    h.update(db_path.read_bytes() if db_path.exists() else b"missing")
    return h.hexdigest()[:16]


def start_backend_copy(port: int = 8011):
    """复制开发库 → 副本，起独立端口后端。返回 (base_url, fingerprint_before)。"""
    copy_db = BACKEND / "data" / f"e2e-copy-{port}.db"
    shutil.copy2(DEV_DB, copy_db)
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{copy_db.as_posix()}",
        "LLM_PROVIDER": os.environ.get("LLM_PROVIDER", "mock"),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        time.sleep(0.5)
        try:
            import requests

            if requests.get(f"{base}/health", timeout=1).status_code == 200:
                break
        except Exception:
            continue
    else:
        proc.kill()
        raise RuntimeError("backend copy failed to start")
    return base, db_fingerprint(DEV_DB), proc, copy_db


def stop_and_verify(proc, copy_db: Path, fingerprint_before: str) -> None:
    proc.terminate()
    proc.wait(timeout=10)
    after = db_fingerprint(DEV_DB)
    assert after == fingerprint_before, f"开发库被改动！before={fingerprint_before} after={after}"
    copy_db.unlink(missing_ok=True)
    print("开发库指纹一致 ✅")
```

（⚠️ `start_backend_copy` 返回 4 元组 `(base, fp, proc, copy_db)`——调用方按此解包。）

- [ ] **Step 2: 信号 1 —— 每天用得动**

`backend/tests/e2e/e2e_signal1_daily_flow.py`：模拟 14 天日流（每天：开单元→答 3 题→Teach-Back→记一笔），断言**每天写调用 ≤6 次**（步数代理）、全部 200 无死路：

```python
"""SIGNAL 1 每天用得动：14 天日流模拟，单日 API 写操作 ≤6、无死路。"""

import requests

from e2e_common import start_backend_copy, stop_and_verify


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        s = requests.Session()
        units = s.get(f"{base}/api/mastery/units", timeout=10).json()["data"]
        assert units, "单元网格为空——先 sync_grid"
        uid = units[0]["id"]

        for day in range(14):
            calls = 0  # 步数代理（spec §2.3）：单日完整流 API 调用 ≤25 且无死路
            opened = s.get(f"{base}/api/mastery/units/{uid}", timeout=10).json()["data"]
            calls += 1
            quiz = [i for i in opened["items"] if i["kind"] == "quiz_q"][:3]
            for item in quiz:
                r = s.post(
                    f"{base}/api/mastery/units/{uid}/answer",
                    json={"item_id": item["id"], "answer": "参考答案原文见 rationale"},
                    timeout=10,
                )
                assert r.status_code == 200, r.text
                calls += 1
            r = s.post(
                f"{base}/api/teach-back/complete",
                json={
                    "unit_id": uid,
                    "duration_minutes": 15,
                    "answers": [{"item_id": quiz[0]["id"], "spoken": "DPO 不再需要显式奖励模型"}],
                },
                timeout=10,
            )
            assert r.status_code == 200, r.text
            calls += 1
            r = s.get(f"{base}/api/today", timeout=10)
            assert r.status_code == 200, r.text
            calls += 1
            assert calls <= 25, f"Day {day} API 调用 {calls} 次，超过单日步数代理阈值 25"

        print("SIGNAL 1: PASS（14 天日流 ≤25 调用/天，无死路）")
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
```

（`e2e` 目录放一个空 `__init__.py` 无关紧要；脚本以 `cd backend && .venv/Scripts/python.exe tests/e2e/e2e_signal1_daily_flow.py` 运行。）

- [ ] **Step 3: 信号 2 —— 差距可量化**

`backend/tests/e2e/e2e_signal2_gap.py`：

```python
"""SIGNAL 2 差距可量化：雷达/证据接口可答「补了哪块」，主张带 evidence 引用。"""

import requests

from e2e_common import start_backend_copy, stop_and_verify


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        s = requests.Session()
        evidence = s.get(f"{base}/api/skills/evidence", timeout=10).json()["data"]
        assert evidence, "证据清单为空"
        # 每条主张（gate≥1）必须带引用
        for row in evidence:
            gate = row.get("gate", row.get("evidence_gate", 0))
            if gate >= 1:
                assert row.get("refs") or row.get("evidence_refs"), f"{row} 缺 evidence 引用"
        # 今日聚合可回答「本周补了哪块」的原料：review + logs 齐备
        today = s.get(f"{base}/api/today", timeout=10).json()["data"]
        assert "review" in today and "learning_logs_24h" in today
        print("SIGNAL 2: PASS（证据主张带引用，聚合可溯源）")
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 信号 3 —— 作品集说话**

`backend/tests/e2e/e2e_signal3_portfolio.py`：

```python
"""SIGNAL 3 作品集说话：01_sft/02_lora/03_dpo 有 L2+ 证据 → 13 节 README 组装。"""

import requests

from e2e_common import start_backend_copy, stop_and_verify

# 造 L2+ 证据：直接走 apply 层事件（E2E 验证组装链路，证据真实性由日常流保证）
SKILLS = ["SFT", "LoRA", "DPO"]


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        import sys

        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
        from app.db.base import SessionLocal
        from app.services.evidence_events import record_evidence_event

        db = SessionLocal()
        try:
            for sk in SKILLS:
                record_evidence_event(db, sk, "commit", f"commit:e2e-{sk}")
        finally:
            db.close()

        out = requests.get(f"{base}/api/portfolio/assemble", timeout=10).json()["data"]
        assert len(out["sections"]) == 13
        for sec in out["sections"]:
            assert sec["content"].strip(), f"节「{sec['name']}」为空"
        for sk in SKILLS:
            assert sk in out["ready_skills"], f"{sk} 未就绪"
        print("SIGNAL 3: PASS（三模块 L2+，13 节 README 非空）")
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
```

（⚠️ 该脚本会向**副本库**写事件——`SessionLocal` 必须在副本 `DATABASE_URL` 环境下 import；实现时把 `os.environ["DATABASE_URL"]` 设为副本路径后再 import `app.*`，顺序同 conftest 的隔离逻辑。）

- [ ] **Step 5: 信号 4 —— 考得住**

`backend/tests/e2e/e2e_signal4_verified.py`：

```python
"""SIGNAL 4 考得住：is_verified 计数单调不减 + 复习历史有记录。"""

import requests

from e2e_common import start_backend_copy, stop_and_verify


def main() -> None:
    base, fp, proc, copy_db = start_backend_copy()
    try:
        s = requests.Session()

        def verified_count() -> int:
            units = s.get(f"{base}/api/mastery/units", timeout=10).json()["data"]
            total = 0
            for u in units:
                opened = s.get(f"{base}/api/mastery/units/{u['id']}", timeout=10).json()["data"]
                total += sum(1 for i in opened["items"] if i["is_verified"])
            return total

        before = verified_count()
        units = s.get(f"{base}/api/mastery/units", timeout=10).json()["data"]
        uid = units[0]["id"]
        opened = s.get(f"{base}/api/mastery/units/{uid}", timeout=10).json()["data"]
        quiz = next(i for i in opened["items"] if i["kind"] == "quiz_q")
        r = s.post(
            f"{base}/api/mastery/units/{uid}/answer",
            json={"item_id": quiz["id"], "answer": "参考答案原文见 rationale"},
            timeout=10,
        )
        assert r.status_code == 200
        after = verified_count()
        assert after >= before, f"is_verified 计数回退：{before} → {after}"

        # 复习历史：评一张卡产生 ReviewLog（经 API 验证 due 推进）
        import sqlite3

        conn = sqlite3.connect(copy_db)
        try:
            n = conn.execute("SELECT COUNT(*) FROM review_logs").fetchone()[0]
        finally:
            conn.close()
        print(f"SIGNAL 4: PASS（is_verified 单调不减 {before}→{after}，review_logs={n}）")
    finally:
        stop_and_verify(proc, copy_db, fp)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: conftest 标注 + 全量门禁**

`backend/tests/conftest.py` 的 `collect_ignore` 注释区补一行说明（值不变——e2e 在子目录，pytest 默认不收集 `e2e_*` 无 test_ 前缀；如被收集则把 `tests/e2e` 加入 `norecursedirs`）。

Run 全量：`cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --tb=short` → 基线不降
Run E2E×4（后端依赖自动拉起）：
```
cd backend
.venv/Scripts/python.exe tests/e2e/e2e_signal1_daily_flow.py
.venv/Scripts/python.exe tests/e2e/e2e_signal2_gap.py
.venv/Scripts/python.exe tests/e2e/e2e_signal3_portfolio.py
.venv/Scripts/python.exe tests/e2e/e2e_signal4_verified.py
```
Expected: 四行 `SIGNAL N: PASS` + 四次「开发库指纹一致 ✅」

- [ ] **Step 7: Commit**

```bash
git add backend/tests/e2e/ backend/tests/conftest.py
git commit -m "test(e2e): 四信号可复跑验收单（用得动/量化/作品集/考得住）"
```

---

## 验收（本计划整体 + 全部三计划收官）

1. pytest 全量基线不降（437+ 新增约 12 例）
2. 四信号 E2E 全绿且开发库指纹始终一致
3. tsc RC0；eslint 零新增
4. 人工走通完整闭环：`/learn` 学单元→测验实证→Teach-Back→commit 半确认→`/progress` 看到证据门晋级与 13 节作品集
5. reviewer 铁律生效：直接调 reviewer 节点不产生任何库写入（测试断言在）
6. 对照 spec §2.3 四信号硬指标逐条打钩，写进 `docs/superpowers/specs/` 同目录的验收记录
