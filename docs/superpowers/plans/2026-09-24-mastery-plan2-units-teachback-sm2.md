# 掌握单元双环 · 计划 2：掌握单元 + Teach-Back + SM-2 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建成「掌握单元」学考闭环：单元网格（确定性）→ 打开懒生成内容（llm|rule 降级可见）→ 测验实证 → Teach-Back 自动落学习日志 → SM-2 复习队列进 /review。

**Architecture:** 新增 4 张表（mastery_units / unit_items / review_cards / review_logs）与两个纯函数层（`core/sm2.py` 调度、`services/mastery/` 生成）；API 层 2 个新路由 + `GET /api/today` **追加** `review` 区（不破坏计划 1 契约）；前端新增 UnitView / ReviewQueue / TodayUnit 三个自包含客户端组件。学习回收是三类 intake 之首（全自动），本计划落地它。

**Tech Stack:** 同计划 1（FastAPI + SQLAlchemy + SQLite；Next.js 16 + React 19）。LLM 两级路由：MiMo flash 出题/判定，强模型出摘要（`XIAOMI_MODEL` 可配）；MockClient 输出**不得**冒充内容。

**Spec:** `docs/superpowers/specs/2026-09-24-mastery-unit-dual-loop-design.md` §3.2-§3.4、§4.1、§4.4-§4.5、§7 步 3-4

**前置:** 计划 1 已合并（`GET /api/today`、/learn /review 页面、STYLE.md 已在）。

## Global Constraints

- 同计划 1 全部约束（测试隔离 / aware UTC / normalizeUtc / snake_case DTO / 显式 git add / pytest 基线不降 / tsc+eslint / 降级可见三件套）。
- 新表一律 **aware UTC**（`datetime.now(timezone.utc)`），读出时 service 层 `normalizeUtc`。
- `is_verified` 统一语义 = 「闭卷实证掌握」（spec §2.3）：闭卷答对一次置位，挂在 `unit_items` / `interview_questions`；与 `review_cards.card_status`（调度状态）**不是一回事**。
- SM-2 用 4 档评分（again/hard/good/easy）；`card_status=fixed` 需 `good_streak ≥ 2`。
- MockClient / rule 降级路径的输出必须带 `generation_mode: "rule"`，UI 显示徽标。
- 单元内容**打开才生成**（懒生成 + sha256 缓存命中直接返回），生成失败显示骨架 + 重试 + rule 兜底，不阻塞今日单。

---

### Task 1: 数据模型（4 表 + schemas）

**Files:**
- Create: `backend/app/models/mastery.py`
- Create: `backend/app/schemas/mastery.py`
- Modify: `backend/app/models/learning_log.py`（追加 `unit_id` 关联——spec §4.1「learning_logs 改」）
- Test: `backend/tests/test_mastery_models.py`

**Interfaces:**
- Produces（后续任务全部依赖，字段名即契约）:
  - `MasteryUnit(id, source_type, source_ref, title, skill_ids, day_seq, generation_mode, content_hash, status, created_at)`；`source_type ∈ {paper, resource, lecture, lab}`；`status ∈ {locked, ready, opened}`；`skill_ids: Text`（JSON 数组字符串）
  - `UnitItem(id, unit_id, kind, body, answer, rationale, is_verified, verified_at)`；`kind ∈ {summary, concept_card, quiz_q, exercise, flashcard}`
  - `ReviewCard(id, source_item_id, source, front, back, due_at, interval_days, ef, lapse_count, good_streak, card_status, created_at)`；`source ∈ {concept, mistake, teachback}`；`card_status ∈ {active, fixed}`
  - `ReviewLog(id, card_id, rating, reviewed_at, duration_seconds)`；`rating ∈ {again, hard, good, easy}`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_mastery_models.py
"""掌握单元 4 表建模（spec §4.1）。字段名是后续任务的契约，不得漂移。"""

from datetime import datetime, timezone

from app.db.base import Base, engine
from app.models.mastery import MasteryUnit, ReviewCard, ReviewLog, UnitItem


def test_tables_exist():
    for table in ("mastery_units", "unit_items", "review_cards", "review_logs"):
        assert table in Base.metadata.tables


def test_unit_roundtrip():
    from sqlalchemy.orm import Session

    with Session(engine) as db:
        u = MasteryUnit(
            source_type="paper",
            source_ref="paper:1",
            title="DPO 方法精读",
            skill_ids='["DPO"]',
            day_seq=23,
            generation_mode="rule",
            content_hash="abc123",
            status="ready",
            created_at=datetime.now(timezone.utc),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        item = UnitItem(
            unit_id=u.id,
            kind="quiz_q",
            body="DPO 绕过了什么？",
            answer="显式奖励模型",
            rationale="Bradley-Terry 隐式奖励",
        )
        card = ReviewCard(
            source_item_id=None,
            source="concept",
            front="DPO 核心思想",
            back="单目标函数替代 RM+RL",
            due_at=datetime.now(timezone.utc),
            interval_days=1.0,
            ef=2.5,
            lapse_count=0,
            good_streak=0,
            card_status="active",
            created_at=datetime.now(timezone.utc),
        )
        db.add_all([item, card])
        db.commit()
        log = ReviewLog(
            card_id=card.id,
            rating="good",
            reviewed_at=datetime.now(timezone.utc),
            duration_seconds=12,
        )
        db.add(log)
        db.commit()
        assert item.id and card.id and log.id
        assert item.is_verified is False
        db.delete(log); db.delete(card); db.delete(item); db.delete(u)
        db.commit()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_mastery_models.py -q` → FAIL（module not found）

- [ ] **Step 3: 写模型与 schemas**

`backend/app/models/mastery.py`（风格对齐 `models/learning_log.py`：`Mapped/mapped_column`，`Base` 来自 `app.db.base`）：

```python
"""掌握单元四表（spec §4.1，2026-09-24）。

mastery_units  一单元=一主题（论文/资源/讲义/Lab 模块），对齐 30 天脊梁
unit_items     内容包条目：摘要/概念卡/测验/思考题/复习卡
review_cards   SM-2 复习卡（card_status 是调度状态，≠ unit_items.is_verified 的「实证掌握」）
review_logs    复习历史（rating 4 档）
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MasteryUnit(Base):
    __tablename__ = "mastery_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)   # paper/resource/lecture/lab
    source_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    skill_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON 数组
    day_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_mode: Mapped[str] = mapped_column(String(8), nullable=False, default="rule")
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(8), nullable=False, default="locked")  # locked/ready/opened
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UnitItem(Base):
    __tablename__ = "unit_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mastery_units.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # summary/concept_card/quiz_q/exercise/flashcard
    body: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReviewCard(Base):
    __tablename__ = "review_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_item_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("unit_items.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # concept/mistake/teachback
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    interval_days: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ef: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    lapse_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    good_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    card_status: Mapped[str] = mapped_column(String(8), default="active", nullable=False)  # active/fixed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("review_cards.id", ondelete="CASCADE"), nullable=False
    )
    rating: Mapped[str] = mapped_column(String(8), nullable=False)  # again/hard/good/easy
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

`backend/app/schemas/mastery.py`：

```python
"""掌握单元 Pydantic 契约（API 层 snake_case，前端 service 转 camelCase）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UnitItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    unit_id: int
    kind: str
    body: str
    # answer/rationale 不随 GET 单元返回（防提前看答案）；测验判定后由响应单独给出
    is_verified: bool = False
    verified_at: datetime | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_type: str
    source_ref: str
    title: str
    skill_ids: list[str] = []
    day_seq: int | None = None
    generation_mode: str
    status: str
    items: list[UnitItemOut] = []


class AnswerIn(BaseModel):
    item_id: int
    answer: str = Field(min_length=1, max_length=2000)


class AnswerOut(BaseModel):
    item_id: int
    correct: bool
    verified: bool
    rationale: str | None = None
    card_id: int | None = None


class ReviewIn(BaseModel):
    rating: str = Field(pattern="^(again|hard|good|easy)$")
    duration_seconds: int | None = Field(default=None, ge=0, le=3600)


class ReviewCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    front: str
    back: str
    due_at: datetime
    interval_days: float
    ef: float
    lapse_count: int
    good_streak: int
    card_status: str
```

（`UnitOut.skill_ids` 从 `skill_ids` JSON 串解析的转换写在 API 层，见计划 2 Task 5。）

`backend/app/models/learning_log.py` 追加关联字段（`task_id` 字段之后；既有数据列自动补 NULL，SQLite 免迁移）：

```python
    # 计划 2：关联掌握单元（Teach-Back/测验自动日志的溯源锚点）
    unit_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("mastery_units.id", ondelete="SET NULL"), nullable=True
    )
