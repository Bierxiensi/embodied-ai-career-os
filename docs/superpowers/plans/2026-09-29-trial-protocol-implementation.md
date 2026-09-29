# 试用期协议 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地试用期协议的两个交付物——错题集文件（双表 + 条目格式）与 `trial_status.py` 只读仪表（一条命令读五项信号）。

**Architecture:** `docs/试用错题集.md` 是唯一问题捕获入口（每日体感表 + 每周五自查表 + 条目区，示例置于代码围栏内避免被解析）。`backend/scripts/trial_status.py` 为只读仪表：纯函数（日期折算/连续天数/Markdown 表解析）+ `main()` 查库打印五项，查询模式镜像 `backend/app/api/today.py` 的 review 区。

**Tech Stack:** Python 3.13（backend/.venv）、SQLAlchemy ORM、pytest；无新增依赖。

**Spec:** `docs/superpowers/specs/2026-09-29-trial-protocol-design.md`（§2 出口条件 / §3 仪表规格 / §4 错题集规格 / §7 交付验收）

## Global Constraints

- **M2 覆盖率口径（spec §2 钉死）**：分子 = `unit_items` 中 `kind='quiz_q' AND is_verified=true` 条数；分母 = `kind='quiz_q'` 总条数；分母为 0 时输出「暂无题目」不许除零。
- **活跃天数判定（spec §3）**：当天存在以下任一即算活跃——新增 `learning_log` / 新增 `review_log` / `unit_items.verified_at` 当日置位；**naive UTC 按项目 normalizeUtc 口径折算本地日**（naive 视为 UTC，转本地日期）；从**今天**往回数，今天无活动则连续天数为 0。
- **仪表只读**：仅 SELECT，零写入 dev 库 `backend/data/app.db`；运行前后文件指纹必须一致。
- **错题条目格式（spec §4）**：`- [YYYY-MM-DD] 现象 | 卡点 | 猜测(?可空) | 严重度(高/中/低)`；示例只能放在 ``` 围栏内，解析器跳过围栏。
- **两表分工**：每日体感表（日期|体感分钟，每天一行）；每周五自查表（周五日期|覆盖率读数|新问题数|本周最卡，每周一行）。
- pytest 基线 **523 passed / 2 skipped** 不得下降；跑法 `cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --basetemp=../.workbuddy/tmp/pytest-base`。
- 不得修改 `backend/tests/conftest.py`；提交只 `git add <显式路径>`，禁止 `git add -A`；提交消息带 trailer `Co-Authored-By: Claude Code <noreply@anthropic.com>`。
- 当前分支 `feature/mastery-plan1`；Windows 控制台 GBK 问题一律 `PYTHONIOENCODING=utf-8`。

## File Structure

| 文件 | 职责 |
|------|------|
| Create: `docs/试用错题集.md` | 问题捕获唯一入口：双表头（空表）+ 条目格式示例（围栏内） |
| Create: `backend/scripts/trial_status.py` | 只读仪表：纯函数 + `main()` 打印五项 |
| Create: `backend/tests/test_trial_status.py` | 纯函数 TDD + main 输出冒烟 |

---

### Task 1: 错题集脚手架

**Files:**
- Create: `docs/试用错题集.md`

**Interfaces:**
- Produces: `docs/试用错题集.md` 的结构契约（Task 2 的解析器依赖）：两张表各自的标题行（`## 每日体感`、`## 每周五自查`）+ Markdown 表头/分隔行；问题条目为行首 `- [YYYY-MM-DD] ` 的列表项，**示例必须在 ``` 围栏内**。

- [ ] **Step 1: 创建文件（完整内容）**

```markdown
# 试用错题集

> 试用期协议（`docs/superpowers/specs/2026-09-29-trial-protocol-design.md`）的问题捕获入口。
> 一行一条、现象先行；同一根因的重复现象合并（在原条目后补 `[+日期 附注]`）。
> 复盘时逐条关闭：`→ 转票据 <名> / 不修（原因）/ 已修 <commit>`。

## 每日体感

<!-- 每天一行：OS 操作耗时（从打开到收工，不含纯学习时间）。M1 计数口径 = 本表有分钟数的行数。 -->

| 日期 | 体感分钟 |
|------|---------|

## 每周五自查

<!-- 每周五跑完 trial_status.py 后填一行；覆盖率读数直接抄脚本输出。 -->

| 周五日期 | 覆盖率读数 | 新问题数(本周) | 本周最卡的一件事 |
|----------|-----------|--------------|----------------|

## 问题条目

<!-- 格式见下方代码块示例；复制示例行改写后写在本节（围栏外）才算有效条目。 -->

```text
- [2026-10-01] 现象描述 | 卡在哪 | 猜测（? 可空） | 严重度(高/中/低)
```
```

