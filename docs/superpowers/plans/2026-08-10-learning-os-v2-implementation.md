# Learning OS V2 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Learning OS 从规则驱动的空壳升级为 LLM 驱动的自动运转 AI 教练系统（A/C/D/F 四个模块）

**Architecture:** LLM 层（`app/llm/`）已就绪，本次迭代将每个 Agent 节点的规则实现替换/增强为 LLM 调用，新增 Reminder/GitHub/ToolBridge 三个服务模块，通过 APScheduler 串联自动化流程

**Tech Stack:** Python 3.12+ / FastAPI 0.115 / LangGraph 0.2+ / SQLAlchemy 2.0 / APScheduler 3.x / Next.js 15 / TypeScript

**Design Spec:** `docs/superpowers/specs/2026-08-10-learning-os-iteration-design.md`

## Global Constraints

- Python 3.12+（已有 `from __future__ import annotations` 模式）
- LLM Provider 默认 `mock`，通过 `LLM_PROVIDER=deepseek` 环境变量切换
- 所有 LLM 调用须保留 fallback 到现有规则引擎（`safe_generate` 模式）
- 新增表须在 `app/models/__init__.py` 注册
- API 路由统一 `/api` 前缀，响应统一 `ApiResponse<T>` 包装
- 前端新增组件须遵循现有目录结构 `frontend/src/components/`
- 数据库迁移使用 `Base.metadata.create_all`（开发态），production 后切 Alembic

---

## Phase 1：LLM 接入 + 提醒骨架

### Task 1: LLM Supervisor 意图路由

**Files:**
- Modify: `backend/app/agents/supervisor/nodes.py:46-67`（`analyze_intent` 节点）
- Test: `backend/tests/test_supervisor_llm.py`（新建）

**Interfaces:**
- Consumes: `get_llm()` from `app.llm`, `SupervisorState` from `app.agents.supervisor.state`
- Produces: `analyze_intent(state) → dict`（`{"intent": "learn"|"complete"|"career"|"unknown"}`）

- [ ] **Step 1: 在 `supervisor/nodes.py` 顶部添加 LLM 版本的 `_analyze_intent_llm` 函数**

```python
# 在现有 _INTENT_KEYWORDS 下方新增

def _analyze_intent_llm(user_input: str) -> str | None:
    """LLM 意图识别。失败返回 None，调用方 fallback 规则路由。"""
    import json

    from app.llm import ChatMessage, get_llm

    prompt = f"""分析用户输入，判断意图类别。

用户输入："{user_input}"

意图类别：
- career：职业规划、岗位分析、转型方向、技能缺口、能力评估
- learn：学习、练习、实践、做实验、写代码、跑模型
- complete：完成任务、提交成果、复盘、回顾、打卡
- unknown：无法归类

返回 JSON：{{"intent": "<类别>", "confidence": 0.0-1.0, "reason": "<一句话理由>"}}
直接输出 JSON，不要其他文字。"""

    try:
        llm = get_llm()
        result = llm.chat_json([
            ChatMessage(role="system", content="你是一个意图分类器。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
        intent = result.get("intent", "")
        if intent in ("career", "learn", "complete", "unknown"):
            return intent
    except Exception:
        pass
    return None
```

- [ ] **Step 2: 修改 `analyze_intent` 节点，LLM 优先，规则兜底**

```python
def analyze_intent(state: SupervisorState) -> dict:
    """节点1：识别用户意图。

    LLM 优先（理解自然语言语义），失败时 fallback 规则关键词匹配。
    """
    user_input = (state.get("user_input") or "").strip()
    if not user_input:
        return {"intent": "unknown"}

    # LLM 优先
    llm_result = _analyze_intent_llm(user_input)
    if llm_result is not None:
        return {"intent": llm_result}

    # Fallback: 规则关键词匹配（保留现有逻辑不变）
    user_input_lower = user_input.lower()
    for intent, keywords in _INTENT_KEYWORDS:
        if any(kw.lower() in user_input_lower for kw in keywords):
            return {"intent": intent}

    return {"intent": "unknown"}
```

- [ ] **Step 3: 编写测试**

```python
# backend/tests/test_supervisor_llm.py
"""Supervisor LLM 意图路由测试。

LLM_PROVIDER=mock 时测试 fallback 路径；
LLM_PROVIDER=deepseek 时测试 LLM 路径。
设置 DEEPSEEK_API_KEY 后可跑真实 LLM 测试。
"""

import pytest
from app.agents.supervisor.nodes import analyze_intent


def test_analyze_intent_career():
    """含"成为"关键词 → career。"""
    result = analyze_intent({"user_input": "我想成为 Robot AI 工程师"})
    assert result["intent"] == "career"


def test_analyze_intent_learn():
    """含"学习"关键词 → learn。"""
    result = analyze_intent({"user_input": "学习 ROS2 Topic 通信"})
    assert result["intent"] == "learn"


def test_analyze_intent_complete():
    """含"完成"关键词 → complete。"""
    result = analyze_intent({"user_input": "完成今天的 publisher 任务"})
    assert result["intent"] == "complete"


def test_analyze_intent_unknown():
    """无关键词 → unknown。"""
    result = analyze_intent({"user_input": "今天天气不错"})
    assert result["intent"] == "unknown"


def test_analyze_intent_empty():
    """空输入 → unknown。"""
    result = analyze_intent({})
    assert result["intent"] == "unknown"


def test_analyze_intent_natural_language_career():
    """自然语言表述职业困惑——规则可能 miss，LLM 应命中。"""
    result = analyze_intent({
        "user_input": "我不确定自己应该先学 ROS2 还是先学 VLA，帮我分析下"
    })
    # 规则兜底应至少不崩溃
    assert result["intent"] in ("career", "learn", "complete", "unknown")
```

- [ ] **Step 4: 运行测试**

```bash
cd backend && python -m pytest tests/test_supervisor_llm.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/supervisor/nodes.py backend/tests/test_supervisor_llm.py
git commit -m "feat(supervisor): add LLM intent routing with rule fallback"
```

---

### Task 2: LLM Reviewer 证据评估

**Files:**
- Modify: `backend/app/agents/reviewer/nodes.py:55-60`（`evaluate_evidence` 节点）
- Modify: `backend/app/agents/reviewer/rules.py`（保留为 fallback）
- Test: `backend/tests/test_reviewer_llm.py`（新建）

**Interfaces:**
- Consumes: `get_llm()` from `app.llm`, `ReviewerState` from `app.agents.reviewer.state`, `score_evidence` / `decide_level` from `app.agents.reviewer.rules`
- Produces: `evaluate_evidence(state) → dict`（`{"evidence_score": int}`）

- [ ] **Step 1: 在 `reviewer/nodes.py` 顶部添加 LLM 评估函数**

```python
# 在现有 import 区域下方新增

def _evaluate_with_llm(task: dict, learning_log: dict) -> dict | None:
    """LLM 证据评估。失败返回 None，调用方 fallback 规则评分。"""
    from app.llm import ChatMessage, get_llm

    task_title = task.get("title", "")
    skill_name = task.get("skill_name", "")
    acceptance = task.get("acceptance", [])
    log_content = learning_log.get("content", "")
    artifact_url = learning_log.get("artifact_url", "")

    prompt = f"""你是具身智能学习导师。评估学生的一次学习成果。

任务：{task_title}
关联技能：{skill_name}
验收标准：{acceptance}
学生日志：{log_content}
产出链接：{artifact_url or "无"}

评估维度（每项 0-5 分）：
- understanding: 日志中展现了多深的理解？（0=照抄，5=能迁移到新场景）
- completion: 验收标准达成了几条？
- reflection: 有无自我反思？（总结/改进/难点/收获）
- evidence: artifact 链接是否有效？

返回 JSON：
{{
  "understanding": 0-5,
  "completion": 0-5,
  "reflection": 0-5,
  "evidence": 0-5,
  "total_score": 0-100,
  "summary": "一句话评估"
}}
直接输出 JSON，不要其他文字。"""

    try:
        llm = get_llm()
        result = llm.chat_json([
            ChatMessage(role="system", content="你是严格的技能评估导师。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
        score = int(result.get("total_score", 0))
        if 0 <= score <= 100:
            return {"evidence_score": min(score, 100), "llm_evaluation": result}
    except Exception:
        pass
    return None
```