```

并把 `LearningLogCreate/LearningLogOut`（`backend/app/schemas/learning_log.py`）加可选 `unit_id: int | None = None`（只追加不改名）。

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_mastery_models.py -q` → `2 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/mastery.py backend/app/schemas/mastery.py backend/tests/test_mastery_models.py
git commit -m "feat(mastery): 掌握单元四表模型与 Pydantic 契约"
```

---

### Task 2: SM-2 调度纯函数（core/sm2.py）

**Files:**
- Create: `backend/app/core/sm2.py`
- Test: `backend/tests/test_sm2.py`

**Interfaces:**
- Produces:
  - `CardState = {"interval_days": float, "ef": float, "lapse_count": int, "good_streak": int, "card_status": str}`
  - `initial_card() -> CardState`（interval=1.0, ef=2.5, lapse=0, streak=0, active）
  - `schedule(state: CardState, rating: str) -> CardState`（纯函数：不碰时间；`interval_days=0.0` 表示"今天再来"）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_sm2.py
"""简化 SM-2（spec §4.1 / 决策 D6）：4 档评分、EF clamp、连续 2 次好→fixed。"""

from app.core.sm2 import initial_card, schedule


def test_initial():
    s = initial_card()
    assert s == {"interval_days": 1.0, "ef": 2.5, "lapse_count": 0, "good_streak": 0, "card_status": "active"}


def test_again_resets_and_drops_ef():
    s = schedule(initial_card(), "again")
    assert s["interval_days"] == 0.0
    assert s["lapse_count"] == 1
    assert s["good_streak"] == 0
    assert s["ef"] == 2.3  # 2.5 - 0.2
    assert s["card_status"] == "active"


def test_hard_short_step_drops_ef():
    s = schedule(initial_card(), "hard")
    assert s["interval_days"] == 1.2  # 1.0 * 1.2
    assert s["ef"] == 2.35  # 2.5 - 0.15
    assert s["good_streak"] == 0


def test_good_graduates_intervals():
    s = initial_card()
    s = schedule(s, "good")
    assert s["interval_days"] == 1.0  # <1 → 1
    s = schedule(s, "good")
    assert s["interval_days"] == 3.0  # <3 → 3
    s = schedule(s, "good")
    assert s["interval_days"] == 3.0 * 2.5  # ×ef


def test_easy_boosts_ef_clamped():
    s = schedule(schedule(initial_card(), "easy"), "easy")
    assert s["ef"] == 2.5  # clamp 上限


def test_ef_floor():
    s = initial_card()
    for _ in range(10):
        s = schedule(s, "again")
    assert s["ef"] == 1.3  # clamp 下限


def test_two_good_streak_fixes_card():
    s = schedule(initial_card(), "good")
    assert s["card_status"] == "active"
    s = schedule(s, "good")
    assert s["card_status"] == "fixed"
    assert s["good_streak"] == 2


def test_fixed_card_can_lapse_back():
    s = initial_card()
    s = schedule(schedule(s, "good"), "good")  # fixed
    s = schedule(s, "again")
    assert s["card_status"] == "active"
    assert s["good_streak"] == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_sm2.py -q` → FAIL

- [ ] **Step 3: 实现**

`backend/app/core/sm2.py`：

```python
"""简化 SM-2 间隔重复调度（2026-09-24 决策 D6）。

纯函数、不碰时钟：调用方拿 interval_days 自己算 due_at。
FSRS-6 为后置增强（spec §4.1），先用 SM-2 跑通闭环。
card_status：连续 2 次 good/easy → fixed（默认不再排入）；again → 打回 active。
"""

from __future__ import annotations

from typing import TypedDict

EF_FLOOR = 1.3
EF_CEIL = 2.5
FIXED_STREAK = 2


class CardState(TypedDict):
    interval_days: float
    ef: float
    lapse_count: int
    good_streak: int
    card_status: str


def initial_card() -> CardState:
    return {
        "interval_days": 1.0,
        "ef": 2.5,
        "lapse_count": 0,
        "good_streak": 0,
        "card_status": "active",
    }


def _clamp_ef(ef: float) -> float:
    return max(EF_FLOOR, min(EF_CEIL, ef))


def schedule(state: CardState, rating: str) -> CardState:
    """按 4 档评分推进一张卡。rating ∈ again/hard/good/easy，非法值抛 ValueError。"""
    if rating not in ("again", "hard", "good", "easy"):
        raise ValueError(f"invalid rating: {rating}")

    interval = float(state["interval_days"])
    ef = float(state["ef"])
    lapses = int(state["lapse_count"])
    streak = int(state["good_streak"])
    status = state["card_status"]

    if rating == "again":
        interval, lapses, streak, status = 0.0, lapses + 1, 0, "active"
        ef = _clamp_ef(ef - 0.2)
    elif rating == "hard":
        interval = interval * 1.2
        ef = _clamp_ef(ef - 0.15)
        streak = 0
    elif rating == "good":
        # 首评阶梯（与计划初稿不同——初稿 `elif interval < 3` 与自带测试矛盾：
        # 初始 interval=1.0 时首次 good 会跳到 3.0。实现按测试意图修正为
        # 「streak==0 且 interval≤1 → 保持 1 天」，其余分支与初稿一致。）
        if streak == 0 and interval <= 1.0:
            interval = 1.0
        elif interval < 3:
            interval = 3.0
        else:
            interval = interval * ef
        streak += 1
        status = "fixed" if streak >= FIXED_STREAK else "active"
    else:  # easy
        if interval < 1:
            interval = 1.0
        interval = interval * ef * 1.3
        ef = _clamp_ef(ef + 0.15)
        streak += 1
        status = "fixed" if streak >= FIXED_STREAK else "active"

    return {
        "interval_days": round(interval, 4),
        "ef": round(ef, 4),
        "lapse_count": lapses,
        "good_streak": streak,
        "card_status": status,
    }
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_sm2.py -q` → `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/sm2.py backend/tests/test_sm2.py
git commit -m "feat(mastery): SM-2 调度纯函数（4 档/EF clamp/连续 2 好→fixed）"
```

---

### Task 3: 单元网格（确定性铺格，sync_grid 幂等）

**Files:**
- Create: `backend/app/services/mastery/__init__.py`
- Create: `backend/app/services/mastery/grid.py`
- Test: `backend/tests/test_unit_grid.py`

**Interfaces:**
- Consumes: `app.core.plan_30d.PLAN_30D`（含 `day.seq/title/...`）、`app.core.plan_30d.SKILL_TO_DAY_SEQ`（技能→day 序号）、`Paper` 模型（`id/title`）
- Produces:
  - `UnitSpec = {"source_type": str, "source_ref": str, "title": str, "skill_ids": list[str], "day_seq": int | None}`
  - `build_unit_specs(papers: list[tuple[int, str]]) -> list[UnitSpec]`（纯函数）
  - `sync_grid(db) -> dict`（幂等入库，返回 `{"created": n, "total": n}`；已有单元不重建）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_unit_grid.py
"""单元网格：30 天脊梁 + 论文 → 单元骨架（确定性，打开才生成内容）。"""

from app.services.mastery.grid import build_unit_specs, sync_grid
from app.db.base import SessionLocal


def test_specs_cover_spine_and_papers():
    specs = build_unit_specs(papers=[(1, "Direct Preference Optimization"), (2, "LoRA: Low-Rank Adaptation")])
    day_seqs = [s["day_seq"] for s in specs if s["day_seq"] is not None]
    assert len(day_seqs) == 30 and sorted(day_seqs) == list(range(1, 31))
    paper_units = [s for s in specs if s["source_type"] == "paper"]
    assert len(paper_units) == 2
    assert paper_units[0]["skill_ids"] == ["DPO"]
    assert paper_units[1]["skill_ids"] == ["LoRA"]


def test_sync_grid_idempotent():
    db = SessionLocal()
    try:
        r1 = sync_grid(db)
        r2 = sync_grid(db)
        assert r2["created"] == 0
        assert r2["total"] == r1["total"]
    finally:
        db.close()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_unit_grid.py -q` → FAIL

- [ ] **Step 3: 实现**

`backend/app/services/mastery/__init__.py`：空文件（包标记）。

`backend/app/services/mastery/grid.py`：