- [ ] **Step 2: 结构核验**（cwd=仓库根）

Run:
```
python -c "
import io
t = io.open(r'docs/试用错题集.md', encoding='utf-8').read()
assert '## 每日体感' in t and '## 每周五自查' in t and '## 问题条目' in t
assert t.count('|------|') >= 2          # 两张表的分隔行
assert '- [2026-10-01]' in t             # 格式示例在
assert t.count('```') >= 2               # 示例在围栏内（成对围栏）
print('scaffold OK')
"
```
Expected: `scaffold OK`

- [ ] **Step 3: Commit**

```bash
git add docs/试用错题集.md
git commit -m "docs(trial): 试用错题集脚手架（双表+条目格式示例）"
```

---

### Task 2: trial_status.py 只读仪表

**Files:**
- Create: `backend/scripts/trial_status.py`
- Test: `backend/tests/test_trial_status.py`

**Interfaces:**
- Consumes: Task 1 的 `docs/试用错题集.md` 结构契约；`app.models.learning_log.LearningLog`、`app.models.mastery.ReviewLog/UnitItem`、`app.models.mastery.ReviewCard`；查询模式镜像 `backend/app/api/today.py` 的 review 区（`card_status=="active"` + `due_at <= now`）。
- Produces:
  - `to_local_date(dt: datetime) -> date`（naive 视为 UTC，转本地日）
  - `active_streak(dates: set[date], today: date) -> int`（从 today 严格往回数）
  - `parse_friday_readings(md_text: str) -> list[tuple[date, float]]`（跳过围栏；覆盖率列 `12.5%` → 12.5）
  - `count_entries(md_text: str) -> int`（跳过围栏；行首 `- [YYYY-MM-DD]`）
  - `main() -> int`（打印五项，恒返 0；仅 SELECT）

- [ ] **Step 1: 写失败测试（完整文件）**

```python
# backend/tests/test_trial_status.py
"""trial_status 纯函数 + main 输出冒烟（试用期协议 spec §3/§7）。"""

from datetime import date, datetime, timedelta, timezone

from scripts.trial_status import (
    active_streak,
    count_entries,
    local_coverage,
    parse_friday_readings,
    to_local_date,
)

# ---- to_local_date：naive 视为 UTC（normalizeUtc 口径），aware 先转 UTC 再本地 ----


def test_to_local_date_naive_treated_as_utc():
    # 契约：naive == 按 UTC 解释（与系统时区无关的等价断言）
    naive = datetime(2026, 10, 1, 16, 0, 0)
    aware = naive.replace(tzinfo=timezone.utc)
    assert to_local_date(naive) == to_local_date(aware)


def test_to_local_date_aware_is_system_local_day():
    # 契约：aware 先归一 UTC 再转系统本地日（等价于自带 astimezone 行为）
    aware = datetime(2026, 10, 1, 16, 0, 0, tzinfo=timezone.utc)
    assert to_local_date(aware) == aware.astimezone().date()


# ---- active_streak：从 today 严格往回数 ----


def test_streak_counts_consecutive_from_today():
    today = date(2026, 10, 9)
    dates = {date(2026, 10, 9), date(2026, 10, 8), date(2026, 10, 7), date(2026, 10, 5)}
    assert active_streak(dates, today) == 3  # 10-6 断档


def test_streak_zero_when_today_inactive():
    today = date(2026, 10, 9)
    dates = {date(2026, 10, 8), date(2026, 10, 7)}
    assert active_streak(dates, today) == 0  # spec：从今天往回，今天没有即 0


def test_streak_empty():
    assert active_streak(set(), date(2026, 10, 9)) == 0


# ---- local_coverage：M2 口径，分母 0 不除零 ----


def test_coverage_normal():
    assert local_coverage(3, 10) == "3/10 (30.0%)"


def test_coverage_zero_denominator():
    assert local_coverage(0, 0) == "暂无题目"


# ---- parse_friday_readings：围栏跳过 + % 解析 ----


