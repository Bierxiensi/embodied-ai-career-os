"""在职转型 / 学业的关键事实与节点（单一真源）。

为什么单独一个模块：
    "答辩哪天截止""导师联系窗口什么时候关""我现在在哪儿上班"这三件事
    会被三个地方同时用到 —— 七维风险雷达（``core/risk.py``）、
    统一落地页（``services/transition/service.py``）、以及笔试/笔试倒计时类文案。
    先前它们只以字面量散落在 ``core/risk.py`` 与前端文案里，改一次要全局搜。
    按本项目"一条规则一个权威实现"的约定（CODEX_MODULAR_DESIGN_STANDARD §4.2），
    全部收进这里；``core/risk.py`` 改为从这里导入（对外名字保持不变，
    既有 ``from app.core.risk import DEFENSE_DEADLINE`` 写法继续可用）。

⚠️ 这里的时间都是**硬事实**（学校 / 公司给定的日期），不是目标值。
   它们过期后必须由用户更新 —— 所以集中一处、并在 /api/transition/dashboard
   输出 ``days_left`` 让"还有几天"始终可见，避免日期悄悄过期没人发现。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# ══════════════════════════════════════════════════════════════════════════════
# 学业：硕士答辩（北航非全日制，延毕至 2026-12 答辩）
# ══════════════════════════════════════════════════════════════════════════════

DEFENSE_DEADLINE = date(2026, 12, 31)      # 答辩硬截止
DEFENSE_LABEL = "硕士答辩（北航非全）"

# ══════════════════════════════════════════════════════════════════════════════
# 学业：博士申请
# ══════════════════════════════════════════════════════════════════════════════

# 导师联系窗口关闭日：晚于这天再联系导师，当年入学基本来不及
PHD_CONTACT_WINDOW = date(2026, 11, 1)

# 申请季是一个**区间**而不是一天，因此只作为展示标签；
# 真正驱动紧迫感的是上面的 PHD_CONTACT_WINDOW。
PHD_APPLICATION_SEASON_LABEL = "2026 秋 – 2027 春"
PHD_WINDOW_LABEL = "导师联系窗口"

# ══════════════════════════════════════════════════════════════════════════════
# 在职：当前工作与在职转型窗口
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Employment:
    """当前在职事实。

    刻意只存**月份标签**而不是日期：入离职在简历与合同里都是月粒度，
    编一个具体的日子（如 1 月 1 日）会算出"已入职 264 天"这种伪精度。
    """

    company: str
    role: str
    focus: str
    since_label: str          # 入职月份，如 "2026.01"
    end_label: str | None     # 离职月份；None = 仍在职
    status_label: str         # 展示用状态
    note: str


EMPLOYMENT = Employment(
    company="北京东鉴科技",
    role="算法工程师（Agent 应用方向）",
    focus="文档智能 / 招投标 Agent",
    since_label="2026.01",
    end_label=None,           # 已确认留任，无离职计划
    status_label="在职",
    note="公司真实业务 = 文档模型后训练，与主攻方向（Post-Training）同构，故选择留任并在职转型",
)

# 在职转型窗口：这个区间内完成从 Agent 应用向 Post-Training 的岗位内迁移
TRANSITION_WINDOW_START = "2026.09"
TRANSITION_WINDOW_END = "2027.03"

# 与 risk.py 的 _COMPANY_REASON 同源渲染，避免两处各写一遍日期
COMPANY_REASON = (
    f"已确认留任，在职转型窗口 {TRANSITION_WINDOW_START}–{TRANSITION_WINDOW_END}"
)


def days_until(target: date, today: date | None = None) -> int:
    """距目标日期还有几天（负数 = 已过期）。"""

    return (target - (today or date.today())).days


@dataclass(frozen=True)
class Milestone:
    """一个带截止日的关键节点。"""

    key: str
    label: str
    deadline: date
    note: str


def key_milestones() -> list[Milestone]:
    """按截止日升序的关键节点（落地页「职业进度」区的节点条）。"""

    return [
        Milestone(
            key="phd_contact_window",
            label=PHD_WINDOW_LABEL,
            deadline=PHD_CONTACT_WINDOW,
            note="晚于这天再联系导师，当年入学基本来不及",
        ),
        Milestone(
            key="defense",
            label=DEFENSE_LABEL,
            deadline=DEFENSE_DEADLINE,
            note="学位论文答辩硬截止；风险雷达的 academic 维度取此日期",
        ),
    ]
