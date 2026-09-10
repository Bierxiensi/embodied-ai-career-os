"""每日产出模型（DayArtifact）—— 计划里的「四件套」。

计划 §十 规定每天结束必须留下 4 样东西：

    ① 一段代码（code）
    ② 一页技术笔记（note）
    ③ 至少 5 道面试题（questions）
    ④ Git commit（commit）

这是把平台从「展示」变「学习」的核心机制：
    现在 Task.status 的 todo/doing/done 是人为切换的，没有客观标准，
    所以"完成"没有约束力；四件套是可核验的。

P0 范围：手工勾选 + 手工链接（本表 + 一个 POST 接口）。
P2 范围：自动核验 —— questions 可由题库当日新增条数自动判定，
        commit 可由 GitHub API 按日期自动归集，code 可由 commit diff 佐证。
        自动核验落地后 auto_verified 字段才真正被写入。
P2 之后：Skill 晋级改为 evidence-gated —— L1 需 note、L2 需 code+commit、
        L3 需 Experiment、L4 需对比实验 + 复现报告。
        届时本表就是技能等级的唯一证据来源。

为什么 P0 就要建表而不是先复用 LearningLog：
    LearningLog 是"一条自由文本 + 一个可选链接"，表达不了"今天该产出 4 类、
    哪几类齐了"。要在 P0 回答"今天做完没有"，必须有按 kind 分类的产出记录。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 四件套类型（前端勾选项与后端统计共用同一份字面量）
ARTIFACT_KIND_CODE = "code"
ARTIFACT_KIND_NOTE = "note"
ARTIFACT_KIND_QUESTIONS = "questions"
ARTIFACT_KIND_COMMIT = "commit"

ARTIFACT_KINDS: list[str] = [
    ARTIFACT_KIND_CODE,
    ARTIFACT_KIND_NOTE,
    ARTIFACT_KIND_QUESTIONS,
    ARTIFACT_KIND_COMMIT,
]

# 计划 §十 要求"至少 5 道面试题"
QUESTIONS_MIN_PER_DAY = 5


class DayArtifact(Base):
    """一条每日产出。归属某一天课程 + 某一类产出。"""

    __tablename__ = "day_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 归属课程日（外键）。注意：P0 阶段"今天是 Day N"由日历推导，
    # 落后时产出仍记在"你应该在做的那一天"上，P1 引入 DayProgress 后再解耦。
    plan_day_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("plan_days.id", ondelete="CASCADE"), nullable=False
    )

    # 产出类型：code / note / questions / commit
    kind: Mapped[str] = mapped_column(String(20), nullable=False)

    # 标题（如 "rope.py" / "docs/rope.md" / "第 3 天 5 道题"）
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 链接（GitHub 文件 / commit / 笔记路径），P2 由 GitHub 同步自动填充
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 结构化补充（questions 类可存题目清单，commit 类可存 sha / 仓库名）
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 是否由系统自动核验（P0 恒为 False；P2 起 commit / questions 不再只靠手工）
    auto_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", nullable=False
    )

    # 备注（为什么今天没交齐 / 补课说明）
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