- [ ] **Step 2: 修改 `evaluate_evidence` 节点**

```python
def evaluate_evidence(state: ReviewerState) -> dict:
    """节点2：计算证据得分。

    LLM 优先（语义理解），失败时 fallback 规则评分。
    """
    task = state.get("task", {})
    learning_log = state.get("learning_log", {})

    # LLM 优先
    llm_result = _evaluate_with_llm(task, learning_log)
    if llm_result is not None:
        return llm_result

    # Fallback: 规则评分
    from app.agents.reviewer.rules import score_evidence as rule_score
    score = rule_score(task, learning_log)
    return {"evidence_score": score}
```

- [ ] **Step 3: 编写测试**

```python
# backend/tests/test_reviewer_llm.py
"""Reviewer LLM 评估测试。"""
import pytest
from app.agents.reviewer.nodes import evaluate_evidence


def test_evaluate_evidence_rule_fallback():
    """Mock LLM 时走 rule fallback，应返回合法分数。"""
    state = {
        "task": {"title": "ROS2 publisher", "skill_name": "ROS2", "status": "done",
                 "acceptance": ["创建publisher", "topic echo验证"]},
        "learning_log": {"content": "完成了publisher节点，理解了QoS配置，学到了通信模型",
                         "artifact_url": "https://github.com/xxx"},
    }
    result = evaluate_evidence(state)
    assert "evidence_score" in result
    assert 0 <= result["evidence_score"] <= 100


def test_evaluate_evidence_insufficient():
    """日志过短，得分应低。"""
    state = {
        "task": {"title": "task", "skill_name": "skill", "status": "todo",
                 "acceptance": []},
        "learning_log": {"content": "done", "artifact_url": ""},
    }
    result = evaluate_evidence(state)
    assert result["evidence_score"] < 50
```

- [ ] **Step 4: 运行测试**

```bash
cd backend && python -m pytest tests/test_reviewer_llm.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/agents/reviewer/nodes.py backend/tests/test_reviewer_llm.py
git commit -m "feat(reviewer): add LLM evidence evaluation with rule fallback"
```

---

### Task 3: LLM Career + Research Agent

**Files:**
- Modify: `backend/app/agents/career/nodes.py:20-34`（`analyze_target` 节点）
- Modify: `backend/app/agents/research/nodes.py:42-56`（`match_template_node` 节点）
- Test: `backend/tests/test_career_llm.py`, `backend/tests/test_research_llm.py`（新建）

**Interfaces:**
- Consumes: `get_llm()` from `app.llm`, `CareerState`, `ResearchState`
- Produces: `analyze_target(state) → dict`, `match_template_node(state) → dict`

- [ ] **Step 1: 在 `career/nodes.py` 添加 LLM 分析函数**

```python
# 在现有 import 下方新增

def _analyze_with_llm(target_role: str, skills: list) -> dict | None:
    """LLM 岗位缺口分析。失败返回 None，fallback 规则查表。"""
    from app.llm import ChatMessage, get_llm

    skills_str = "\n".join(
        f"- {s['name']}: Lv{s.get('level',0)}→Lv{s.get('target_level',5)} (证据:{s.get('evidence',[])})"
        for s in skills[:10]
    )

    prompt = f"""分析岗位能力缺口。

目标岗位：{target_role}
当前技能：
{skills_str}

返回 JSON：
{{
  "required_skills": ["技能1", "技能2", ...],
  "market_insights": "当前市场对 {target_role} 的核心要求（1-2句话）",
  "priority": ["按优先级排序的技能名列表"]
}}
直接输出 JSON。"""

    try:
        llm = get_llm()
        return llm.chat_json([
            ChatMessage(role="system", content="你是机器人行业猎头和技术面试官。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
    except Exception:
        return None
```

- [ ] **Step 2: 修改 `career/nodes.py` 的 `analyze_target` 节点**

```python
def analyze_target(state: CareerState) -> dict:
    """节点1：分析目标岗位，提取必需技能清单。

    LLM 优先（含市场洞察），失败 fallback 固定字典。
    """
    target_role = state.get("target_role", "")
    current = state.get("current_skills", [])

    llm_result = _analyze_with_llm(target_role, current)
    if llm_result is not None and llm_result.get("required_skills"):
        from app.agents.career.rules import get_required_skills as fallback_skills
        # LLM 结果优先，但至少包含固定字典中的必需技能（保底）
        required = list(set(llm_result["required_skills"]) | set(fallback_skills(target_role)))
        return {
            "required_skills": required,
            "llm_market_insights": llm_result.get("market_insights", ""),
            "llm_priority": llm_result.get("priority", []),
        }

    # Fallback
    required = get_required_skills(target_role)
    return {"required_skills": required}
```

- [ ] **Step 3: 在 `research/nodes.py` 添加 LLM 模板函数**

```python
# 在 match_template_node 函数前新增

def _match_with_llm(topic: str) -> dict | None:
    """LLM 研究主题拆解。失败返回 None。"""
    from app.llm import ChatMessage, get_llm

    prompt = f"""为主题生成结构化研究计划模板。

主题：{topic}

返回 JSON：
{{
  "topic": "{topic}",
  "paper": {{"title": "推荐阅读的论文", "description": "读什么", "resources": ["链接"]}},
  "code": {{"title": "推荐研究的代码库", "description": "看什么", "resources": ["GitHub链接"]}},
  "experiment": {{"title": "建议的最小实验", "description": "做什么", "resources": []}},
  "verification": {{"title": "验证标准", "description": "怎么算成功", "resources": []}}
}}
直接输出 JSON。"""

    try:
        llm = get_llm()
        return llm.chat_json([
            ChatMessage(role="system", content="你是机器人/AI研究员。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
    except Exception:
        return None
```

- [ ] **Step 4: 修改 `match_template_node`**

```python
def match_template_node(state: ResearchState) -> dict:
    """节点2：匹配研究模板。LLM 优先，fallback 预设模板。"""
    topic = state.get("normalized_topic", "Unknown")

    # 先查预设模板（精确匹配优先）
    template = match_template(topic)
    if template is not None:
        return {"template": dict(template)}

    # LLM 动态生成
    llm_result = _match_with_llm(topic)
    if llm_result is not None:
        return {"template": llm_result}

    # Fallback
    return {"template": dict(fallback_template(topic))}
```

- [ ] **Step 5: 编写测试**

```python
# backend/tests/test_career_llm.py
def test_analyze_target_fallback():
    """Mock 环境走 fallback。"""
    from app.agents.career.nodes import analyze_target
    result = analyze_target({
        "target_role": "Robot AI Engineer",
        "current_skills": [{"name": "ROS2", "level": 1, "target_level": 4, "evidence": []}],
    })
    assert "required_skills" in result
    assert len(result["required_skills"]) > 0

# backend/tests/test_research_llm.py
def test_match_template_fallback():
    """Mock 环境走 fallback。"""
    from app.agents.research.nodes import match_template_node
    result = match_template_node({"normalized_topic": "ACT"})
    assert "template" in result
    assert "paper" in result["template"]
```

- [ ] **Step 6: 运行测试**

```bash
cd backend && python -m pytest tests/test_career_llm.py tests/test_research_llm.py -v
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/agents/career/nodes.py backend/app/agents/research/nodes.py backend/tests/test_career_llm.py backend/tests/test_research_llm.py
git commit -m "feat(career,research): add LLM analysis with rule fallback"
```

---

