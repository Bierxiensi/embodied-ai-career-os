"""赛道完整性护栏（P1，2026-09-22 新增）。

================================================================================
为什么需要这个测试
================================================================================
本项目反复出现同一类缺陷：**数据里出现了一个"不在赛道表里的赛道"**。

已发生的实例：某条 JD 的 ``track='agent'``，而 ``TARGET_ROLES`` 只有
``llm / vlm / ai-algo / embodied`` —— 于是由它派生的任务不属于任何赛道，
在任何"按赛道过滤"的视图里凭空消失（漂移任务）。修那一条数据只要一行 SQL，
但**没有任何东西阻止下一条再出现**。

本测试把这条一致性从"文档里的清单"变成"可执行的断言"：
文档会过时（这条缺陷其实在 2026-09-22 傍晚实测时已不存在，但清单里还挂着），
测试不会。

================================================================================
两层结构（缺一不成立）
================================================================================
1. **配置层哨兵**：赛道集合本身必须是预期的四条。若有人误删/误加赛道，
   下面的数据层断言会因"合法集合变了"而失去意义 —— 所以先钉住集合。
2. **数据层**：库中所有非空 track 值都必须属于该集合。

注：本测试跑在 conftest 的隔离临时库上（``tests/conftest.py`` 模块级覆盖
``DATABASE_URL``）。临时库里可能没有 job_postings 数据，"非法集合为空"
依然成立、不会假失败；真正的发现能力来自"每次有人写进非法 track 就红"。
"""

from __future__ import annotations

from app.core.target_roles import TARGET_ROLES
from app.db.base import SessionLocal
from app.models.job_posting import JobPosting
from app.models.task import Task

# 当前生效的赛道集合（career_mode 的 long_term_transition 模式以此为范围）。
# 变更赛道定义时必须同步改这里 —— 这是**有意的摩擦**：赛道集合是战略决策，
# 不该被顺手改掉。
EXPECTED_TRACK_KEYS = {"llm", "vlm", "ai-algo", "embodied"}


def test_target_roles_are_the_expected_four():
    """哨兵：赛道集合本身是预期的四条（否则下面的护栏永不命中）。"""
    keys = {r.key for r in TARGET_ROLES}
    assert keys == EXPECTED_TRACK_KEYS, (
        f"TARGET_ROLES 集合变了：{sorted(keys)} != {sorted(EXPECTED_TRACK_KEYS)}。"
        "若是有意变更，请同步本文件顶部注释与该常量。"
    )


def test_no_job_posting_track_outside_target_roles():
    """岗位的 track（非空）必须都属于 TARGET_ROLES。"""
    valid = {r.key for r in TARGET_ROLES}
    db = SessionLocal()
    try:
        rows = db.query(JobPosting).all()
        bad = [(p.id, p.company, p.track) for p in rows if p.track and p.track not in valid]
    finally:
        db.close()
    assert bad == [], (
        f"以下岗位的 track 不在 TARGET_ROLES（{sorted(valid)}）：{bad}。"
        "要么把 track 改成既有赛道，要么正式新增赛道（需同步 EXPECTED_TRACK_KEYS）。"
    )


def test_no_task_track_outside_target_roles():
    """任务的 track_key（非空）必须都属于 TARGET_ROLES —— 漂移任务的根因。"""
    valid = {r.key for r in TARGET_ROLES}
    db = SessionLocal()
    try:
        rows = db.query(Task).all()
        bad = [(t.id, t.title, t.track_key) for t in rows if t.track_key and t.track_key not in valid]
    finally:
        db.close()
    assert bad == [], (
        f"以下任务的 track_key 不在 TARGET_ROLES（{sorted(valid)}）：{bad}。"
        "这类任务会在按赛道过滤的视图里凭空消失。"
    )
