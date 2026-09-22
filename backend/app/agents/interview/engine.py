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


def _match_skill_name(topic: str) -> str | None:
    """尝试把弱项文本匹配到规范技能名（大小写不敏感）。"""
    try:
        # SKILL_PROFILE 是 SkillProfile 对象列表（core/skill_profile.py），
        # 匹配其 .name 字段，而不是把对象当字符串遍历。
        from app.core.skill_profile import SKILL_PROFILE
        topic_lower = topic.strip().lower()
        for profile in SKILL_PROFILE:
            if profile.name.lower() == topic_lower:
                return profile.name
    except ImportError:
        pass
    return None


def weak_to_tasks(
    weak_items: list[WeakItem],
    gaps: list[str] | None = None,
    limit: int = 5,
    duration: int = 40,
) -> list[TaskDraft]:
    """弱项（+ 知识缺口）→ 学习任务草稿。

    取前 limit 条：弱项优先，其次 knowledge_gaps 中未与弱项重复的条目。
    尝试把弱项文本匹配到规范技能名（skill_name），打通面试→学习→题库闭环。
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
            skill_name=_match_skill_name(topic),
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
    skill_name: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """从题库抽题。

    Args:
        items: 每题形如 {"id", "category", "question", "difficulty", "hit_count", ...}
        category: 过滤分类（None 表示不限）
        difficulty: 过滤难度（None 表示不限）
        skill_name: 过滤关联技能（None 表示不限，精确匹配）
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
        if skill_name and it.get("skill_name") != skill_name:
            continue
        pool.append(it)
    # 命中次数少者优先；稳定保持原顺序
    pool.sort(key=lambda it: (it.get("hit_count") or 0))
    if limit is not None and limit >= 0:
        pool = pool[:limit]
    return pool


# ───────────────────────── P3：题库覆盖率 ─────────────────────────

# 分类目标 —— 裁决计划里的口径冲突（见 docs/platform-direction-30day.md 决策 5）：
#   §十「每天 5 题 × 30 天 = 150」 → **累计目标 150**（上界）
#   §八 Day26/27「50 LLM + 25~30 VLM ≈ 80」 → **核心必达 80**（下界）
# 两个数字都对，混在一起会让人以为要写 150 题而放弃。
# Project / Coding 是把 150 补满的差额，按 40 / 30 分配。
QUESTION_CATEGORY_TARGETS: dict[str, int] = {
    "LLM": 50,
    "Multimodal": 30,
    "Project": 40,
    "Coding": 30,
}
# 核心必达分类（求职主攻盘：LLM + 多模态）
CORE_CATEGORIES: tuple[str, ...] = ("LLM", "Multimodal")
CORE_TARGET = 80


def coverage_matrix(
    questions: list[dict],
    skills: list[str],
    per_skill_target: int = 4,
) -> dict:
    """题库覆盖率：分类进度 + skill×category 矩阵（红格 = 缺）。

    纯函数，只吃普通 dict / list，便于单测。

    Args:
        questions: 每题形如 {"category": str, "skill_name": str | None}
        skills: 矩阵行（技能名，顺序即展示顺序）。题库里出现但不在其中的技能
            会自动补到行尾 —— 否则"录了题却没进矩阵"的缺口会看不见。
        per_skill_target: 单个技能的题量目标（默认 4 = 四个分类各 1 题）

    Returns:
        {
          total, target_total, core_target, core_done, per_skill_target,
          categories: [{key, done, target, gap, core}],
          skills: [{name, total, gap, missing, counts}],
          cells_total, cells_filled,
        }

    「红格」判定：某 (skill, category) 计数为 0 → 计入该技能的 missing。
    """
    cats = list(QUESTION_CATEGORY_TARGETS.keys())

    # 1) 行顺序：传入技能打头，题库里多出来的技能补到行尾
    row_order: list[str] = []
    seen: set[str] = set()
    for s in skills:
        if s and s not in seen:
            row_order.append(s)
            seen.add(s)
    extras = sorted(
        {q.get("skill_name") for q in questions if q.get("skill_name") and q.get("skill_name") not in seen}
    )
    row_order.extend(extras)

    # 2) 计数
    cat_counts: dict[str, int] = {c: 0 for c in cats}
    counts: dict[str, dict[str, int]] = {s: {c: 0 for c in cats} for s in row_order}
    for q in questions:
        cat = q.get("category")
        if cat in cat_counts:
            cat_counts[cat] += 1
        name = q.get("skill_name")
        if name in counts and cat in counts[name]:
            counts[name][cat] += 1

    # 3) 分类进度
    categories = [
        {
            "key": c,
            "done": cat_counts[c],
            "target": QUESTION_CATEGORY_TARGETS[c],
            "gap": max(0, QUESTION_CATEGORY_TARGETS[c] - cat_counts[c]),
            "core": c in CORE_CATEGORIES,
        }
        for c in cats
    ]

    # 4) 技能矩阵行
    skill_rows: list[dict] = []
    filled = 0
    for s in row_order:
        cnt = counts[s]
        total = sum(cnt.values())
        missing = [c for c in cats if cnt[c] == 0]
        filled += len(cats) - len(missing)
        skill_rows.append(
            {
                "name": s,
                "total": total,
                "gap": max(0, per_skill_target - total),
                "missing": missing,
                "counts": cnt,
            }
        )

    return {
        "total": sum(cat_counts.values()),
        "target_total": sum(QUESTION_CATEGORY_TARGETS.values()),
        "core_target": CORE_TARGET,
        "core_done": sum(cat_counts.get(c, 0) for c in CORE_CATEGORIES),
        "per_skill_target": per_skill_target,
        "categories": categories,
        "skills": skill_rows,
        "cells_total": len(row_order) * len(cats),
        "cells_filled": filled,
    }
