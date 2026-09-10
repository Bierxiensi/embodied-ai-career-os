"""面试闭环引擎（纯规则，可解释，不依赖 LLM）。

三个确定性能力：
1. weakness_stats(logs)：把多条面经的 weak_questions 聚合为弱项排行榜（出现次数降序）。
2. weak_to_tasks(weak_items)：每条弱项 → 一个学习任务草稿（回写 Task，形成"面试→补知识"闭环）。
3. pick_questions(items)：按分类 / 难度从题库抽题（优先命中次数少的，保证覆盖面）。

所有函数只操作普通 dict / list，便于单测（不依赖 DB / LLM）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WeakItem:
    """一条聚合后的弱项。"""

    topic: str
    count: int
    log_ids: list[int] = field(default_factory=list)


@dataclass
class TaskDraft:
    """一条待回写为学习任务的任务草稿。"""

    title: str
    objective: str
    duration: int
    difficulty: str
    skill_name: str | None
    acceptance: list[str] = field(default_factory=list)


def _norm_topic(topic: str) -> str:
    """弱项去重口径：去首尾空白（保留原大小写与内部空格，便于展示）。"""
    return topic.strip()


def weakness_stats(logs: list[dict]) -> list[WeakItem]:
    """聚合多条面经的弱项。

    Args:
        logs: 每项形如 {"id": int, "weak_questions": list[str], ...}

    Returns:
        按出现次数降序、其次按 topic 升序的 WeakItem 列表。
    """
    counts: dict[str, int] = {}
    ids: dict[str, list[int]] = {}
    for log in logs:
        log_id = log.get("id")
        for raw in log.get("weak_questions") or []:
            if not raw or not str(raw).strip():
                continue
            topic = _norm_topic(str(raw))
            counts[topic] = counts.get(topic, 0) + 1
            if log_id is not None:
                ids.setdefault(topic, [])
                if log_id not in ids[topic]:
                    ids[topic].append(log_id)

    items = [
        WeakItem(topic=t, count=c, log_ids=ids.get(t, []))
        for t, c in counts.items()
    ]
    items.sort(key=lambda i: (-i.count, i.topic))
    return items


def weak_to_tasks(
    weak_items: list[WeakItem],
    gaps: list[str] | None = None,
    limit: int = 5,
    duration: int = 40,
) -> list[TaskDraft]:
    """弱项（+ 知识缺口）→ 学习任务草稿。

    取前 limit 条：弱项优先，其次 knowledge_gaps 中未与弱项重复的条目。
    """
    topics: list[str] = []
    seen: set[str] = set()
    for w in weak_items:
        if w.topic and w.topic not in seen:
            topics.append(w.topic)
            seen.add(w.topic)
    for g in gaps or []:
        gt = _norm_topic(str(g))
        if gt and gt not in seen:
            topics.append(gt)
            seen.add(gt)

    drafts: list[TaskDraft] = []
    for topic in topics[:limit]:
        drafts.append(TaskDraft(
            title=f"补强：{topic}",
            objective=f"针对面试暴露的弱项「{topic}」做专项补强，能独立讲清原理并给出实践例子",
            duration=duration,
            difficulty="intermediate",
            skill_name=None,
            acceptance=[
                f"能不看资料讲清 {topic} 的核心原理",
                f"写出一个与 {topic} 相关的最小可运行示例 / 实验",
                "记录到 LearningLog 并给出可对外陈述的结论",
            ],
        ))
    return drafts


def pick_questions(
    items: list[dict],
    category: str | None = None,
    difficulty: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """从题库抽题。

    Args:
        items: 每题形如 {"id", "category", "question", "difficulty", "hit_count", ...}
        category: 过滤分类（None 表示不限）
        difficulty: 过滤难度（None 表示不限）
        limit: 最多返回数量

    Returns:
        优先 hit_count 小（练得少 / 更需覆盖）、其次原顺序的题目列表。
    """
    pool = []
    for it in items:
        if category and it.get("category") != category:
            continue
        if difficulty and it.get("difficulty") != difficulty:
            continue
        pool.append(it)
    # 命中次数少者优先；稳定保持原顺序
    pool.sort(key=lambda it: (it.get("hit_count") or 0))
    if limit is not None and limit >= 0:
        pool = pool[:limit]
    return pool