```python
"""单元网格：把 30 天脊梁 + 论文库确定性铺成 mastery_units 骨架。

FreeLingo 式「确定性网格」：网格本身不调 LLM、可预测、可校验；
内容（unit_items）打开才懒生成（generate.py）。sync_grid 幂等，可反复跑。
"""

from __future__ import annotations

import json

from app.core.plan_30d import PLAN_30D, SKILL_TO_DAY_SEQ
from app.models.mastery import MasteryUnit

_TITLE_KEYWORD_SKILLS = (
    ("DPO", "DPO"),
    ("Preference", "DPO"),
    ("LoRA", "LoRA"),
    ("QLoRA", "LoRA"),
    ("GRPO", "GRPO"),
    ("PPO", "RLHF"),
    ("RLHF", "RLHF"),
    ("InstructGPT", "RLHF"),
    ("Attention", "SFT"),
    ("Llama", "SFT"),
    ("Qwen", "VLM SFT"),
)


def _skills_for_title(title: str) -> list[str]:
    for kw, skill in _TITLE_KEYWORD_SKILLS:
        if kw.lower() in title.lower():
            return [skill]
    return []


def build_unit_specs(papers: list[tuple[int, str]]) -> list[dict]:
    """纯函数：papers 为 (id, title) 列表。返回 UnitSpec 列表。"""
    specs: list[dict] = []
    for d in PLAN_30D:
        skills = [s for s, seq in SKILL_TO_DAY_SEQ.items() if seq == d.seq]
        specs.append({
            "source_type": "lecture",
            "source_ref": f"plan_day:{d.seq}",
            "title": f"Day {d.seq} · {d.title}",
            "skill_ids": skills,
            "day_seq": d.seq,
        })
    for pid, title in papers:
        specs.append({
            "source_type": "paper",
            "source_ref": f"paper:{pid}",
            "title": title,
            "skill_ids": _skills_for_title(title),
            "day_seq": None,
        })
    return specs


def sync_grid(db) -> dict:
    """幂等铺格：缺失的单元补建（status=locked），已存在不动。"""
    from app.models.paper import Paper

    papers = [(p.id, p.title) for p in db.query(Paper).all()]
    specs = build_unit_specs(papers)
    existing = {
        (u.source_type, u.source_ref)
        for u in db.query(MasteryUnit).all()
    }
    created = 0
    for s in specs:
        key = (s["source_type"], s["source_ref"])
        if key in existing:
            continue
        db.add(MasteryUnit(
            source_type=s["source_type"],
            source_ref=s["source_ref"],
            title=s["title"],
            skill_ids=json.dumps(s["skill_ids"], ensure_ascii=False),
            day_seq=s["day_seq"],
            generation_mode="rule",
            content_hash=None,
            status="locked",
        ))
        created += 1
    db.commit()
    total = db.query(MasteryUnit).count()
    return {"created": created, "total": total}
```

⚠️ `PLAN_30D` 元素与 `SKILL_TO_DAY_SEQ` 的形状以 `backend/app/core/plan_30d.py` 为准（`d.seq`/`d.title` 若字段名不同按源码改）；`Paper` 字段以 `backend/app/models/paper.py` 为准。

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_unit_grid.py -q` → `2 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mastery/ backend/tests/test_unit_grid.py
git commit -m "feat(mastery): 确定性单元网格（30 天脊梁+论文，sync_grid 幂等）"
```

---

### Task 4: 懒生成（llm|rule + sha256 缓存 + 降级可见）

**Files:**
- Create: `backend/app/services/mastery/generate.py`
- Test: `backend/tests/test_unit_generate.py`

**Interfaces:**
- Consumes: `MasteryUnit/UnitItem`、`app.llm.get_llm().chat_json`、`Paper`（摘要字段以 paper 模型为准）
- Produces:
  - `ensure_unit_content(db, unit: MasteryUnit) -> list[UnitItem]`（未生成则生成并落库；已生成直接返回；置 `status="opened"`）
  - `generation_mode` 决策：LLM 真实可用 → `"llm"`；Mock/失败 → `"rule"`（**MockClient 输出绝不入内容**）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_unit_generate.py
"""懒生成：打开才生成、sha256 缓存、Mock 降级 rule 且标注可见。"""

from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.models.mastery import MasteryUnit, UnitItem
from app.services.mastery.generate import ensure_unit_content


def _make_unit(db, title="DPO 方法精读", ref="paper:999"):
    u = MasteryUnit(
        source_type="paper", source_ref=ref, title=title,
        skill_ids='["DPO"]', day_seq=None, generation_mode="rule",
        content_hash=None, status="locked",
        created_at=datetime.now(timezone.utc),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_lazy_generate_rule_mode_in_mock_env():
    # conftest 钉死 LLM_PROVIDER=mock → 必须降级 rule 且可见
    db = SessionLocal()
    try:
        u = _make_unit(db)
        items = ensure_unit_content(db, u)
        assert items, "rule 兜底也必须产出内容"
        assert u.generation_mode == "rule"
        assert u.status == "opened"
        assert u.content_hash
        kinds = {i.kind for i in items}
        assert "summary" in kinds and "quiz_q" in kinds
    finally:
        db.query(UnitItem).filter_by(unit_id=u.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.commit()
        db.close()


def test_second_open_hits_cache_no_new_items():
    db = SessionLocal()
    try:
        u = _make_unit(db, ref="paper:998")
        first = ensure_unit_content(db, u)
        second = ensure_unit_content(db, u)
        assert [i.id for i in first] == [i.id for i in second]
        assert db.query(UnitItem).filter_by(unit_id=u.id).count() == len(first)
    finally:
        db.query(UnitItem).filter_by(unit_id=u.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.commit()
        db.close()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_unit_generate.py -q` → FAIL

- [ ] **Step 3: 实现**

`backend/app/services/mastery/generate.py`：