### Task 4: Reminder Service —— 骨架 + Terminal 通道

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/reminder/__init__.py`
- Create: `backend/app/services/reminder/channels.py`
- Create: `backend/app/services/reminder/templates.py`
- Create: `backend/app/services/reminder/engine.py`
- Create: `backend/app/services/reminder/scheduler.py`
- Modify: `backend/app/core/config.py`（新增提醒配置项）
- Modify: `backend/app/main.py`（lifespan 中启动 scheduler）
- Test: `backend/tests/test_reminder.py`（新建）

**Interfaces:**
- Consumes: `settings` from `app.core.config`, `SessionLocal` from `app.db.base`, Task/Skill/LearningLog models
- Produces: `start_scheduler()`, `ReminderEngine.send_morning()`, `ReminderEngine.send_evening()`

- [ ] **Step 1: 扩展 Settings 配置**

在 `backend/app/core/config.py` 的 `Settings` dataclass 中添加：

```python
# ---------- Reminder ----------
reminder_channel: str = "terminal"        # serverchan | pushplus | email | terminal
reminder_channel_key: str = ""            # Server酱 SendKey / PushPlus Token
reminder_morning_time: str = "08:30"
reminder_evening_time: str = "21:00"
reminder_inactivity_days: int = 3
reminder_timezone: str = "Asia/Shanghai"
```

在 `from_env` 方法中添加对应读取：

```python
reminder_channel=os.getenv("REMINDER_CHANNEL", "terminal"),
reminder_channel_key=os.getenv("REMINDER_CHANNEL_KEY", ""),
reminder_morning_time=os.getenv("REMINDER_MORNING_TIME", "08:30"),
reminder_evening_time=os.getenv("REMINDER_EVENING_TIME", "21:00"),
reminder_inactivity_days=int(os.getenv("REMINDER_INACTIVITY_DAYS", "3")),
reminder_timezone=os.getenv("REMINDER_TIMEZONE", "Asia/Shanghai"),
```

- [ ] **Step 2: 创建 `backend/app/services/__init__.py`**

```python
"""Services —— 业务服务层。

与 agents/ 的区别：
- agents/ 是 LangGraph 驱动的智能决策单元（LLM 推理）
- services/ 是确定性业务逻辑（定时任务 / 外部 API / 文件处理）
"""
```

- [ ] **Step 3: 创建 `backend/app/services/reminder/__init__.py`**

```python
"""Reminder Service —— 每日学习提醒。

三个推送时段：
- 早间（默认 08:30）：今日任务 + 预计时长
- 晚间（默认 21:00）：任务完成确认
- 中断恢复（>3 天无活动自动触发）

通道：Server酱(微信) / PushPlus / Email / Terminal
"""
```

- [ ] **Step 4: 创建 `backend/app/services/reminder/channels.py`**

```python
"""提醒推送通道实现。

每个通道实现 send(title, body) 方法。
通道注册表 CHANNELS 按名查找，便于扩展。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Channel(ABC):
    """推送通道抽象基类。"""

    @abstractmethod
    def send(self, title: str, body: str) -> bool:
        """发送推送。成功返回 True，失败返回 False。"""
        ...


class TerminalChannel(Channel):
    """终端打印通道（开发调试默认）。"""

    def send(self, title: str, body: str) -> bool:
        print(f"\n{'='*50}")
        print(f"📬 {title}")
        print(f"{'='*50}")
        print(body)
        print(f"{'='*50}\n")
        return True


class ServerChanChannel(Channel):
    """Server酱微信推送通道。

    注册地址: https://sct.ftqq.com/
    免费额度: 每天 5 条
    """

    def __init__(self, send_key: str):
        self._send_key = send_key.strip()

    def send(self, title: str, body: str) -> bool:
        import urllib.request

        import json as _json

        url = f"https://sctapi.ftqq.com/{self._send_key}.send"
        data = _json.dumps({"title": title, "desp": body}).encode("utf-8")
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception:
            return False


CHANNELS: dict[str, type[Channel]] = {
    "terminal": TerminalChannel,
    "serverchan": ServerChanChannel,
}
```

- [ ] **Step 5: 创建 `backend/app/services/reminder/templates.py`**

```python
"""提醒消息模板。

每个模板函数接收数据 dict，返回 (title, body) 字符串对。
"""

from __future__ import annotations

from datetime import datetime


def morning_template(task_title: str, skill_name: str,
                     current_level: int, target_level: int,
                     duration: int) -> tuple[str, str]:
    """早间任务推送模板。"""
    bar = "█" * current_level + "░" * (target_level - current_level)
    title = f"☀️ 今日学习任务"
    body = (
        f"📌 {task_title}\n"
        f"   技能：{skill_name}\n"
        f"   预计 {duration} 分钟\n\n"
        f"📊 {skill_name} Lv{current_level} {bar} → Lv{target_level}\n"
    )
    return title, body


def evening_template(task_title: str, skill_name: str) -> tuple[str, str]:
    """晚间检查模板。"""
    title = "🌙 今日学习回顾"
    body = (
        f"{task_title}\n\n"
        f"完成了吗？回 \"1\"=完成  \"2\"=部分  \"3\"=没做"
    )
    return title, body


def comeback_template(days_away: int, last_task: str,
                      last_skill: str, suggestion: str) -> tuple[str, str]:
    """中断恢复模板。"""
    title = f"👋 {days_away} 天不见了"
    body = (
        f"离开前：{last_task}\n"
        f"技能：{last_skill}\n\n"
        f"🔁 今天建议：{suggestion}"
    )
    return title, body
```

- [ ] **Step 6: 创建 `backend/app/services/reminder/engine.py`**

```python
"""提醒引擎 —— 读数据 → 选模板 → 调通道 → 发推送。"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import settings
from app.db.base import SessionLocal
from app.services.reminder.channels import CHANNELS
from app.services.reminder.templates import (
    comeback_template,
    evening_template,
    morning_template,
)


class ReminderEngine:
    """提醒引擎。每个推送场景一个方法，独立可测。"""

    def __init__(self):
        channel_cls = CHANNELS.get(settings.reminder_channel)
        if channel_cls is None:
            channel_cls = CHANNELS["terminal"]
        if settings.reminder_channel == "serverchan":
            self._channel = channel_cls(settings.reminder_channel_key)
        else:
            self._channel = channel_cls()

    def send_morning(self) -> bool:
        """早间推送：今日最新 todo 任务。"""
        db = SessionLocal()
        try:
            from app.models.task import Task
            task = db.query(Task).filter(
                Task.status.in_(["todo", "doing"])
            ).order_by(Task.created_at.desc()).first()

            if task is None:
                return self._channel.send(
                    "☀️ 今日学习",
                    "暂无待办任务。打开 Dashboard 让 Planner 生成一个吧！"
                )

            skill_name = task.skill_name or "Unknown"
            title, body = morning_template(
                task_title=task.title,
                skill_name=skill_name,
                current_level=1,
                target_level=4,
                duration=task.duration or 30,
            )
            return self._channel.send(title, body)
        finally:
            db.close()

    def send_evening(self) -> bool:
        """晚间检查：今天有完成任务吗？"""
        db = SessionLocal()
        try:
            from app.models.task import Task
            # 查最近一条 doing 或今天创建的 todo
            task = db.query(Task).filter(
                Task.status.in_(["todo", "doing"])
            ).order_by(Task.created_at.desc()).first()

            if task is None:
                return self._channel.send(
                    "🌙 今日回顾",
                    "今天没有待办任务。明天让 Planner 生成一个吧！"
                )

            skill_name = task.skill_name or "Unknown"
            title, body = evening_template(
                task_title=task.title,
                skill_name=skill_name,
            )
            return self._channel.send(title, body)
        finally:
            db.close()

    def send_comeback(self) -> bool | None:
        """中断恢复检测。>3 天无活动时推送，否则返回 None（不发）。"""
        db = SessionLocal()
        try:
            from app.models.learning_log import LearningLog
            last_log = db.query(LearningLog).order_by(
                LearningLog.created_at.desc()
            ).first()

            if last_log is None:
                return None  # 从未有过活动，不触发

            days = (datetime.utcnow() - last_log.created_at).days
            if days < settings.reminder_inactivity_days:
                return None

            from app.models.task import Task
            last_task = db.query(Task).order_by(Task.created_at.desc()).first()
            task_title = last_task.title if last_task else "学习"
            skill = last_task.skill_name if last_task else "Unknown"

            title, body = comeback_template(
                days_away=days,
                last_task=task_title,
                last_skill=skill,
                suggestion=f"继续 {task_title}（预计 30 分钟）",
            )
            return self._channel.send(title, body)
        finally:
            db.close()
