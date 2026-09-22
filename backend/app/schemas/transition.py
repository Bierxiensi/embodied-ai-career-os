"""Career Transition Dashboard 的响应契约（Phase 3）。

页面：``frontend/src/app/today/page.tsx`` —— 平台的统一落地页。
它把原先散在多个页面的五件事收口到一屏：

    1. 职业进度（模式 + 各赛道双轨就绪度 + 关键节点倒计时）
    2. 当前工作（在职事实 + 在职转型窗口）
    3. 学术与博士（硕士答辩倒计时 + 博士申请进度）
    4. ROI 任务（来自 ``/api/plan/today`` 的 ``roi_ranked_tasks``，不在本契约内）
    5. 风险雷达（来自 ``/api/plan/today`` 的 ``risk``，不在本契约内）

为什么后两区不放进这个契约：
    它们已由 ``TODAY`` 响应提供，且与"今天"强相关（当日任务排序、当日风险）。
    本契约只负责**不随日期变化的那部分事实**（进度 / 在职 / 学业），
    两者在页面层并排渲染即可 —— 合并进一个端点会让 /api/plan/today
    承担职业与学业职责，违反模块边界（CODEX_MODULAR_DESIGN_STANDARD §1）。

口径纪律：
    就绪度字段（``match_pct`` / ``strict_pct`` / ``qualified_count`` /
    ``required_count``）**必须**与 ``/api/job-hunt`` 逐字相同 ——
    两者都取自 ``services/readiness``，并由测试断言相等。
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.career_mode import CareerModeOut


class TrackProgressOut(BaseModel):
    """一条赛道的进度摘要（比 /api/job-hunt 的 target_roles 更薄）。

    明细技能（``skills``）不在本契约里：落地页只需要"哪条赛道差多少"，
    要看到逐项技能应去 /jobs 页 —— 同一份数据在两页各画一遍是重复建设。
    """

    key: str
    name: str
    priority: str
    frozen: bool
    # 推进度：[0, 100]，向岗位要求等级线性推进的百分比
    match_pct: int
    # 硬性达标率：[0, 100]，level >= required 的技能占比（与 JobsBoard 同源）
    strict_pct: int
    qualified_count: int
    required_count: int
    # 该赛道硬性要求技能数 / 其中仍有缺口的技能数
    skill_count: int
    gap_count: int


class MilestoneOut(BaseModel):
    """一个带截止日的关键节点。"""

    key: str
    label: str
    deadline: date
    days_left: int          # 负数 = 已过期
    status: str             # overdue / urgent / soon / ok
    note: str


class CareerProgressOut(BaseModel):
    """第 1 区：职业进度。"""

    primary_track_key: str | None = None
    tracks: list[TrackProgressOut] = Field(default_factory=list)
    milestones: list[MilestoneOut] = Field(default_factory=list)


class PositionOut(BaseModel):
    """第 2 区：当前工作。"""

    company: str
    role: str
    focus: str
    since_label: str            # 入职月份，如 "2026.01"
    end_label: str | None = None  # 离职月份；None = 仍在职
    status_label: str
    note: str
    transition_window_start: str
    transition_window_end: str
    transition_window_label: str


class DegreeOut(BaseModel):
    """第 3 区（上半）：硕士答辩。"""

    label: str
    deadline: date
    days_left: int
    status: str
    note: str


class AdvisorBriefOut(BaseModel):
    """导师摘要（落地页只显示 Top N，明细去 /phd 页）。"""

    id: int
    name: str
    institution: str | None = None
    tier: str | None = None
    contacted: bool = False
    # 六维匹配置信度缓存（未计算过时为 None）
    match_overall: int | None = None
    match_grade: str | None = None
    match_overall_max: int | None = None


class NearestDeadlineOut(BaseModel):
    """最近的博士申请截止日（院校 / 日期 / 剩余天数）。"""

    institution: str
    deadline: date
    days_left: int


class PhDProgressOut(BaseModel):
    """第 3 区（下半）：博士申请进度。"""

    season_label: str
    window_label: str
    window_deadline: date
    window_days_left: int
    window_status: str
    target_count: int
    advisor_count: int
    contacted_count: int
    matched_count: int
    nearest_deadline: NearestDeadlineOut | None = None
    top_advisors: list[AdvisorBriefOut] = Field(default_factory=list)


class AcademicOut(BaseModel):
    """第 3 区：学术（答辩 + 博士）。"""

    degree: DegreeOut
    phd: PhDProgressOut


class TransitionDashboard(BaseModel):
    """``GET /api/transition/dashboard`` 的 data。"""

    # 计算基准日（服务端日期），便于前端显示"截至 X 日"
    as_of: date
    mode: CareerModeOut
    career_progress: CareerProgressOut
    position: PositionOut
    academic: AcademicOut