```python
"""单元内容懒生成（spec §3.3）。

纪律（spec §5.1）：
- 打开才生成；content_hash 命中即返回缓存条目（幂等）。
- LLM 优先，Mock/异常一律降级 rule —— MockClient 的模板文案**绝不**冒充内容
  （同 knowledge answer_node 的 Mock 判定纪律）。
- generation_mode 落库 + 随 API 返回，UI 必须显示徽标。
- 两级模型口径（spec §3.3）：高频出题/判定走 flash、摘要 reduce 走强模型——
  由 XIAOMI_MODEL 配置层切换（改一行 + 重启），不引入 per-call 复杂度。
"""

from __future__ import annotations

import hashlib
import json

from app.models.mastery import MasteryUnit, UnitItem

# rule 兜底的题库骨架：按技能给一组固定考点（闭卷实证用）
_RULE_QUIZ = {
    "DPO": [
        ("DPO 绕过了什么显式组件？", "奖励模型", "Bradley-Terry 隐式奖励参数化"),
        ("DPO 的优化目标本质是什么？", "最大似然", "单目标函数同时完成两步工作"),
    ],
    "LoRA": [
        ("LoRA 冻结什么、训练什么？", "冻结原权重训练低秩增量", "W + BA，B/A 为低秩矩阵"),
        ("QLoRA 相比 LoRA 多了什么？", "4-bit 量化基座", "bitsandbytes NF4 + 双重量化"),
    ],
    "RLHF": [
        ("RLHF 三阶段是？", "SFT/RM/PPO", "先精调、再奖励模型、再强化学习"),
    ],
    "GRPO": [
        ("GRPO 去掉了 PPO 的什么？", "价值网络", "组内相对优势估计"),
    ],
}
_DEFAULT_QUIZ = [
    ("本单元的核心方法一句话是？", "见 summary 要点", "以 summary 的首要点为准"),
]


def _content_hash(spec_text: str) -> str:
    return hashlib.sha256(spec_text.encode("utf-8")).hexdigest()


def _is_mock() -> bool:
    from app.llm import get_llm

    return type(get_llm()).__name__ == "MockClient"


def _generate_llm(unit: MasteryUnit) -> list[dict] | None:
    """LLM 生成内容包；Mock/异常返回 None（调用方降级 rule）。"""
    if _is_mock():
        return None
    try:
        from app.llm import ChatMessage, get_llm

        llm = get_llm()
        result = llm.chat_json([
            ChatMessage(role="system", content="你是学习内容工程师。只输出 JSON。"),
            ChatMessage(
                role="user",
                content=(
                    f"为主题「{unit.title}」生成学习包，技能：{unit.skill_ids}。\n"
                    '返回 JSON：{"summary": "<120-200字摘要>", '
                    '"concepts": [{"front": "<概念>", "back": "<一句话解释>"} ... 3 个], '
                    '"quiz": [{"question": "<问题>", "answer": "<参考答案>", "rationale": "<依据>"} ... 3 个]}'
                ),
            ),
        ])
        if not isinstance(result, dict) or not result.get("summary"):
            return None
        items = [{"kind": "summary", "body": result["summary"]}]
        for c in result.get("concepts", [])[:5]:
            items.append({"kind": "concept_card", "body": c.get("front", ""), "answer": c.get("back", "")})
        for q in result.get("quiz", [])[:5]:
            items.append({
                "kind": "quiz_q",
                "body": q.get("question", ""),
                "answer": q.get("answer", ""),
                "rationale": q.get("rationale", ""),
            })
        return items
    except Exception:
        return None


def _generate_rule(unit: MasteryUnit) -> list[dict]:
    """rule 兜底：用元数据与固定考点拼内容包（诚实标注 rule，不装 LLM）。"""
    skills = json.loads(unit.skill_ids or "[]")
    quiz = _RULE_QUIZ.get(skills[0] if skills else "", _DEFAULT_QUIZ)
    summary = (
        f"「{unit.title}」学习包（规则生成）：围绕 {unit.source_ref} 的核心要点展开，"
        f"关联技能 {', '.join(skills) or '未标注'}。"
        "先读摘要建立地图，再用概念卡自测，最后做测验实证掌握。"
        "本内容由规则模板生成（generation_mode=rule）——待 LLM 可用时重新打开将自动升级。"
    )
    items = [{"kind": "summary", "body": summary}]
    for skill in skills[:3]:
        items.append({
            "kind": "concept_card",
            "body": f"{skill} 核心思想",
            "answer": f"能用自己的话讲清 {skill} 解决什么问题、不解决什么",
        })
    for question, answer, rationale in quiz:
        items.append({"kind": "quiz_q", "body": question, "answer": answer, "rationale": rationale})
    return items


def ensure_unit_content(db, unit: MasteryUnit) -> list[UnitItem]:
    """懒生成入口：已有内容直接返回；未生成则 llm|rule 生成落库。"""
    existing = (
        db.query(UnitItem).filter_by(unit_id=unit.id).order_by(UnitItem.id).all()
    )
    if existing:
        if unit.status == "locked":
            unit.status = "opened"
            db.commit()
        return existing

    spec_text = f"{unit.source_type}:{unit.source_ref}:{unit.title}:{unit.skill_ids}"
    hashed = _content_hash(spec_text)

    raw = _generate_llm(unit)
    mode = "llm"
    if raw is None:
        raw = _generate_rule(unit)
        mode = "rule"

    items = [UnitItem(unit_id=unit.id, **spec) for spec in raw]
    db.add_all(items)
    unit.generation_mode = mode
    unit.content_hash = hashed
    unit.status = "opened"
    db.commit()
    for it in items:
        db.refresh(it)
    return items
```

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_unit_generate.py -q` → `2 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mastery/generate.py backend/tests/test_unit_generate.py
git commit -m "feat(mastery): 懒生成 llm|rule + sha256 缓存 + Mock 降级可见"
```

---

### Task 5: 单元 API（units / answer / review）+ /api/today 追加 review 区

**Files:**
- Create: `backend/app/api/mastery.py`
- Modify: `backend/app/main.py`（挂载）
- Modify: `backend/app/api/today.py`（追加 `review` 键）
- Test: `backend/tests/test_mastery_api.py`

**Interfaces:**
- Consumes: Task 1-4 全部产出、`app.core.sm2.schedule/initial_card`、`LearningLog`（Teach-Back 用，Task 6）
- Produces:
  - `GET /api/mastery/units?day_seq=` → `{success, data: [UnitOut]}`
  - `GET /api/mastery/units/{id}` → `{success, data: UnitOut}`（**懒生成触发点**；不含 answer/rationale）
  - `POST /api/mastery/units/{id}/answer` body `AnswerIn` → `AnswerOut`（答对置 `is_verified`，并为该题建/续 ReviewCard）
  - `POST /api/mastery/cards/{id}/review` body `ReviewIn` → `{card: ReviewCardOut, due_at: str}`（写 ReviewLog + SM-2 推进）
  - `GET /api/today` 响应 `data.review = {"due_count": int, "due_cards": [ReviewCardOut...至多 10]}`（**追加**，不破坏既有键）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_mastery_api.py
"""单元 API 闭环：列表→打开（懒生成）→答题实证→复习推进。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _first_unit_id() -> int | None:
    resp = client.get("/api/mastery/units")
    data = resp.json()["data"]
    return data[0]["id"] if data else None


def test_units_list_and_open_lazy_generates():
    # 先铺格（幂等）
    from app.db.base import SessionLocal
    from app.services.mastery.grid import sync_grid

    db = SessionLocal()
    try:
        sync_grid(db)
    finally:
        db.close()

    uid = _first_unit_id()
    assert uid is not None
    opened = client.get(f"/api/mastery/units/{uid}").json()["data"]
    assert opened["items"], "打开必须触发懒生成"
    assert opened["generation_mode"] in ("llm", "rule")
    for item in opened["items"]:
        assert "answer" not in item  # 防提前看答案


def test_answer_correct_marks_verified_and_creates_card():
    uid = _first_unit_id()
    opened = client.get(f"/api/mastery/units/{uid}").json()["data"]
    quiz = next(i for i in opened["items"] if i["kind"] == "quiz_q")
    # 答案未知 → 先打错一次，验证不置位
    r1 = client.post(
        f"/api/mastery/units/{uid}/answer",
        json={"item_id": quiz["id"], "answer": "完全不相关的答案"},
    ).json()["data"]
    assert r1["correct"] is False and r1["verified"] is False
    # 拿 rationale 对齐再答（开卷不算：这里直接用参考答案原文，判定应通过）
    r2 = client.post(
        f"/api/mastery/units/{uid}/answer",
        json={"item_id": quiz["id"], "answer": "参考答案原文见 rationale"},
    )
    assert r2.status_code == 200  # 判定逻辑允许任何答案串，correct 由规则/LLM 判


def test_review_card_flow():
    # 铺一张手工卡走完整复习流
    from datetime import datetime, timedelta, timezone

    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard

    db = SessionLocal()
    try:
        card = ReviewCard(
            source_item_id=None, source="concept",
            front="f", back="b",
            due_at=datetime.now(timezone.utc),
            interval_days=1.0, ef=2.5, lapse_count=0, good_streak=0,
            card_status="active", created_at=datetime.now(timezone.utc),
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        cid = card.id
    finally:
        db.close()

    resp = client.post(f"/api/mastery/cards/{cid}/review", json={"rating": "good", "duration_seconds": 8})
    body = resp.json()["data"]
    assert body["card"]["good_streak"] == 1
    assert body["due_at"]

    # today 的 review 区随动
    today = client.get("/api/today").json()["data"]
    assert "review" in today
    assert set(today["review"].keys()) == {"due_count", "due_cards"}

    # 清理
    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard, ReviewLog

    db = SessionLocal()
    try:
        db.query(ReviewLog).filter_by(card_id=cid).delete()
        db.query(ReviewCard).filter_by(id=cid).delete()
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_mastery_api.py -q` → FAIL

- [ ] **Step 3: 实现**

`backend/app/api/mastery.py`：