def test_parse_readings_from_table():
    md = (
        "## 每周五自查\n\n"
        "| 周五日期 | 覆盖率读数 | 新问题数(本周) | 本周最卡的一件事 |\n"
        "|----------|-----------|--------------|----------------|\n"
        "| 2026-10-03 | 12.5% | 2 | 知识库卡 |\n"
        "| 2026-10-10 | 18.0% | 1 | 复习队列空 |\n"
    )
    rows = parse_friday_readings(md)
    assert rows == [(date(2026, 10, 3), 12.5), (date(2026, 10, 10), 18.0)]


def test_parse_readings_skips_fenced_example():
    md = "```\n| 2026-10-03 | 99.9% | x | x |\n```\n| 2026-10-10 | 1.0% | x | x |\n"
    assert parse_friday_readings(md) == [(date(2026, 10, 10), 1.0)]


def test_parse_readings_empty_table():
    assert parse_friday_readings("## 每周五自查\n\n| 周五日期 | 覆盖率读数 |\n|---|---|\n") == []


# ---- count_entries：围栏跳过 ----


def test_count_entries_counts_live_only():
    md = (
        "- [2026-10-01] 症状A | 卡点 | ? | 高\n"
        "```text\n- [2026-10-01] 现象描述 | 卡在哪 | ? | 中\n```\n"
        "- [2026-10-02] 症状B | 卡点2 | 猜测 | 低\n"
    )
    assert count_entries(md) == 2


def test_count_entries_zero():
    assert count_entries("暂无") == 0


# ---- main 冒烟（conftest 隔离库；五项标签齐 + 不写库）


def test_main_prints_five_sections(capsys):
    from scripts.trial_status import main

    assert main() == 0
    out = capsys.readouterr().out
    for label in ("连续活跃天数", "quiz 覆盖率", "覆盖率历史读数", "错题条数", "到期卡数"):
        assert label in out, label
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_trial_status.py -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'scripts.trial_status'`）

- [ ] **Step 3: 实现 `backend/scripts/trial_status.py`（完整文件）**

```python
"""试用期信号仪表（spec 2026-09-29-trial-protocol-design §3）。

只读：仅 SELECT，零写入 dev 库。五项输出：
  连续活跃天数 / quiz 覆盖率(M2 口径) / 覆盖率历史读数(读错题集每周五自查表) /
  错题条数 / 到期卡数+最近自查日期

用法：cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/trial_status.py
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

# backend/scripts/ → parents[1]=backend, parents[2]=仓库根
_TRIAL_MD = Path(__file__).resolve().parents[2] / "docs" / "试用错题集.md"

_DATE_RE = re.compile(r"^\[?(\d{4}-\d{2}-\d{2})\]?$")
_ENTRY_RE = re.compile(r"^- \[\d{4}-\d{2}-\d{2}\]")
_FENCE_RE = re.compile(r"^```")


def to_local_date(dt: datetime) -> date:
    """naive 视为 UTC（normalizeUtc 口径），转本地日；aware 先归一到 UTC 再转本地。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().date()


def active_streak(dates: set[date], today: date) -> int:
    """从 today 严格往回数连续天数；today 不在集合中即 0（spec §3 字面口径）。"""
    n = 0
    cur = today
    while cur in dates:
        n += 1
        cur = cur.fromordinal(cur.toordinal() - 1)
    return n


def local_coverage(numerator: int, denominator: int) -> str:
    """M2 口径展示；分母 0 输出「暂无题目」不许除零。"""
    if denominator <= 0:
        return "暂无题目"
    return f"{numerator}/{denominator} ({numerator / denominator * 100:.1f}%)"


def _lines_outside_fences(text: str):
    """跳过 ``` 围栏内所有行（示例不参与解析）。"""
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line


def parse_friday_readings(md_text: str) -> list[tuple[date, float]]:
    """解析每周五自查表的覆盖率列；表为空/无 % 列返回 []。"""
    rows: list[tuple[date, float]] = []
    for line in _lines_outside_fences(md_text):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        m = _DATE_RE.match(cells[0])
        pct = re.fullmatch(r"(\d+(?:\.\d+)?)%", cells[1])
        if m and pct:
            rows.append((date.fromisoformat(m.group(1)), float(pct.group(1))))
    return rows


def count_entries(md_text: str) -> int:
    """有效问题条目数：围栏外、行首 `- [YYYY-MM-DD] `。"""
    return sum(1 for line in _lines_outside_fences(md_text) if _ENTRY_RE.match(line))


