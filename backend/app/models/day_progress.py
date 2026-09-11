"""执行进度记录（DayProgress）—— 计划与日历解耦的关键实体。

见 docs/platform-direction-30day.md §四 决策 1 与 §七 P1：
    PlanDay.seq = 1..30（课程脊梁，不可变）
    DayProgress.calendar_date（执行记录，可移动）

为什么单列一张表而不是给 plan_days 加 calendar_date：
    决策 1 的核心就是「Day N 不与日历日期绑死」。若把日期直接写进 plan_days，
    滑期时被迫改 plan_days，会牵连种子脚本的幂等匹配（按 seq 更新），
    也会让「计划内容」和「执行记录」两种性质混在一张表。
    这里每张 plan_days 行对应最多一条 day_progress（plan_day_id UNIQUE），
    记录你实际在哪天执行、状态如何、为什么偏离。

status 取值与语义：
    pending    未执行（默认）
    done       四件套齐全 / 明确标记完成
    compressed 压缩：本日验收降级速通，算「过」但留 deviation_note 说明砍了什么
    deferred   顺延：内容推到以后手动补；注意**不自动顺延后续天**
    skipped    放弃：本日内容不再投入（释放时间给更高优先赛道）

滑期约束（风险 3）：落后时**只提示、不自动顺延**。用户必须手动对每一个
「已错过」的日期选一个决策，且决策要落 deviation_note，强迫面对取舍。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 进度状态字面量（前端 / 决策按钮共用）
PROGRESS_PENDING = "pending"
PROGRESS_DONE = "done"
PROGRESS_COMPRESSED = "compressed"
PROGRESS_DEFERRED = "deferred"
PROGRESS_SKIPPED = "skipped"

PROGRESS_STATUSES: list[str] = [
    PROGRESS_PENDING,
    PROGRESS_DONE,
    PROGRESS_COMPRESSED,
    PROGRESS_DEFERRED,
    PROGRESS_SKIPPED,
]

# 算「通过」的两种状态（计入课程进度、不再算落后）
PROGRESS_PASSED: tuple[str, ...] = (PROGRESS_DONE, PROGRESS_COMPRESSED)


class DayProgress(Base):
    """某一天课程的执行记录。plan_day_id 唯一，一张计划日最多一条。"""

    __tablename__ = "day_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 归属课程日（外键，唯一 —— 一天只有一条进度记录，随 plan_days 级联删除）
    plan_day_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("plan_days.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # 实际执行日期（可移动）。done/compressed 时由接口写入当天；
    # deferred/skipped 留空（你并没有在这一天真正执行）。
    calendar_date: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 执行状态（见模块顶部常量说明）
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PROGRESS_PENDING
    )

    # 实际投入分钟数（可选，用于复盘计划 vs 实际的偏差）
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 偏离说明：压缩砍了什么 / 顺延推到哪 / 放弃为什么。滑期机制的硬性落点。
    deviation_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