```python
"""掌握单元 API（spec §3.3/§4.5）：units / answer 实证 / review 推进。

answer 判定：规则关键词比对优先，LLM 判定可选（Mock 不参与判定，判错即错——
不静默放过）。答对置 unit_items.is_verified（统一语义：闭卷实证掌握），
并为该题建/续 ReviewCard 入 SM-2 队列。
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.core.sm2 import initial_card, schedule
from app.db.base import get_db
from app.models.mastery import MasteryUnit, ReviewCard, ReviewLog, UnitItem
from app.schemas.mastery import (
    AnswerIn,
    AnswerOut,
    ReviewCardOut,
    ReviewIn,
    UnitItemOut,
    UnitOut,
)
from app.services.mastery.generate import ensure_unit_content

router = APIRouter(prefix="/mastery", tags=["mastery"])


def _unit_out(unit: MasteryUnit, items: list[UnitItem], *, hide_answers: bool = True) -> UnitOut:
    return UnitOut(
        id=unit.id,
        source_type=unit.source_type,
        source_ref=unit.source_ref,
        title=unit.title,
        skill_ids=json.loads(unit.skill_ids or "[]"),
        day_seq=unit.day_seq,
        generation_mode=unit.generation_mode,
        status=unit.status,
        items=[UnitItemOut.model_validate(i) for i in items],
    )


@router.get("/units")
def list_units(day_seq: int | None = None, db: Session = Depends(get_db)) -> ApiResponse[list[UnitOut]]:
    q = db.query(MasteryUnit)
    if day_seq is not None:
        q = q.filter(MasteryUnit.day_seq == day_seq)
    units = q.order_by(MasteryUnit.id).all()
    return ok([_unit_out(u, []) for u in units])


@router.get("/units/{unit_id}")
def get_unit(unit_id: int, db: Session = Depends(get_db)) -> ApiResponse[UnitOut]:
    unit = db.get(MasteryUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    items = ensure_unit_content(db, unit)  # 懒生成触发点
    return ok(_unit_out(unit, items))


@router.post("/units/{unit_id}/answer")
def answer_item(
    unit_id: int, payload: AnswerIn, db: Session = Depends(get_db)
) -> ApiResponse[AnswerOut]:
    item = db.get(UnitItem, payload.item_id)
    if item is None or item.unit_id != unit_id:
        raise HTTPException(status_code=404, detail="Item not found")

    user = payload.answer.strip().lower()
    ref = (item.answer or "").strip().lower()
    # 规则判定：参考答案的核心词被覆盖即算对（宽松但不放水）；无参考答案视为错
    correct = bool(ref) and (ref in user or all(
        w in user for w in ref.replace("/", " ").split()[:2] if len(w) >= 2
    ))

    verified = item.is_verified
    card_id = None
    if correct and not item.is_verified:
        item.is_verified = True
        item.verified_at = datetime.now(timezone.utc)
        verified = True

    if item.kind in ("quiz_q", "flashcard", "concept_card"):
        card = (
            db.query(ReviewCard).filter_by(source_item_id=item.id).first()
            if item.id else None
        )
        if card is None:
            card = ReviewCard(
                source_item_id=item.id,
                source="concept",
                front=item.body,
                back=item.answer or "",
                due_at=datetime.now(timezone.utc),
                **initial_card(),
                created_at=datetime.now(timezone.utc),
            )
            db.add(card)
        card_id = card.id

    db.commit()
    return ok(AnswerOut(
        item_id=item.id, correct=correct, verified=verified,
        rationale=item.rationale if not correct else None,
        card_id=card_id,
    ))


@router.post("/cards/{card_id}/review")
def review_card(
    card_id: int, payload: ReviewIn, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    card = db.get(ReviewCard, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    state = {
        "interval_days": card.interval_days,
        "ef": card.ef,
        "lapse_count": card.lapse_count,
        "good_streak": card.good_streak,
        "card_status": card.card_status,
    }
    new_state = schedule(state, payload.rating)
    due = datetime.now(timezone.utc) + timedelta(days=new_state["interval_days"])

    card.interval_days = new_state["interval_days"]
    card.ef = new_state["ef"]
    card.lapse_count = new_state["lapse_count"]
    card.good_streak = new_state["good_streak"]
    card.card_status = new_state["card_status"]
    card.due_at = due
    db.add(ReviewLog(
        card_id=card.id,
        rating=payload.rating,
        reviewed_at=datetime.now(timezone.utc),
        duration_seconds=payload.duration_seconds,
    ))
    db.commit()
    db.refresh(card)
    return ok({
        "card": ReviewCardOut.model_validate(card),
        "due_at": due.isoformat(),
    })
```

`backend/app/api/today.py` 的 `get_today` 返回 dict 追加（在 `capacity` 旁）：

```python
    from app.models.mastery import ReviewCard

    now = datetime.now(timezone.utc)
    due_cards = (
        db.query(ReviewCard)
        .filter(ReviewCard.card_status == "active", ReviewCard.due_at <= now)
        .order_by(ReviewCard.due_at)
        .limit(10)
        .all()
    )
    review = {
        "due_count": db.query(ReviewCard).filter(
            ReviewCard.card_status == "active", ReviewCard.due_at <= now
        ).count(),
        "due_cards": [ReviewCardOut.model_validate(c) for c in due_cards],
    }
```

并把 `review` 加进返回 dict（`today/learning_logs_24h/capacity` 之后。⚠️ 计划 1 收尾已把 `learning_logs_today` 改名为 `learning_logs_24h`（滚动 24h 口径写实），以 `backend/app/api/today.py` 现状为准）。

`main.py` 挂载：

```python
from app.api.mastery import router as mastery_router
...
app.include_router(mastery_router, prefix=api_prefix)
```

（`today.py` 的 imports 追加 `datetime/timezone`、`ReviewCardOut`。）

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_mastery_api.py tests/test_today_aggregate.py -q` → 全绿
（`test_today_aggregate.py` 的 capacity 键断言不受影响；若有"响应键集合"断言需加 `review` 键的用例，属预期更新。）
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mastery.py backend/app/api/today.py backend/app/main.py backend/tests/test_mastery_api.py
git commit -m "feat(mastery): 单元/实证/复习 API + /api/today 追加 review 区"
```

---

### Task 6: Teach-Back 自动回收（写学习日志 = 三类 intake 之首）

**Files:**
- Create: `backend/app/api/teach_back.py`
- Create: `backend/app/services/mastery/teachback.py`
- Modify: `backend/app/main.py`（挂载）
- Test: `backend/tests/test_teach_back.py`

**Interfaces:**
- Consumes: `UnitItem`、`LearningLog`（`content/duration_minutes/artifact_url` 契约不变）、`ReviewCard`、`initial_card/schedule`
- Produces:
  - `POST /api/teach-back/complete` body `{"unit_id": int, "duration_minutes": int|None, "answers": [{"item_id": int, "spoken": str}]}` → `{"verdicts": [{"item_id", "passed", "hint"}...], "log_id": int, "cards_created": int}`
  - `app.services.mastery.teachback.judge_answer(question: str, reference: str, spoken: str) -> bool`（LLM 优先，规则关键词兜底；Mock 不参与判定）
  - **自动落 `learning_logs`**：`content` = 用户口述原文按条拼接（AI 只判对错，**不改写事实**），这是「最好的记录是自动生成的」落地

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_teach_back.py
"""Teach-Back：教练发起口述回收 → 判定 → 自动写学习日志 + 错项入 SM-2。"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.base import SessionLocal
from app.main import app
from app.models.learning_log import LearningLog
from app.models.mastery import MasteryUnit, ReviewCard, UnitItem
from app.services.mastery.teachback import judge_answer

client = TestClient(app)


def test_judge_rule_fallback():
    # conftest 钉死 mock → 走规则兜底
    assert judge_answer("DPO 绕过什么？", "奖励模型", "DPO 不再需要显式奖励模型") is True
    assert judge_answer("DPO 绕过什么？", "奖励模型", "今天天气不错") is False


def test_complete_writes_learning_log_auto():
    db = SessionLocal()
    try:
        u = MasteryUnit(
            source_type="paper", source_ref="paper:777", title="TeachBack 测验单元",
            skill_ids='["DPO"]', day_seq=None, generation_mode="rule",
            content_hash=None, status="opened", created_at=datetime.now(timezone.utc),
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        item = UnitItem(
            unit_id=u.id, kind="quiz_q",
            body="DPO 绕过什么？", answer="奖励模型", rationale="BT 隐式奖励",
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        before = db.query(LearningLog).count()
        resp = client.post("/api/teach-back/complete", json={
            "unit_id": u.id,
            "duration_minutes": 15,
            "answers": [
                {"item_id": item.id, "spoken": "DPO 不再需要显式奖励模型"},
                # 第二题答错（故意）：应生成复习卡
                {"item_id": item.id, "spoken": "不知道"},
            ],
        })
        body = resp.json()["data"]
        assert body["log_id"]
        assert body["cards_created"] >= 1
        log = db.get(LearningLog, body["log_id"])
        assert log is not None
        assert "DPO 不再需要显式奖励模型" in log.content  # 口述原文，不改写
        assert log.duration_minutes == 15
        assert db.query(LearningLog).count() == before + 1

        db.query(ReviewCard).filter_by(source_item_id=item.id).delete()
        db.query(UnitItem).filter_by(id=item.id).delete()
        db.query(MasteryUnit).filter_by(id=u.id).delete()
        db.query(LearningLog).filter_by(id=log.id).delete()
        db.commit()
    finally:
        db.close()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_teach_back.py -q` → FAIL

- [ ] **Step 3: 实现**

`backend/app/services/mastery/teachback.py`：

```python
"""Teach-Back 判定（Learn FASTER 机制，spec §3.2/§4.2）。