def _read_trial_md() -> str:
    """读错题集；文件不存在返回空串（输出侧按空处理，不抛）。"""
    try:
        return _TRIAL_MD.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _streak_dates(db) -> set[date]:
    """三源活跃日（本地日）：learning_log / review_log / verified_at。"""
    from app.models.learning_log import LearningLog
    from app.models.mastery import ReviewLog, UnitItem

    dates: set[date] = set()
    for (ts,) in db.query(LearningLog.created_at).all():
        if ts is not None:
            dates.add(to_local_date(ts))
    for (ts,) in db.query(ReviewLog.reviewed_at).all():
        if ts is not None:
            dates.add(to_local_date(ts))
    for (ts,) in db.query(UnitItem.verified_at).all():
        if ts is not None:
            dates.add(to_local_date(ts))
    return dates


def main() -> int:
    from app.db.base import SessionLocal
    from app.models.mastery import ReviewCard, UnitItem

    db = SessionLocal()
    try:
        # 1) 连续活跃天数
        streak = active_streak(_streak_dates(db), date.today())

        # 2) quiz 覆盖率（M2 口径）
        denom = db.query(UnitItem).filter(UnitItem.kind == "quiz_q").count()
        num = (
            db.query(UnitItem)
            .filter(UnitItem.kind == "quiz_q", UnitItem.is_verified.is_(True))
            .count()
        )

        # 3/4/5 覆盖率历史 + 错题条数 + 最近自查（错题集）
        md = _read_trial_md()
        readings = parse_friday_readings(md)
        entries = count_entries(md)

        # 历史读数展示
        if readings:
            pcts = [f"{d.isoformat()}={p}%" for d, p in readings]
            delta = (
                f"（最近差值 {readings[-1][1] - readings[-2][1]:+.1f}）"
                if len(readings) >= 2
                else "（仅 1 次读数）"
            )
            hist = " ".join(pcts) + " " + delta
        else:
            hist = "暂无历史读数"

        # 5) 到期卡数（镜像 today.py review 区查询）
        now = datetime.now(timezone.utc)
        due = (
            db.query(ReviewCard)
            .filter(ReviewCard.card_status == "active", ReviewCard.due_at <= now)
            .count()
        )
        last_check = readings[-1][0].isoformat() if readings else "无"

        print("===== trial_status =====")
        print(f"连续活跃天数: {streak}")
        print(f"quiz 覆盖率: {local_coverage(num, denom)}")
        print(f"覆盖率历史读数: {hist}")
        print(f"错题条数: {entries}")
        print(f"到期卡数: {due} · 最近自查: {last_check}")
        print("========================")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
```

⚠️ 标签口径：print 用 `错题条数`（与 Step 1 测试的 `"错题条数"` 标签一致）——五项输出的标签以测试为准，实现不得改词。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/test_trial_status.py -q`
Expected: PASS（13 个用例）

- [ ] **Step 5: 全量回归**

Run: `cd backend && .venv/Scripts/python.exe -m pytest tests/ -q --basetemp=../.workbuddy/tmp/pytest-base`
Expected: **523 + 13 = 536 passed / 2 skipped / 0 failed**

- [ ] **Step 6: CLI 实跑 + 只读指纹核验**

Run:
```
cd backend
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -c "import hashlib, pathlib, subprocess, sys; p=pathlib.Path('data/app.db'); b=hashlib.sha256(p.read_bytes()).hexdigest(); subprocess.run([sys.executable, 'scripts/trial_status.py'], check=True, env={'PYTHONIOENCODING': 'utf-8'}); a=hashlib.sha256(p.read_bytes()).hexdigest(); print('fingerprint', 'SAME' if a==b else 'CHANGED'); sys.exit(0 if a==b else 1)"
```
Expected: 五项输出齐（连续活跃天数 / quiz 覆盖率 / 覆盖率历史读数=暂无历史读数 / 错题条数=0 / 到期卡数）且末行 `fingerprint SAME`

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/trial_status.py backend/tests/test_trial_status.py
git commit -m "feat(trial): trial_status 只读仪表（五项信号一条命令）"
```

---

## 验收（本计划整体，对应 spec §7）

1. `docs/试用错题集.md`：双表头空表 + 围栏内格式示例（Task 1 Step 2 核验）
2. `scripts/trial_status.py`：五项输出正确、CLI 实跑指纹 SAME（Task 2 Step 6）
3. pytest 全量 **536 passed / 2 skipped / 0 failed**（基线 523+13 不降）
4. spec 口径（M2 分子分母、活跃天数、两表分工）在代码注释与测试中均有钉子