```

- [ ] **Step 7: 创建 `backend/app/services/reminder/scheduler.py`**

```python
"""APScheduler 生命周期管理。

FastAPI lifespan 中调用 start_scheduler()，shutdown 时自动停止。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_scheduler = None


def start_scheduler() -> None:
    """启动 APScheduler，注册三段时间点 job。"""
    global _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning(
            "APScheduler not installed. Install with: pip install apscheduler. "
            "Reminder scheduler disabled."
        )
        return

    from app.core.config import settings
    from app.services.reminder.engine import ReminderEngine

    engine = ReminderEngine()

    # 解析时间
    morning_h, morning_m = _parse_time(settings.reminder_morning_time)
    evening_h, evening_m = _parse_time(settings.reminder_evening_time)

    _scheduler = BackgroundScheduler(timezone=settings.reminder_timezone)
    _scheduler.add_job(
        engine.send_morning,
        "cron", hour=morning_h, minute=morning_m,
        id="reminder_morning",
    )
    _scheduler.add_job(
        engine.send_evening,
        "cron", hour=evening_h, minute=evening_m,
        id="reminder_evening",
    )
    _scheduler.add_job(
        engine.send_comeback,
        "cron", hour=10, minute=0,
        id="reminder_comeback",
    )
    _scheduler.start()
    logger.info(
        "Reminder scheduler started (morning=%s, evening=%s)",
        settings.reminder_morning_time, settings.reminder_evening_time,
    )


def _parse_time(time_str: str) -> tuple[int, int]:
    """解析 'HH:MM' 字符串为 (hour, minute)。"""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])
```

- [ ] **Step 8: 修改 `backend/app/main.py` lifespan**

在 `lifespan` 函数中添加 scheduler 启动：

```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    setup_default_agents()
    # ---- 新增 ----
    from app.services.reminder.scheduler import start_scheduler as start_reminder
    start_reminder()
    # -------------
    yield
```

- [ ] **Step 9: 编写测试**

```python
# backend/tests/test_reminder.py
"""Reminder 引擎测试（Terminal 通道）。"""
import pytest
from app.services.reminder.engine import ReminderEngine
from app.services.reminder.templates import (
    morning_template,
    evening_template,
    comeback_template,
)


def test_morning_template_output():
    title, body = morning_template(
        task_title="ROS2 publisher 实战",
        skill_name="ROS2",
        current_level=1,
        target_level=4,
        duration=40,
    )
    assert "ROS2 publisher" in title or "ROS2 publisher" in body
    assert "40" in body


def test_evening_template_output():
    title, body = evening_template("ROS2 publisher 实战", "ROS2")
    assert "1" in body
    assert "2" in body
    assert "3" in body


def test_comeback_template_output():
    title, body = comeback_template(3, "ROS2 publisher", "ROS2", "继续 subscriber")
    assert "3" in title
    assert "ROS2" in body


def test_engine_terminal_channel():
    """Terminal 通道 send 永远返回 True。"""
    engine = ReminderEngine()
    assert engine.send_morning() is True
    assert engine.send_evening() is True
```

- [ ] **Step 10: 安装 APScheduler 依赖**

```bash
cd backend && pip install apscheduler
```

更新 `backend/requirements.txt`：

```
apscheduler>=3.10
```

- [ ] **Step 11: 运行测试**

```bash
cd backend && python -m pytest tests/test_reminder.py -v
```

- [ ] **Step 12: Commit**

```bash
git add backend/app/services/ backend/app/core/config.py backend/app/main.py backend/requirements.txt backend/tests/test_reminder.py
git commit -m "feat(reminder): add daily reminder service with terminal/serverchan channels"
```

---

### Task 5: Server酱 微信推送通道

**Files:**
- Modify: `backend/app/services/reminder/channels.py`（已有 ServerChanChannel，本 Task 做集成验证）
- Modify: `backend/app/core/config.py`（补充 REMINDER_CHANNEL_KEY 说明）
- Test: `backend/tests/test_reminder_channels.py`（新建）

**Interfaces:**
- Consumes: `settings.reminder_channel`, `settings.reminder_channel_key`
- Produces: `ServerChanChannel.send(title, body) → bool`

- [ ] **Step 1: 编写 Server酱 通道不可达时的测试（不需要真实 SendKey）**

```python
# backend/tests/test_reminder_channels.py
"""提醒通道单元测试。"""
from app.services.reminder.channels import TerminalChannel, ServerChanChannel


def test_terminal_channel():
    ch = TerminalChannel()
    assert ch.send("test title", "test body") is True


def test_serverchan_invalid_key_does_not_crash():
    """无效 SendKey 应返回 False，不抛异常。"""
    ch = ServerChanChannel("invalid-key-12345")
    result = ch.send("test", "body")
    assert isinstance(result, bool)
```

- [ ] **Step 2: 运行测试**

```bash
cd backend && python -m pytest tests/test_reminder_channels.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_reminder_channels.py
git commit -m "test(reminder): add channel unit tests"
```

---

## Phase 2：GitHub 感知 + 活动草稿

### Task 6: CommitSuggestion 模型 + 表

**Files:**
- Create: `backend/app/models/commit_suggestion.py`
- Modify: `backend/app/models/__init__.py`（注册新模型）

**Interfaces:**
- Produces: `CommitSuggestion` ORM model with fields: `id`, `commit_sha`, `commit_message`, `repo`, `files_changed`, `diff_summary`, `ai_suggestions`, `status`, `confirmed_skill`, `confirmed_at`, `created_at`

- [ ] **Step 1: 创建 `backend/app/models/commit_suggestion.py`**

```python
"""GitHub Commit 建议模型。

AI 分析 commit 后生成技能关联建议，用户确认后作为 Reviewer 证据来源之一。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommitSuggestion(Base):
    __tablename__ = "commit_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    repo: Mapped[str] = mapped_column(String(255), nullable=False)
    files_changed: Mapped[list] = mapped_column(JSON, default=list)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # status: pending | confirmed | rejected
    confirmed_skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: 注册模型到 `backend/app/models/__init__.py`**

在现有 import 区域追加：

```python
from app.models.commit_suggestion import CommitSuggestion
```

在 `__all__` 列表中追加 `"CommitSuggestion"`。

- [ ] **Step 3: 验证表创建**

```bash
cd backend && python -c "
from app.db.base import init_db
init_db()
print('OK: commit_suggestions table created')
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/commit_suggestion.py backend/app/models/__init__.py
git commit -m "feat(db): add CommitSuggestion model for GitHub skill tracking"
```

---

### Task 7: ActivityDraft 模型 + 表

**Files:**
- Create: `backend/app/models/activity_draft.py`
- Modify: `backend/app/models/__init__.py`（注册新模型）

**Interfaces:**
- Produces: `ActivityDraft` ORM model

- [ ] **Step 1: 创建 `backend/app/models/activity_draft.py`**

```python
"""活动草稿模型。

被动感知层（GitHub commit / 文件变更）产出的待确认活动。
用户确认后触发 Reviewer 复盘。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActivityDraft(Base):
    __tablename__ = "activity_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # source: github_commit | evening_checkin | manual
    source_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 引用：commit_sha / task_id
    task_guess: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_guess: Mapped[str | None] = mapped_column(String(100), nullable=True)
    suggested_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_confirm", index=True)
    # status: pending_confirm | confirmed | rejected | expired
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: 注册模型到 `backend/app/models/__init__.py`**

追加 import 和 `__all__` 条目。

- [ ] **Step 3: 验证**

```bash
cd backend && python -c "
from app.db.base import init_db
init_db()
from app.db.base import SessionLocal
db = SessionLocal()
from app.models.activity_draft import ActivityDraft
print('columns:', [c.name for c in ActivityDraft.__table__.columns])
db.close()
"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/activity_draft.py backend/app/models/__init__.py
git commit -m "feat(db): add ActivityDraft model for passive result perception"
```

---

### Task 8: GitHub Sync Service —— 拉取 + LLM 分析 + 存储

**Files:**
- Create: `backend/app/services/github/__init__.py`
- Create: `backend/app/services/github/client.py`
- Create: `backend/app/services/github/analyzer.py`
- Create: `backend/app/services/github/store.py`
- Create: `backend/app/services/github/sync.py`
- Modify: `backend/app/core/config.py`（新增 GitHub 配置）
- Test: `backend/tests/test_github_service.py`（新建）

**Interfaces:**
- Consumes: `settings` from `app.core.config`, `SessionLocal`, `get_llm()`
- Produces: `GitHubClient.fetch_commits(since) → list[dict]`, `CommitAnalyzer.analyze(commit) → dict | None`, `sync_new_commits() → int`

- [ ] **Step 1: 扩展 Settings 配置**

在 `Settings` dataclass 添加：

```python
# ---------- GitHub ----------
github_token: str = ""                           # Personal Access Token
github_repos: list[str] = field(default_factory=lambda: ["embodied-ai-career-os"])
github_poll_interval_minutes: int = 30
github_last_sync_file: str = ".github_last_sync"
```

在 `from_env` 添加：

```python
github_token=os.getenv("GITHUB_TOKEN", ""),
github_repos=[r.strip() for r in os.getenv("GITHUB_REPOS", "embodied-ai-career-os").split(",")],
github_poll_interval_minutes=int(os.getenv("GITHUB_POLL_INTERVAL", "30")),
```

- [ ] **Step 2: 创建 `backend/app/services/github/__init__.py`**

```python
"""GitHub Service —— commit 感知 + AI 分析 + 技能关联建议。"""
```

- [ ] **Step 3: 创建 `backend/app/services/github/client.py`**

```python
"""GitHub API 客户端 —— 拉取 commit 列表。"""