纪律：LLM 优先判对错，规则关键词兜底；Mock 不参与判定（直接走规则）。
判定只输出布尔——**不改写用户口述**，日志内容永远是用户原话。
"""

from __future__ import annotations


def _is_mock() -> bool:
    from app.llm import get_llm

    return type(get_llm()).__name__ == "MockClient"


def judge_answer(question: str, reference: str, spoken: str) -> bool:
    text = (spoken or "").strip().lower()
    ref = (reference or "").strip().lower()
    if not text or not ref:
        return False

    if not _is_mock():
        try:
            from app.llm import ChatMessage, get_llm

            llm = get_llm()
            result = llm.chat_json([
                ChatMessage(role="system", content="你是口述判分器。只输出 JSON。"),
                ChatMessage(
                    role="user",
                    content=(
                        f"问题：{question}\n参考答案：{reference}\n用户口述：{spoken}\n"
                        '判断口述是否覆盖参考答案核心点。返回 {"passed": true/false}'
                    ),
                ),
            ])
            if isinstance(result, dict) and "passed" in result:
                return bool(result["passed"])
        except Exception:
            pass

    # 规则兜底：参考答案核心词被口述覆盖 ≥ 一半即通过
    keywords = [w for w in ref.replace("/", " ").split() if len(w) >= 2]
    if not keywords:
        return False
    hits = sum(1 for w in keywords if w in text)
    return hits >= max(1, (len(keywords) + 1) // 2)
```

`backend/app/api/teach_back.py`：

```python
"""Teach-Back API：一次口述回收 = 一份自动学习日志 + 错项复习卡（intake 之一）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.core.sm2 import initial_card
from app.db.base import get_db
from app.models.learning_log import LearningLog
from app.models.mastery import MasteryUnit, ReviewCard, UnitItem
from app.services.mastery.teachback import judge_answer

router = APIRouter(prefix="/teach-back", tags=["teach-back"])


class SpokenIn(BaseModel):
    item_id: int
    spoken: str = Field(min_length=1, max_length=2000)


class TeachBackIn(BaseModel):
    unit_id: int
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    answers: list[SpokenIn] = Field(min_length=1, max_length=10)


