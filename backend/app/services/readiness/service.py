"""就绪度服务：**岗位对齐**的匹配计算唯一实现。

为什么要抽出来（Phase 3）：
    ``/api/job-hunt``（求职看板）与 ``/api/transition/dashboard``（统一落地页）
    都要回答同一个问题 ——「离目标岗位还差多少」。这段计算原本内联在
    ``api/job_hunt.py`` 里；落地页要用同一组数字时，若再抄一遍就会出现
    两个真相：同一天的匹配度在两页上不一样，用户无从判断哪个可信。

    这正是本项目反复出现的那类缺陷（见 CODEX_MODULAR_DESIGN_STANDARD §4.2
    「一条业务规则只能有一个权威实现」）。因此把它收成一个服务模块，
    两个路由都调用它，并由 ``tests/test_transition_dashboard.py``
    断言两处输出逐字段相同。

双轨口径（v3.2，见 docs/项目梳理与迭代指导-2026-09-21.md 裁决②）：
    - ``match_pct``  = 推进度：向 required_level 线性推进的百分比
    - ``strict_pct`` = 硬性达标率：level >= required_level 的技能占比

    两者必须并列展示，否则 67% 的推进度会被误读成"已达标"（真实达标仅 23%）。
    严格达标率与七维风险雷达同源（``core/risk.track_strict_pct``），
    llm 67%/23%（3/13）是回归锚点。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.risk import track_strict_pct
from app.core.target_roles import TARGET_ROLES, TargetRole
from app.models.skill import Skill


@dataclass(frozen=True)
class SkillMatch:
    """一项岗位要求技能的对齐情况。"""

    name: str
    level: int
    required: int
    gap: int
    missing: bool     # 技能表里根本没有这一项（≠ 有但等级为 0）


@dataclass(frozen=True)
class RoleReadiness:
    """一条赛道的就绪度快照。"""

    key: str
    name: str
    priority: str
    salary_range: str
    note: str
    frozen: bool
    match_pct: int
    strict_pct: int
    qualified_count: int
    required_count: int
    skills: list[SkillMatch] = field(default_factory=list)

    @property
    def skill_count(self) -> int:
        """该赛道硬性要求技能数（= 雷达轴数）。"""
        return len(self.skills)

    @property
    def gap_count(self) -> int:
        """其中仍存在缺口（gap>0）的技能数。"""
        return sum(1 for s in self.skills if s.gap > 0)

    def to_dict(self) -> dict:
        """``/api/job-hunt`` 的 ``target_roles[i]`` 形状。

        键名与历史输出逐字一致 —— 前端 ``jobHuntService`` 的 DTO 与
        ``test_job_hunt_caliber`` 都按这些键断言，改名会同时打破两处。
        """
        return {
            "key": self.key,
            "name": self.name,
            "priority": self.priority,
            "salary_range": self.salary_range,
            "note": self.note,
            "frozen": self.frozen,
            "match_pct": self.match_pct,
            "strict_pct": self.strict_pct,
            "qualified_count": self.qualified_count,
            "required_count": self.required_count,
            "skills": [
                {
                    "name": m.name,
                    "level": m.level,
                    "required": m.required,
                    "gap": m.gap,
                    "missing": m.missing,
                }
                for m in self.skills
            ],
        }


def load_skill_levels(db: Session) -> dict[str, int]:
    """库里的技能等级，键为**小写规范名**（与 track_strict_pct 的约定一致）。"""

    return {s.name.lower(): s.level for s in db.query(Skill).all()}


def role_readiness(role: TargetRole, skill_levels: dict[str, int]) -> RoleReadiness:
    """计算一条赛道的匹配情况。

    ``skill_levels`` 的键必须是小写技能名；缺失即视为等级 0 且 ``missing=True``。
    """

    matches: list[SkillMatch] = []
    for name in role.required_skills:
        level = skill_levels.get(name.lower())
        matches.append(
            SkillMatch(
                name=name,
                level=level if level is not None else 0,
                required=role.required_level,
                gap=max(role.required_level - (level if level is not None else 0), 0),
                missing=level is None,
            )
        )

    need = sum(m.required for m in matches)
    have = sum(min(m.level, m.required) for m in matches)
    strict_pct, qualified_count, required_count = track_strict_pct(
        role.required_skills, role.required_level, skill_levels
    )

    return RoleReadiness(
        key=role.key,
        name=role.name,
        priority=role.priority,
        salary_range=role.salary_range,
        note=role.note,
        frozen=role.frozen,
        match_pct=round(have / need * 100) if need else 0,
        strict_pct=strict_pct,
        qualified_count=qualified_count,
        required_count=required_count,
        skills=matches,
    )


def all_roles_readiness(skill_levels: dict[str, int]) -> list[RoleReadiness]:
    """全部赛道（TARGET_ROLES 原顺序）的就绪度。"""

    return [role_readiness(role, skill_levels) for role in TARGET_ROLES]


def primary_role() -> TargetRole | None:
    """主攻赛道（``priority == "主攻"``）。

    单点定义，供就绪度、风险雷达与落地页共用 —— 原先这段 ``next(...)``
    在 ``api/plan.py`` 与 ``api/risk.py`` 各写了一遍。
    """

    return next((r for r in TARGET_ROLES if r.priority == "主攻"), None)


def primary_readiness(readiness: list[RoleReadiness]) -> RoleReadiness | None:
    """从就绪度列表里挑主攻赛道；没有主攻则退回第一个未冻结赛道。"""

    for r in readiness:
        if r.priority == "主攻":
            return r
    for r in readiness:
        if not r.frozen:
            return r
    return readiness[0] if readiness else None