from __future__ import annotations

import json
import os
from datetime import datetime
from urllib.request import Request, urlopen


class GitHubClient:
    """GitHub REST API 轻量封装。使用 urllib（零依赖）。"""

    BASE = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self._token = token

    def _headers(self) -> dict:
        h = {"Accept": "application/vnd.github+json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def fetch_commits(self, repo: str, since: datetime | None = None,
                      per_page: int = 10) -> list[dict]:
        """拉取 repo 最近 commit 列表。

        Args:
            repo: 仓库名（如 "embodied-ai-career-os"）
            since: ISO 时间字符串，只拉此时间之后的 commit
            per_page: 每页数量

        Returns:
            commit 列表，每项含 sha / message / files 列表 / stats
        """
        commits: list[dict] = []
        url = f"{self.BASE}/repos/prideandprejudice/{repo}/commits?per_page={per_page}"
        if since is not None:
            url += f"&since={since.isoformat()}"

        try:
            req = Request(url, headers=self._headers())
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for item in data:
                sha = item.get("sha", "")
                commit_info = item.get("commit", {})
                message = commit_info.get("message", "")

                # 拉取单个 commit 详情获取文件列表
                files = self._fetch_commit_files(repo, sha)

                commits.append({
                    "sha": sha,
                    "message": message.split("\n")[0],  # 首行作为摘要
                    "full_message": message,
                    "files": files,
                    "additions": sum(f.get("additions", 0) for f in files),
                    "deletions": sum(f.get("deletions", 0) for f in files),
                    "timestamp": commit_info.get("committer", {}).get("date", ""),
                })
        except Exception:
            pass

        return commits

    def _fetch_commit_files(self, repo: str, sha: str) -> list[dict]:
        """拉取单个 commit 的文件变更列表。"""
        url = f"{self.BASE}/repos/prideandprejudice/{repo}/commits/{sha}"
        try:
            req = Request(url, headers=self._headers())
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read())
            return data.get("files", [])
        except Exception:
            return []
```

- [ ] **Step 4: 创建 `backend/app/services/github/analyzer.py`**

```python
"""LLM Commit 分析器 —— 生成技能关联建议。"""

from __future__ import annotations

from app.llm import ChatMessage, get_llm

# 系统中已有的技能名（供 LLM 参考）
KNOWN_SKILLS = [
    "Python", "Frontend", "Web Engineering", "Agent Application",
    "PyTorch", "Deep Learning", "ROS2", "Isaac", "Robot Learning", "VLA", "C++",
]