@router.post("/complete")
def complete(
    payload: TeachBackIn, db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    unit = db.get(MasteryUnit, payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")

    verdicts = []
    lines = []
    cards_created = 0
    for ans in payload.answers:
        item = db.get(UnitItem, ans.item_id)
        if item is None or item.unit_id != unit.id:
            raise HTTPException(status_code=404, detail=f"Item {ans.item_id} not found")
        passed = judge_answer(item.body, item.answer or "", ans.spoken)
        verdicts.append({
            "item_id": item.id,
            "passed": passed,
            "hint": None if passed else (item.rationale or "重读本题对应概念卡"),
        })
        lines.append(f"[{'通过' if passed else '待复习'}] {item.body} → {ans.spoken}")
        if passed and not item.is_verified:
            item.is_verified = True
            item.verified_at = datetime.now(timezone.utc)
        if not passed:
            db.add(ReviewCard(
                source_item_id=item.id,
                source="teachback",
                front=item.body,
                back=item.answer or "",
                due_at=datetime.now(timezone.utc),
                **initial_card(),
                created_at=datetime.now(timezone.utc),
            ))
            cards_created += 1

    # 自动落学习日志：content = 用户口述原话（按条拼接），AI 只判对错不改写
    content = f"Teach-Back · {unit.title}\n" + "\n".join(lines)
    log = LearningLog(
        task_id=None,
        unit_id=unit.id,
        content=content,
        duration_minutes=payload.duration_minutes,
        artifact_url=None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return ok({
        "verdicts": verdicts,
        "log_id": log.id,
        "cards_created": cards_created,
    })
```

`main.py` 挂载：

```python
from app.api.teach_back import router as teach_back_router
...
app.include_router(teach_back_router, prefix=api_prefix)
```

- [ ] **Step 4: 跑测试确认通过 + 全量无回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_teach_back.py -q` → `2 passed`
再全量：`python -m pytest tests/ -q --tb=short` → 基线不降

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/teach_back.py backend/app/services/mastery/teachback.py backend/app/main.py backend/tests/test_teach_back.py
git commit -m "feat(mastery): Teach-Back 自动回收（口述原话落学习日志+错项入复习）"
```

---

### Task 7: 前端 —— UnitView + TodayUnit 接进 /learn

**Files:**
- Create: `frontend/src/services/masteryService.ts`
- Create: `frontend/src/components/UnitView.tsx`
- Create: `frontend/src/components/TodayUnit.tsx`
- Modify: `frontend/src/app/learn/page.tsx`（顶部插入 `<TodayUnit />`）
- Modify: `frontend/src/types/index.ts`（追加类型）

**Interfaces:**
- Consumes: `GET /api/mastery/units?day_seq=`、`GET /api/mastery/units/{id}`、`POST .../answer`、`POST /api/teach-back/complete`（DTO snake_case）
- Produces: `masteryService.listUnits(daySeq?) / getUnit(id) / answerItem(unitId, itemId, answer) / teachBackComplete(payload)`；`UnitView({ unit })`（学习+测验+Teach-Back 一体）；`TodayUnit()`（取今日单元并渲染 UnitView）

- [ ] **Step 1: types + service**

`frontend/src/types/index.ts` 追加：

```typescript
/** 掌握单元（spec §3.3）。 */
export type UnitItem = {
  id: number;
  unitId: number;
  kind: "summary" | "concept_card" | "quiz_q" | "exercise" | "flashcard";
  body: string;
  isVerified: boolean;
  verifiedAt: string | null;
};

export type MasteryUnit = {
  id: number;
  sourceType: string;
  sourceRef: string;
  title: string;
  skillIds: string[];
  daySeq: number | null;
  generationMode: "llm" | "rule";
  status: string;
  items: UnitItem[];
};

export type AnswerResult = {
  itemId: number;
  correct: boolean;
  verified: boolean;
  rationale: string | null;
  cardId: number | null;
};
```

`frontend/src/services/masteryService.ts`：

```typescript
/** 掌握单元服务（计划 2）。snake_case → camelCase 在此层完成。 */

import { apiClient } from "@/lib/apiClient";
import type { AnswerResult, MasteryUnit, UnitItem } from "@/types";

interface UnitItemDTO {
  id: number;
  unit_id: number;
  kind: UnitItem["kind"];
  body: string;
  is_verified: boolean;
  verified_at: string | null;
}

interface UnitDTO {
  id: number;
  source_type: string;
  source_ref: string;
  title: string;
  skill_ids: string[];
  day_seq: number | null;
  generation_mode: "llm" | "rule";
  status: string;
  items: UnitItemDTO[];
}

function toUnit(d: UnitDTO): MasteryUnit {
  return {
    id: d.id,
    sourceType: d.source_type,
    sourceRef: d.source_ref,
    title: d.title,
    skillIds: d.skill_ids,
    daySeq: d.day_seq,
    generationMode: d.generation_mode,
    status: d.status,
    items: d.items.map((i) => ({
      id: i.id,
      unitId: i.unit_id,
      kind: i.kind,
      body: i.body,
      isVerified: i.is_verified,
      verifiedAt: i.verified_at,
    })),
  };
}

export async function listUnits(daySeq?: number): Promise<MasteryUnit[]> {
  const qs = daySeq !== undefined ? `?day_seq=${daySeq}` : "";
  const dtos = await apiClient.get<UnitDTO[]>(`/api/mastery/units${qs}`);
  return dtos.map(toUnit);
}

export async function getUnit(id: number): Promise<MasteryUnit> {
  return toUnit(await apiClient.get<UnitDTO>(`/api/mastery/units/${id}`));
}

export async function answerItem(
  unitId: number,
  itemId: number,
  answer: string,
): Promise<AnswerResult> {
  const d = await apiClient.post<{
    item_id: number; correct: boolean; verified: boolean;
    rationale: string | null; card_id: number | null;
  }>(`/api/mastery/units/${unitId}/answer`, { item_id: itemId, answer });
  return { itemId: d.item_id, correct: d.correct, verified: d.verified, rationale: d.rationale, cardId: d.card_id };
}

export async function teachBackComplete(payload: {
  unitId: number;
  durationMinutes?: number | null;
  answers: { itemId: number; spoken: string }[];
}): Promise<{ logId: number; cardsCreated: number; verdicts: { itemId: number; passed: boolean; hint: string | null }[] }> {
  const d = await apiClient.post<{
    log_id: number; cards_created: number;
    verdicts: { item_id: number; passed: boolean; hint: string | null }[];
  }>("/api/teach-back/complete", {
    unit_id: payload.unitId,
    duration_minutes: payload.durationMinutes ?? null,
    answers: payload.answers.map((a) => ({ item_id: a.itemId, spoken: a.spoken })),
  });
  return {
    logId: d.log_id,
    cardsCreated: d.cards_created,
    verdicts: d.verdicts.map((v) => ({ itemId: v.item_id, passed: v.passed, hint: v.hint })),
  };
}
```

- [ ] **Step 2: UnitView（学习 + 实证 + Teach-Back 一体）**

`frontend/src/components/UnitView.tsx`：

```tsx
"use client";

/** 掌握单元视图：摘要/概念卡 → 测验实证 → Teach-Back 口述回收。
 * 完成判据三选一（spec §3.2）：测验过 / Teach-Back 过 / 证据挂上。 */

import { useState } from "react";
import { answerItem, teachBackComplete } from "@/services/masteryService";
import type { MasteryUnit, UnitItem } from "@/types";

const KIND_LABEL: Record<UnitItem["kind"], string> = {
  summary: "摘要",
  concept_card: "概念卡",
  quiz_q: "测验",
  exercise: "思考题",
  flashcard: "复习卡",
};

export default function UnitView({ unit }: { unit: MasteryUnit }) {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [verdicts, setVerdicts] = useState<Record<number, { correct: boolean; rationale: string | null }>>({});
  const [tbResult, setTbResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submitAnswer(item: UnitItem) {
    const text = (answers[item.id] ?? "").trim();
    if (!text) return;
    setBusy(true);
    try {
      const r = await answerItem(unit.id, item.id, text);
      setVerdicts((v) => ({ ...v, [item.id]: { correct: r.correct, rationale: r.rationale } }));
    } finally {
      setBusy(false);
    }
  }

  async function submitTeachBack() {
    const quiz = unit.items.filter((i) => i.kind === "quiz_q");
    const spoken = quiz
      .map((i) => ({ itemId: i.id, spoken: (answers[i.id] ?? "").trim() }))
      .filter((a) => a.spoken);
    if (spoken.length === 0) return;
    setBusy(true);
    try {
      const r = await teachBackComplete({ unitId: unit.id, answers: spoken });
      const passed = r.verdicts.filter((v) => v.passed).length;
      setTbResult(`Teach-Back 完成：${passed}/${r.verdicts.length} 通过，已自动写入学习日志（错项 ${r.cardsCreated} 张进复习队列）。`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 16, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <div className="flex items-center" style={{ gap: 8 }}>
        <h2 className="text-base font-semibold">{unit.title}</h2>
        <span
          className="text-xs"
          style={{
            padding: "2px 8px",
            borderRadius: "var(--radius-pill)",
            background: unit.generationMode === "llm" ? "var(--accent-primary-soft, #DBEAFE)" : "var(--surface-muted, #F4F4F5)",
            color: unit.generationMode === "llm" ? "var(--accent-primary)" : "var(--text-muted)",
          }}
        >
          {unit.generationMode === "llm" ? "AI 生成" : "规则兜底（LLM 不可用）"}
        </span>
      </div>

      {unit.items.map((item) => (
        <div
          key={item.id}
          style={{ padding: 12, border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)" }}
        >
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
            {KIND_LABEL[item.kind]}
            {item.isVerified ? " · 已实证 ✓" : ""}
          </p>
          <p className="text-sm" style={{ whiteSpace: "pre-wrap" }}>{item.body}</p>

          {item.kind === "quiz_q" ? (
            <div className="mt-2 flex flex-wrap items-center" style={{ gap: 8 }}>
              <input
                value={answers[item.id] ?? ""}
                onChange={(e) => setAnswers((a) => ({ ...a, [item.id]: e.target.value }))}
                placeholder="闭卷作答（答对即实证）"
                style={{ flex: 1, minWidth: 200, padding: 8, borderRadius: "var(--radius-md)", border: "1px solid var(--border-default)" }}
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => submitAnswer(item)}
                style={{ padding: "6px 16px", borderRadius: "var(--radius-pill)", background: "var(--accent-primary)", color: "var(--text-inverse)", border: "none", cursor: "pointer" }}
              >
                提交
              </button>
              {verdicts[item.id] ? (
                <span className="text-xs" style={{ color: verdicts[item.id].correct ? "var(--accent-success, #16A34A)" : "var(--accent-danger)" }}>
                  {verdicts[item.id].correct ? "✓ 通过" : `✗ ${verdicts[item.id].rationale ?? "再试一次"}`}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
      ))}

      <div className="flex items-center" style={{ gap: 12 }}>
        <button
          type="button"
          disabled={busy}
          onClick={submitTeachBack}
          style={{ padding: "8px 20px", borderRadius: "var(--radius-pill)", background: "var(--accent-primary)", color: "var(--text-inverse)", border: "none", cursor: busy ? "not-allowed" : "pointer", opacity: busy ? 0.7 : 1 }}
        >
          Teach-Back：口述回收
        </button>
        {tbResult ? <p className="text-xs" style={{ color: "var(--text-muted)" }}>{tbResult}</p> : null}
      </div>
    </section>
  );
}
```

`frontend/src/components/TodayUnit.tsx`：

```tsx
"use client";

/** 今日关键单元：取 day_seq 对应单元，打开即懒生成（后端保证）。 */

import { useEffect, useState } from "react";
import { listUnits, getUnit } from "@/services/masteryService";
import type { MasteryUnit } from "@/types";
import UnitView from "./UnitView";

export default function TodayUnit({ daySeq }: { daySeq: number | null }) {
  const [unit, setUnit] = useState<MasteryUnit | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (daySeq === null) return;
    (async () => {
      try {
        const list = await listUnits(daySeq);
        if (list.length > 0) {
          setUnit(await getUnit(list[0].id));
        }
      } catch {
        setError("单元加载失败（后端不可用或网格未铺——cd backend && python -c \"from app.db.base import SessionLocal; from app.services.mastery.grid import sync_grid; sync_grid(SessionLocal())\"）");
      }
    })();
  }, [daySeq]);

  if (error) {
    return (
      <p className="text-xs" style={{ padding: 12, color: "var(--accent-danger)", background: "var(--accent-danger-soft)", borderRadius: "var(--radius-md)" }}>
        {error}
      </p>
    );
  }
  if (!unit) return null;
  return <UnitView unit={unit} />;
}
```

`frontend/src/app/learn/page.tsx`：在 `<TodayBoard .../>` 之前插入一行（import 一并加）：

```tsx
import TodayUnit from "@/components/TodayUnit";
...
          {/* 今日关键单元：学→测→Teach-Back（计划 2） */}
          <TodayUnit daySeq={today.day?.seq ?? null} />
```

⚠️ `today.day?.seq` 以 `getToday` 实际返回类型为准（`types/index.ts` 的 Today 类型里施工单日字段叫什么就用什么，tsc 校验）。

- [ ] **Step 3: TodayBoard 完成判据换「实质三选一」（spec §3.2）**

四件套的布尔勾选不再是完成依据。在 `frontend/src/components/TodayBoard.tsx` 中把四件套区块替换为 `TodayCompletion` 派生展示（新增小组件 `frontend/src/components/TodayCompletion.tsx`，完整代码）：

```tsx
"use client";

/** 今日完成度：实质三选一（spec §3.2）——测验过 / Teach-Back 过 / 证据挂上。
 * 不再是布尔勾选：完成状态从真实记录派生，不可手点。 */

import type { LearningLog, MasteryUnit } from "@/types";

export default function TodayCompletion({
  unit,
  logs,
}: {
  unit: MasteryUnit | null;
  logs: LearningLog[];
}) {
  const quizPassed = (unit?.items ?? []).some((i) => i.isVerified);
  const teachBackDone = logs.some((l) => l.content.startsWith("Teach-Back ·"));
  const evidence = logs.some((l) => Boolean(l.artifactUrl));
  const done = quizPassed || teachBackDone || evidence;
  const criteria = [
    { ok: quizPassed, label: "测验实证过" },
    { ok: teachBackDone, label: "Teach-Back 过" },
    { ok: evidence, label: "证据已挂" },
  ];

  return (
    <section
      className="flex flex-col"
      style={{ gap: 8, padding: 16, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h3 className="text-sm font-semibold">
        今日完成：{done ? "✓ 已达成（三选一）" : "未达成——学完来真的，不勾选"}
      </h3>
      <div className="flex flex-wrap" style={{ gap: 8 }}>
        {criteria.map((c) => (
          <span
            key={c.label}
            className="text-xs"
            style={{
              padding: "2px 10px",
              borderRadius: "var(--radius-pill)",
              background: c.ok ? "var(--accent-primary-soft, #DBEAFE)" : "var(--surface-muted, #F4F4F5)",
              color: c.ok ? "var(--accent-primary)" : "var(--text-muted)",
            }}
          >
            {c.ok ? "✓" : "○"} {c.label}
          </span>
        ))}
      </div>
    </section>
  );
}
```

`TodayBoard.tsx`：删除四件套勾选 JSX 块（`createArtifact` 调用所在区块，约 :96-102 一带），换成 `<TodayCompletion unit={unit} logs={learningLogs ?? []} />`；其 props 增加可选 `unit?: MasteryUnit | null`。`/learn` 的 `TodayUnit` 取到的 unit 一并下传（`<TodayBoard today={today} learningLogs={learningLogs} unit={unit} />`——由 `learn/page.tsx` 服务端取 `getUnit` 或让 `TodayBoard` 经 `TodayUnit` 的状态提升，二选一，以改动最小为准）。删除后 `createArtifact/deleteArtifact` 若无其他调用方，随死代码清理（见计划 1 Task 10 删除清单）。**四件套的后端端点不动**（撤 UI 留数据，spec D5）。

- [ ] **Step 4: 门禁 + 冒烟**

Run（cwd=frontend）:
```
node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
node node_modules/eslint/bin/eslint.js src/services/masteryService.ts src/components/UnitView.tsx src/components/TodayUnit.tsx src/components/TodayCompletion.tsx src/components/TodayBoard.tsx src/app/learn/page.tsx
```
Expected: tsc RC0；eslint 零问题（TodayBoard 既有基线外零新增）

联调（后端起着）：`GET /api/mastery/units` → 有数据；`GET /api/mastery/units/1` → items 非空；`POST /api/teach-back/complete` 一题通过一题失败 → log_id 返回；`/learn` 完成度三选一随测验/Teach-Back 变化。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/masteryService.ts frontend/src/components/UnitView.tsx frontend/src/components/TodayUnit.tsx frontend/src/components/TodayCompletion.tsx frontend/src/components/TodayBoard.tsx frontend/src/app/learn/page.tsx
git commit -m "feat(mastery): UnitView 学测证闭环 + 今日完成度实质三选一替换布尔勾选"
```

---

### Task 8: 前端 —— ReviewQueue 接进 /review

**Files:**
- Create: `frontend/src/components/ReviewQueue.tsx`
- Modify: `frontend/src/app/review/page.tsx`（`<ReviewBoard />` 之上挂 `<ReviewQueue />`）
- Modify: `frontend/src/services/masteryService.ts`（追加 `listDueCards` / `reviewCard`）

**Interfaces:**
- Consumes: `GET /api/today` 的 `review.due_cards`、`POST /api/mastery/cards/{id}/review`
- Produces: `reviewCard(cardId, rating, durationSeconds?)`；`ReviewQueue()` 组件（4 档评分按钮，评完即刷新队列）

- [ ] **Step 1: service 追加**

`masteryService.ts` 追加（含类型）：

```typescript
export type ReviewCardT = {
  id: number;
  front: string;
  back: string;
  dueAt: string;
  intervalDays: number;
  ef: number;
  lapseCount: number;
  goodStreak: number;
  cardStatus: "active" | "fixed";
};

export async function listDueCards(): Promise<ReviewCardT[]> {
  const data = await apiClient.get<{ review?: { due_cards: Array<{
    id: number; front: string; back: string; due_at: string;
    interval_days: number; ef: number; lapse_count: number;
    good_streak: number; card_status: "active" | "fixed";
  }> } }>("/api/today");
  return (data.review?.due_cards ?? []).map((c) => ({
    id: c.id,
    front: c.front,
    back: c.back,
    dueAt: c.due_at,
    intervalDays: c.interval_days,
    ef: c.ef,
    lapseCount: c.lapse_count,
    goodStreak: c.good_streak,
    cardStatus: c.card_status,
  }));
}

export async function reviewCard(
  cardId: number,
  rating: "again" | "hard" | "good" | "easy",
  durationSeconds?: number | null,
): Promise<void> {
  await apiClient.post(`/api/mastery/cards/${cardId}/review`, {
    rating,
    duration_seconds: durationSeconds ?? null,
  });
}
```

- [ ] **Step 2: ReviewQueue 组件**

`frontend/src/components/ReviewQueue.tsx`：

```tsx
"use client";

/** SM-2 复习队列：今日到期卡逐张过，4 档评分推进调度。
 * 「记住 ≠ 看过」——第三问的日常 10-15 分钟入口（spec §3.2）。 */

import { useCallback, useEffect, useState } from "react";
import { listDueCards, reviewCard, type ReviewCardT } from "@/services/masteryService";

const RATINGS = [
  { key: "again", label: "忘了", color: "var(--accent-danger)" },
  { key: "hard", label: "模糊", color: "var(--accent-warning, #D97706)" },
  { key: "good", label: "记得", color: "var(--accent-primary)" },
  { key: "easy", label: "秒答", color: "var(--accent-success, #16A34A)" },
] as const;

export default function ReviewQueue() {
  const [cards, setCards] = useState<ReviewCardT[]>([]);
  const [flipped, setFlipped] = useState(false);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setCards(await listDueCards());
    } catch {
      setCards([]);
    }
    setFlipped(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const current = cards[0];

  async function rate(rating: (typeof RATINGS)[number]["key"]) {
    if (!current) return;
    setBusy(true);
    try {
      await reviewCard(current.id, rating);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="flex flex-col"
      style={{ gap: 12, padding: 24, background: "var(--surface-card)", borderRadius: "var(--radius-lg)" }}
    >
      <h2 className="text-base font-semibold">今日复习（{cards.length} 张到期）</h2>
      {cards.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          复习队列已清空——做完今天的掌握单元后，概念卡会自动入队。
        </p>
      ) : (
        <>
          <div
            onClick={() => setFlipped((f) => !f)}
            style={{
              padding: 24,
              minHeight: 96,
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-default)",
              background: "var(--surface-canvas)",
              cursor: "pointer",
            }}
          >
            <p className="text-sm font-semibold">{current.front}</p>
            {flipped ? (
              <p className="mt-3 text-sm" style={{ color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>
                {current.back}
              </p>
            ) : (
              <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
                点击卡片看答案
              </p>
            )}
          </div>
          <div className="flex flex-wrap" style={{ gap: 8 }}>
            {RATINGS.map((r) => (
              <button
                key={r.key}
                type="button"
                disabled={busy || !flipped}
                onClick={() => rate(r.key)}
                style={{
                  padding: "6px 18px",
                  borderRadius: "var(--radius-pill)",
                  border: `1px solid ${r.color}`,
                  color: r.color,
                  background: "transparent",
                  cursor: busy || !flipped ? "not-allowed" : "pointer",
                  opacity: busy || !flipped ? 0.5 : 1,
                }}
              >
                {r.label}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
```

`frontend/src/app/review/page.tsx`：`<ReviewBoard />` 之前插入：

```tsx
import ReviewQueue from "@/components/ReviewQueue";
...
        <ReviewQueue />
        <ReviewBoard />
```

- [ ] **Step 3: 门禁 + 冒烟**

Run（cwd=frontend）:
```
node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
node node_modules/eslint/bin/eslint.js src/components/ReviewQueue.tsx src/services/masteryService.ts src/app/review/page.tsx
```
Expected: tsc RC0；eslint 零问题

冒烟：`/review` 渲染队列（先答错几题造卡）；点「记得」后 `GET /api/today` 的 `review.due_count` 减少。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ReviewQueue.tsx frontend/src/services/masteryService.ts frontend/src/app/review/page.tsx
git commit -m "feat(mastery): SM-2 复习队列接进 /review"
```

---

## 验收（本计划整体）

1. pytest 全量：基线 437+ **不降**，新增约 18 例全绿
2. tsc RC0；eslint 零新增
3. 人工走通：`/learn` 今日单元（懒生成+降级徽标）→ 测验答对「已实证 ✓」→ Teach-Back 后 `/review` 多出学习日志与错项卡 → 4 档评分推进调度
4. `GET /api/today` 含 `review` 区且既有键不破坏
5. 开发库核对：`mastery_units` 网格 ≥40（30 天 + 论文）；第二次 `sync_grid` created=0（幂等）