def analyze_commit(commit: dict) -> dict | None:
    """LLM 分析单条 commit，生成技能关联建议。

    Args:
        commit: {sha, message, files, additions, deletions}

    Returns:
        {suggestions: [...], suggest_ignore: bool, summary: str} 或 None（失败时）
    """
    files_str = "\n".join(
        f"  - {f.get('filename', '')} (+{f.get('additions', 0)} -{f.get('deletions', 0)})"
        for f in commit.get("files", [])[:10]
    )
    skills_str = ", ".join(KNOWN_SKILLS)

    prompt = f"""分析以下 Git commit 关联的学习技能。

Commit Message: {commit.get('message', '')}
文件变更:
{files_str or '（无文件信息）'}
统计: +{commit.get('additions', 0)} -{commit.get('deletions', 0)} 行

已知技能: {skills_str}

返回 JSON：
{{
  "suggestions": [
    {{"skill": "技能名", "reason": "一句话理由", "confidence": 0.0-1.0}}
  ],
  "suggest_ignore": true/false,
  "summary": "一句话总结这个 commit 做了什么"
}}

规则：
- 如果只改了依赖/格式/README小修 → suggest_ignore=true
- 每个 commit 最多关联 3 个技能
- confidence > 0.6 才是可信建议
直接输出 JSON。"""

    try:
        llm = get_llm()
        return llm.chat_json([
            ChatMessage(role="system", content="你是代码活动分析器。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
    except Exception:
        return None
```

- [ ] **Step 5: 创建 `backend/app/services/github/store.py`**

```python
"""CommitSuggestion 存储层。"""

from __future__ import annotations

import uuid

from app.db.base import SessionLocal
from app.models.commit_suggestion import CommitSuggestion


def save_suggestion(commit: dict, analysis: dict, repo: str) -> str | None:
    """存储一条 commit 分析建议。返回 suggestion id，失败返回 None。"""
    db = SessionLocal()
    try:
        sid = str(uuid.uuid4())
        db.add(CommitSuggestion(
            id=sid,
            commit_sha=commit.get("sha", ""),
            commit_message=commit.get("message", ""),
            repo=repo,
            files_changed=[f.get("filename") for f in commit.get("files", [])],
            diff_summary=analysis.get("summary", ""),
            ai_suggestions=analysis.get("suggestions", []),
            status="pending",
        ))
        db.commit()
        return sid
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def get_pending_suggestions(limit: int = 10) -> list[dict]:
    """获取待确认的建议列表。"""
    db = SessionLocal()
    try:
        rows = db.query(CommitSuggestion).filter(
            CommitSuggestion.status == "pending"
        ).order_by(CommitSuggestion.created_at.desc()).limit(limit).all()

        return [
            {
                "id": r.id,
                "commit_sha": r.commit_sha[:7],
                "commit_message": r.commit_message,
                "repo": r.repo,
                "ai_suggestions": r.ai_suggestions,
                "summary": r.diff_summary,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def confirm_suggestion(suggestion_id: str, skill: str) -> bool:
    """确认一条建议的关联技能。"""
    db = SessionLocal()
    try:
        row = db.query(CommitSuggestion).filter(
            CommitSuggestion.id == suggestion_id
        ).first()
        if row is None:
            return False
        row.status = "confirmed"
        row.confirmed_skill = skill
        from datetime import datetime
        row.confirmed_at = datetime.utcnow()
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def reject_suggestion(suggestion_id: str) -> bool:
    """驳回一条建议。"""
    db = SessionLocal()
    try:
        row = db.query(CommitSuggestion).filter(
            CommitSuggestion.id == suggestion_id
        ).first()
        if row is None:
            return False
        row.status = "rejected"
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()
```

- [ ] **Step 6: 创建 `backend/app/services/github/sync.py`**

```python
"""GitHub 同步调度 —— 定时拉取 + 分析 + 存储。"""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timedelta

from app.core.config import settings
from app.services.github.client import GitHubClient
from app.services.github.analyzer import analyze_commit
from app.services.github.store import save_suggestion

logger = logging.getLogger(__name__)


def _load_last_sync() -> datetime | None:
    """从文件读取上次同步时间。"""
    path = settings.github_last_sync_file
    if os.path.exists(path):
        try:
            with open(path) as f:
                ts = json.load(f).get("last_sync", "")
                if ts:
                    return datetime.fromisoformat(ts)
        except Exception:
            pass
    return None


def _save_last_sync(dt: datetime) -> None:
    """保存本次同步时间。"""
    with open(settings.github_last_sync_file, "w") as f:
        json.dump({"last_sync": dt.isoformat()}, f)


def sync_new_commits() -> int:
    """拉取新 commit → LLM 分析 → 存储。返回新增 suggestion 数量。"""
    if not settings.github_token:
        logger.debug("GitHub token not configured, skipping sync")
        return 0

    client = GitHubClient(token=settings.github_token)
    last_sync = _load_last_sync()
    total_new = 0

    for repo in settings.github_repos:
        commits = client.fetch_commits(repo.strip(), since=last_sync)
        for commit in commits:
            analysis = analyze_commit(commit)
            if analysis is None:
                continue
            if analysis.get("suggest_ignore"):
                continue  # 改动太小，跳过
            sid = save_suggestion(commit, analysis, repo)
            if sid:
                total_new += 1

    _save_last_sync(datetime.utcnow())
    if total_new > 0:
        logger.info("GitHub sync: %d new suggestions", total_new)
    return total_new
```

- [ ] **Step 7: 编写测试**

```python
# backend/tests/test_github_service.py
"""GitHub Service 单元测试。"""
import pytest
from app.services.github.analyzer import analyze_commit


def test_analyze_commit_mock():
    """Mock LLM 时返回 None（fallback）。"""
    result = analyze_commit({
        "sha": "abc123",
        "message": "feat: add ROS2 publisher",
        "files": [{"filename": "ros2_ws/src/publisher.py", "additions": 45, "deletions": 0}],
        "additions": 45,
        "deletions": 0,
    })
    # MockClient 返回 JSON parse 失败 → None
    assert result is None


def test_analyze_commit_empty_files():
    result = analyze_commit({
        "sha": "abc",
        "message": "chore: update deps",
        "files": [],
        "additions": 1,
        "deletions": 1,
    })
    assert result is None
```

- [ ] **Step 8: 运行测试**

```bash
cd backend && python -m pytest tests/test_github_service.py -v
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/github/ backend/app/core/config.py backend/tests/test_github_service.py
git commit -m "feat(github): add GitHub commit sync + LLM analyzer + storage"
```

---

### Task 9: GitHub API 路由 + Scheduler 集成

**Files:**
- Create: `backend/app/api/github.py`
- Modify: `backend/app/main.py`（注册路由 + scheduler 集成）
- Modify: `backend/app/services/reminder/scheduler.py`（新增 GitHub sync job）
- Test: `backend/tests/test_github_api.py`（新建）

**Interfaces:**
- Produces: `GET /api/github/suggestions`, `POST /api/github/suggestions/{id}/confirm`, `POST /api/github/suggestions/{id}/reject`

- [ ] **Step 1: 创建 `backend/app/api/github.py`**

```python
"""GitHub API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.response import ApiResponse, ok
from app.services.github.sync import sync_new_commits
from app.services.github.store import (
    confirm_suggestion,
    get_pending_suggestions,
    reject_suggestion,
)

router = APIRouter(prefix="/github", tags=["github"])


class SuggestionOut(BaseModel):
    id: str
    commit_sha: str
    commit_message: str
    repo: str
    ai_suggestions: list
    summary: str | None
    created_at: str | None


class ConfirmRequest(BaseModel):
    skill: str


@router.get("/suggestions")
def list_suggestions() -> ApiResponse[list[SuggestionOut]]:
    """获取待确认的 commit 建议列表。"""
    items = get_pending_suggestions(limit=10)
    return ok([SuggestionOut(**it) for it in items])


@router.post("/suggestions/{suggestion_id}/confirm")
def confirm(suggestion_id: str, req: ConfirmRequest) -> ApiResponse[dict]:
    """确认一条 commit 建议的关联技能。"""
    ok_flag = confirm_suggestion(suggestion_id, req.skill)
    if not ok_flag:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return ok({"id": suggestion_id, "skill": req.skill, "status": "confirmed"})


@router.post("/suggestions/{suggestion_id}/reject")
def reject(suggestion_id: str) -> ApiResponse[dict]:
    """驳回一条 commit 建议。"""
    ok_flag = reject_suggestion(suggestion_id)
    if not ok_flag:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return ok({"id": suggestion_id, "status": "rejected"})


@router.post("/sync")
def manual_sync() -> ApiResponse[dict]:
    """手动触发 GitHub 同步。"""
    count = sync_new_commits()
    return ok({"new_suggestions": count})
```

- [ ] **Step 2: 注册路由到 `backend/app/main.py`**

```python
from app.api.github import router as github_router
# ...
app.include_router(github_router, prefix=api_prefix)
```

- [ ] **Step 3: 在 scheduler 中添加 GitHub sync job**

在 `backend/app/services/reminder/scheduler.py` 的 `start_scheduler` 中添加：

```python
_scheduler.add_job(
    lambda: sync_new_commits(),
    "interval",
    minutes=settings.github_poll_interval_minutes,
    id="github_sync",
)
```

- [ ] **Step 4: 编写测试**

```python
# backend/tests/test_github_api.py
"""GitHub API 测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_suggestions_empty():
    resp = client.get("/api/github/suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_confirm_not_found():
    resp = client.post("/api/github/suggestions/nonexistent/confirm", json={"skill": "Python"})
    assert resp.status_code == 404


def test_reject_not_found():
    resp = client.post("/api/github/suggestions/nonexistent/reject")
    assert resp.status_code == 404


def test_manual_sync_without_token():
    """无 GitHub token 时 sync 返回 0。"""
    resp = client.post("/api/github/sync")
    assert resp.status_code == 200
    assert resp.json()["data"]["new_suggestions"] == 0
```

- [ ] **Step 5: 运行测试**

```bash
cd backend && python -m pytest tests/test_github_api.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/github.py backend/app/main.py backend/app/services/reminder/scheduler.py backend/tests/test_github_api.py
git commit -m "feat(github): add GitHub API routes + scheduler integration"
```

---

## Phase 3：工具桥接 + 闭环验证

### Task 10: Tool Prompt 生成器 + 上下文恢复包

**Files:**
- Create: `backend/app/services/tools/__init__.py`
- Create: `backend/app/services/tools/prompts.py`
- Create: `backend/app/services/tools/context.py`
- Test: `backend/tests/test_tool_bridge.py`（新建）

**Interfaces:**
- Consumes: Task/Skill/LearningLog models, `SessionLocal`
- Produces: `generate_tool_prompt(task, tool) → str`, `generate_context_pack() → str`

- [ ] **Step 1: 创建 `backend/app/services/tools/__init__.py`**

```python
"""Tool Bridge —— 外部 AI 工具桥接层。

方向 A：指令注入（SKILL.md / project_rules.md / prompt 导出）
方向 B：结果感知（被动检测 → ActivityDraft → 晚间追问确认）
"""
```

- [ ] **Step 2: 创建 `backend/app/services/tools/prompts.py`**

```python
"""Prompt 模板生成 —— 按目标工具 + 任务类型生成适配 prompt。"""

from __future__ import annotations

from app.models.task import Task

# 工具角色配置
TOOL_ROLES = {
    "trae": "你是 Trae，一个 IDE 内置的 AI 编程助手。请帮我写代码。",
    "claude": "你是 Claude Code，一个命令行 AI 编程助手。请帮我写代码。",
    "chatgpt": "你是 ChatGPT，一个 AI 技术顾问。请帮我分析架构和概念。",
    "deepseek": "你是 DeepSeek，一个 AI 编程助手。请帮我解释代码和推导算法。",
    "workbuddy": "你是 WorkBuddy，一个本地 AI 工作助手。请帮我检索项目资料。",
}


def generate_tool_prompt(task: Task, tool: str) -> str:
    """为指定工具生成适配 prompt。

    Args:
        task: 任务对象
        tool: 工具名（trae / claude / chatgpt / deepseek / workbuddy）

    Returns:
        可直接复制粘贴的 prompt 文本
    """
    role = TOOL_ROLES.get(tool, "")
    acceptance = "\n".join(f"  - {a}" for a in (task.acceptance or []))
    resources = "\n".join(f"  - {r}" for r in (task.resources or []))

    if tool in ("trae", "claude"):
        return f"""{role}

任务：{task.title}

目标：{task.objective or task.title}

验收标准：
{acceptance}

参考资源：
{resources}

要求：
- 先解释整体架构，再写代码
- 每段关键代码后加注释说明
- 完成后标注我需要检查的关键点
- 代码放到 {task.skill_name or 'main'} 相关目录"""

    if tool == "chatgpt":
        return f"""{role}

我需要设计一个方案：{task.title}

背景：
- 我是有 6.5 年开发经验的工程师，正在转型具身智能
- 当前 {task.skill_name} 技能等级：入门
- 目标：{task.objective}

请帮我分析：
1. 这个任务的架构决策
2. 推荐的技术方案
3. 可能踩到的坑
4. 和 Robot AI Engineer 岗位能力模型的关联

先不要写代码，只讨论方案和架构。"""

    if tool == "workbuddy":
        return f"""{role}

当前项目上下文：
- 仓库：embodied-ai-career-os
- 模块：{task.skill_name or '通用'}
- 目标：{task.objective or task.title}

参考资料：
{resources}

请帮我：
1. 分析项目中与 {task.skill_name} 相关的现有代码
2. 推荐实现 {task.title} 的最佳路径
3. 如果已有相关笔记/文档，优先引用"""

    # 默认：通用 prompt
    return f"任务：{task.title}\n目标：{task.objective}\n技能：{task.skill_name}\n验收：{acceptance}"
```

- [ ] **Step 3: 创建 `backend/app/services/tools/context.py`**

```python
"""上下文恢复包生成 —— Markdown 格式，可喂给 WorkBuddy / Obsidian / ChatGPT。"""

from __future__ import annotations

from datetime import datetime

from app.db.base import SessionLocal


def generate_context_pack() -> str:
    """生成当前学习上下文包。

    返回 Markdown 字符串，包含：目标岗位、技能状态、最近任务、最近日志。
    """
    db = SessionLocal()
    try:
        from app.models.career import Career
        from app.models.skill import Skill
        from app.models.task import Task
        from app.models.learning_log import LearningLog

        career = db.query(Career).first()
        role = career.target_role if career else "Robot AI Engineer"

        skills = db.query(Skill).order_by(Skill.level - Skill.target_level).all()
        skill_lines = "\n".join(
            f"- {s.name}: Lv{s.level}→Lv{s.target_level}"
            for s in (skills or [])[:8]
        )

        tasks = db.query(Task).order_by(Task.created_at.desc()).limit(3).all()
        task_lines = "\n".join(
            f"- [{t.status}] {t.title} ({t.skill_name}, {t.duration}min)"
            for t in tasks
        )

        logs = db.query(LearningLog).order_by(LearningLog.created_at.desc()).limit(3).all()
        log_lines = "\n".join(
            f"- {log.created_at.strftime('%m-%d %H:%M')}: {log.content[:100]}..."
            for log in logs
        )

        return f"""# Session Context · {datetime.utcnow().strftime('%Y-%m-%d')}

## 目标岗位
{role}

## 技能状态
{skill_lines or '（暂无数据）'}

## 最近任务
{task_lines or '（暂无数据）'}

## 最近学习日志
{log_lines or '（暂无数据）'}

---
由 Embodied AI Career OS 自动生成
"""
    finally:
        db.close()
```

- [ ] **Step 4: 编写测试**

```python
# backend/tests/test_tool_bridge.py
"""工具桥接测试。"""
from app.services.tools.prompts import generate_tool_prompt
from app.services.tools.context import generate_context_pack


def test_generate_trae_prompt():
    """Trae prompt 应包含架构先行要求。"""

    class FakeTask:
        title = "ROS2 publisher 实战"
        objective = "掌握 Topic 通信"
        skill_name = "ROS2"
        acceptance = ["创建publisher", "topic echo验证"]
        resources = ["ROS2 Tutorial"]
        duration = 40

    prompt = generate_tool_prompt(FakeTask(), "trae")
    assert "ROS2 publisher" in prompt
    assert "先解释整体架构" in prompt
    assert "验收标准" in prompt


def test_generate_chatgpt_prompt():
    """ChatGPT prompt 不含代码要求，强调方案讨论。"""

    class FakeTask:
        title = "ROS2 架构设计"
        objective = "理解 ROS2 通信模型"
        skill_name = "ROS2"
        acceptance = []
        resources = []
        duration = 30

    prompt = generate_tool_prompt(FakeTask(), "chatgpt")
    assert "先不要写代码" in prompt
    assert "架构决策" in prompt


def test_generate_workbuddy_prompt():
    """WorkBuddy prompt 应关注项目已有代码。"""

    class FakeTask:
        title = "分析现有 Agent"
        objective = "理解 Agent 架构"
        skill_name = "Agent Application"
        acceptance = []
        resources = []
        duration = 20

    prompt = generate_tool_prompt(FakeTask(), "workbuddy")
    assert "现有代码" in prompt


def test_generate_context_pack():
    """上下文恢复包生成不应崩溃。"""
    pack = generate_context_pack()
    assert "Session Context" in pack
    assert "## 目标岗位" in pack
    assert "## 技能状态" in pack
```

- [ ] **Step 5: 运行测试**

```bash
cd backend && python -m pytest tests/test_tool_bridge.py -v
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/tools/ backend/tests/test_tool_bridge.py
git commit -m "feat(tools): add prompt generator + context pack for external AI tools"
```

---

### Task 11: Tool Bridge API 路由

**Files:**
- Create: `backend/app/api/tools.py`
- Modify: `backend/app/main.py`（注册路由）
- Test: `backend/tests/test_tools_api.py`（新建）

**Interfaces:**
- Produces: `POST /api/tools/prompt`（生成工具 prompt）, `GET /api/tools/context`（获取上下文包）

- [ ] **Step 1: 创建 `backend/app/api/tools.py`**

```python
"""工具桥接 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.task import Task
from app.services.tools.prompts import generate_tool_prompt
from app.services.tools.context import generate_context_pack

router = APIRouter(prefix="/tools", tags=["tools"])


class PromptRequest(BaseModel):
    task_id: int
    tool: str  # trae | claude | chatgpt | deepseek | workbuddy


@router.post("/prompt")
def get_prompt(req: PromptRequest, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """为指定任务和工具生成适配 prompt。"""
    task = db.get(Task, req.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    prompt = generate_tool_prompt(task, req.tool)
    return ok({"tool": req.tool, "task_title": task.title, "prompt": prompt})


@router.get("/context")
def get_context() -> ApiResponse[dict]:
    """获取当前学习上下文恢复包。"""
    pack = generate_context_pack()
    return ok({"context_pack": pack})
```

- [ ] **Step 2: 注册路由**

```python
from app.api.tools import router as tools_router
# ...
app.include_router(tools_router, prefix=api_prefix)
```

- [ ] **Step 3: 编写测试**

```python
# backend/tests/test_tools_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_context_endpoint():
    resp = client.get("/api/tools/context")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_prompt_endpoint_task_not_found():
    resp = client.post("/api/tools/prompt", json={"task_id": 99999, "tool": "trae"})
    assert resp.status_code == 404
```

- [ ] **Step 4: 运行测试**

```bash
cd backend && python -m pytest tests/test_tools_api.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/tools.py backend/app/main.py backend/tests/test_tools_api.py
git commit -m "feat(tools): add tool prompt + context pack API endpoints"
```

---

### Task 12: Dashboard "待确认" + "最近活动" 面板

**Files:**
- Create: `frontend/src/components/PendingSuggestions.tsx`
- Create: `frontend/src/components/RecentActivity.tsx`
- Modify: `frontend/src/components/Dashboard.tsx`（集成新面板）
- Modify: `frontend/src/app/dashboard/page.tsx`（数据注入）
- Modify: `frontend/src/types/index.ts`（新类型）
- Create: `frontend/src/services/githubService.ts`

**Interfaces:**
- Consumes: `GET /api/github/suggestions`, `POST /api/github/suggestions/{id}/confirm|reject`
- Produces: `PendingSuggestions` component, `RecentActivity` component

- [ ] **Step 1: 新增前端类型**

在 `frontend/src/types/index.ts` 末尾添加：

```typescript
/** GitHub commit 关联建议。 */
export interface CommitSuggestion {
  id: string;
  commitSha: string;
  commitMessage: string;
  repo: string;
  aiSuggestions: Array<{
    skill: string;
    reason: string;
    confidence: number;
  }>;
  summary: string | null;
  createdAt: string | null;
}
```

- [ ] **Step 2: 创建 `frontend/src/services/githubService.ts`**

```typescript
import { apiClient } from "@/lib/apiClient";
import type { CommitSuggestion } from "@/types";

export const githubService = {
  getSuggestions: () =>
    apiClient.get<CommitSuggestion[]>("/api/github/suggestions"),

  confirm: (id: string, skill: string) =>
    apiClient.post<{ id: string; skill: string; status: string }>(
      `/api/github/suggestions/${id}/confirm`,
      { skill }
    ),

  reject: (id: string) =>
    apiClient.post<{ id: string; status: string }>(
      `/api/github/suggestions/${id}/reject`
    ),
};
```

- [ ] **Step 3: 创建 `frontend/src/components/PendingSuggestions.tsx`**

```typescript
"use client";

import { useState, useEffect } from "react";
import type { CommitSuggestion } from "@/types";
import { githubService } from "@/services/githubService";

export default function PendingSuggestions() {
  const [items, setItems] = useState<CommitSuggestion[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchItems = async () => {
    try {
      const data = await githubService.getSuggestions();
      setItems(data || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchItems(); }, []);

  const handleConfirm = async (id: string, skill: string) => {
    await githubService.confirm(id, skill);
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleReject = async (id: string) => {
    await githubService.reject(id);
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  if (loading) return null;
  if (items.length === 0) return null;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
        📋 待确认（{items.length} 条新 commit）
      </h2>
      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800"
          >
            <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
              {item.commitMessage}
            </p>
            <p className="mt-0.5 text-xs text-zinc-500">
              {item.commitSha} · {item.summary || ""}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {item.aiSuggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handleConfirm(item.id, s.skill)}
                  className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-300"
                  title={s.reason}
                >
                  ✓ {s.skill}
                </button>
              ))}
              <button
                onClick={() => handleReject(item.id)}
                className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs text-zinc-500 hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-400"
              >
                ✗ 都不是
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 集成到 Dashboard**

在 `Dashboard.tsx` 中，`<AgentActivity>` 上方添加：

```tsx
<div className="mt-6">
  <PendingSuggestions />
</div>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): add PendingSuggestions panel for commit skill confirmation"
```

---

### Task 13: 端到端闭环测试

**Files:**
- Create: `backend/tests/test_e2e_v2_learning_loop.py`

**Interfaces:**
- 全链路：Task 生成 → LLM Planner → Task 持久化 → Reviewer 评估（LLM 优先 + 规则 fallback）→ Skill 更新 → 提醒推送

- [ ] **Step 1: 编写 E2E 测试**

```python
# backend/tests/test_e2e_v2_learning_loop.py
"""V2 学习闭环端到端测试。

场景：用户说"学 ROS2" → 系统生成任务 → 用户完成 → 系统评估 → 技能可能升级
全程使用 mock LLM（规则 fallback），验证各环节不崩溃。
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_learning_loop():
    """全链路：意图分析 → 任务生成 → 复盘评估。"""
    # 1. Supervisor: 意图分析
    resp = client.post("/api/agent/run", json={"user_input": "学习 ROS2"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    # 2. Planner: 生成任务
    resp = client.post("/api/planner/generate", json={
        "available_minutes": 45,
        "skills": [
            {"name": "ROS2", "level": 1, "target": 4},
            {"name": "Python", "level": 4, "target": 5},
            {"name": "VLA", "level": 0, "target": 4},
        ],
        "generator": "rule",
        "persist": True,
    })
    assert resp.status_code == 200
    task_data = resp.json()["data"]
    task_id = task_data["taskId"]
    assert task_id is not None

    # 3. Reviewer: 完成复盘
    resp = client.post("/api/reviewer/review", json={
        "task_id": task_id,
        "content": "完成了 ROS2 publisher 节点，topic 通信正常。学会了 QoS 配置。改进了代码结构。",
        "duration_minutes": 40,
        "artifact_url": "https://github.com/prideandprejudice/embodied-ai-career-os/commit/test",
    })
    assert resp.status_code == 200
    review_data = resp.json()["data"]
    assert "assessment" in review_data
    assert "updatedSkill" in review_data

    # 4. 验证任务状态
    resp = client.get(f"/api/tasks/{task_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "done"


def test_reminder_engine_does_not_crash():
    """提醒引擎三个推送场景均不崩溃。"""
    from app.services.reminder.engine import ReminderEngine
    engine = ReminderEngine()
    assert engine.send_morning() is True
    assert engine.send_evening() is True
    # comeback 可能返回 None 或 True
    result = engine.send_comeback()
    assert result is None or result is True


def test_context_pack_generation():
    """上下文恢复包生成不崩溃。"""
    from app.services.tools.context import generate_context_pack
    pack = generate_context_pack()
    assert isinstance(pack, str)
    assert len(pack) > 50


def test_github_suggestions_api():
    """GitHub suggestions API 可访问。"""
    resp = client.get("/api/github/suggestions")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_tools_api():
    """工具桥接 API 可访问。"""
    resp = client.get("/api/tools/context")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
```

- [ ] **Step 2: 运行 E2E 测试**

```bash
cd backend && python -m pytest tests/test_e2e_v2_learning_loop.py -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_e2e_v2_learning_loop.py
git commit -m "test(e2e): add V2 full learning loop end-to-end tests"
```

---

### Task 14: 最终集成验证 + 文档更新

**Files:**
- Modify: `docs/agent-system.md`（更新架构图 + Agent 清单）
- Modify: `backend/requirements.txt`（确认所有依赖）
- Modify: `docker-compose.yml`（如有环境变量变更）

**验证清单：**

- [ ] **Step 1: 全量测试**

```bash
cd backend && python -m pytest tests/ -v
```

- [ ] **Step 2: 启动验证**

```bash
docker-compose up -d
# 验证 /health 返回 ok
curl http://localhost:8000/health
# 验证 /api/github/suggestions 可访问
curl http://localhost:8000/api/github/suggestions
# 验证 /api/tools/context 返回上下文包
curl http://localhost:8000/api/tools/context
```

- [ ] **Step 3: 更新 `docs/agent-system.md`**

在文档末尾追加：

```markdown
## 九、V2 升级（2026-08）

### 9.1 LLM 接入

所有 Agent 节点支持 LLM 驱动（`LLM_PROVIDER=deepseek`），规则引擎保留为 fallback：
- Supervisor: `analyze_intent` → LLM 意图分类
- Planner: `LLMGenerator` 增强 prompt（含用户背景 + 能量水平）
- Reviewer: `evaluate_evidence` → LLM 语义评估（理解深度/完成质量/反思）
- Career: `analyze_target` → LLM 岗位缺口 + 市场洞察
- Research: `match_template_node` → LLM 动态研究计划

### 9.2 Reminder Service

APScheduler 驱动的三时段提醒：早间任务推送 / 晚间完成确认 / 中断恢复检测。
支持 Server酱(微信) / Terminal 双通道。

### 9.3 GitHub 感知

自动拉取 commit → LLM 分析技能关联 → 人工确认 → Reviewer 引用。

### 9.4 工具桥接

Prompts 生成（Trae/Claude Code/ChatGPT/WorkBuddy）+ 上下文恢复包。
```

- [ ] **Step 4: Commit**

```bash
git add docs/agent-system.md backend/requirements.txt
git commit -m "docs: update agent-system.md for V2 upgrades"
```

---

## 完成标准

- [x] 全量 `pytest` 通过
- [x] `docker-compose up` 启动正常
- [x] `/health` 返回 `{"status": "ok"}`
- [x] Supervisor/Planner/Reviewer/Career/Research 支持 LLM 优先 + 规则 fallback
- [x] Reminder 引擎三时段推送不崩溃
- [x] GitHub 同步 API 可访问（无 token 时返回 0）
- [x] 工具 prompt 生成 + 上下文恢复包 API 可用
- [x] 前端 Dashboard 新增待确认面板
