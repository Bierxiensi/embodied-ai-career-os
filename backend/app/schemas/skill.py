"""Skill Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SkillOut(BaseModel):
    """Skill 响应模型。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None = None
    level: int = Field(ge=0, le=5)
    target_level: int = Field(ge=0, le=5)
    evidence: list[str] = []
    evidence_gate: int | None = None  # P2：从真实证据推导的最高可信等级（0-4）

    # Phase 3：六域归属（llm_foundation / finetune_alignment / inference_engineering /
    # multimodal / engineering_delivery / research_foundation）。
    #
    # ⚠️ 它**不是** skills 表的列 —— 真源是 core/skill_profile.py 的 SkillProfile.domain。
    # 路由用技能名回查补上这个字段（见 api/skills.py），因此这里默认 None：
    # None 表示"不在六域内"（当前为 7 项冻结 / 历史旁证技能），
    # 与"路由忘了补字段"无法区分，所以路由侧由测试断言总数守恒。
    domain: str | None = None
    domain_label: str | None = None

    @field_validator("evidence", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        """数据库 JSON 字段可能为 None，统一转为空列表。"""

        return v or []


class SkillPrereqOut(BaseModel):
    """一条先修及其达成状态。"""

    name: str
    level: int | None = None
    met: bool
    note: str | None = None


class SkillDomainGap(BaseModel):
    """域内一项待补技能（含未满足的先修，用于回答「该先学哪个」）。"""

    name: str
    level: int
    target_level: int
    gap: int
    # 先修清单；met=False 表示该先修尚未达到 PREREQ_SATISFIED_LEVEL
    prerequisites: list[SkillPrereqOut]


class SkillDomainOut(BaseModel):
    """六域中的一域（Phase 3 / R2 域聚合雷达的一根轴）。"""

    key: str
    label: str
    skill_count: int
    # 域内技能等级均值 / 目标等级均值（保留 1 位小数）。
    # 雷达图直接用这两个值当轴长：用均值而不是"缺口计数"，
    # 是因为均值能同时表达"这层投入够不够"与"离目标多远"。
    current_avg: float
    target_avg: float
    gap_avg: float
    # 域内仍有缺口的技能，按 gap 降序（供卡片列出"最该补的几项"）
    gap_skills: list[SkillDomainGap]


class SkillDomainOverview(BaseModel):
    """GET /api/skills/domains 的响应。"""

    domains: list[SkillDomainOut]
    # 六域覆盖了多少技能、多少不在域内（后者是冻结 / 历史旁证区）
    mapped_count: int
    unmapped_count: int
    unmapped_names: list[str]
    prereq_satisfied_level: int


class SkillGraphNode(BaseModel):
    """依赖图节点 = 一项技能 + 它的域 / 等级。"""

    name: str
    domain: str | None = None
    domain_label: str | None = None
    level: int | None = None
    target_level: int | None = None
    frozen: bool = False


class SkillGraphEdge(BaseModel):
    """依赖图有向边：先修 -> 后继。"""

    prerequisite: str
    dependent: str
    note: str | None = None


class SkillGraphOut(BaseModel):
    """GET /api/skills/graph 的响应。"""

    nodes: list[SkillGraphNode]
    edges: list[SkillGraphEdge]
    prereq_satisfied_level: int


class SkillPatch(BaseModel):
    """Skill 部分更新请求。

    Day6 仅开放 level 与 evidence 更新（name/category/target_level 不动，
    避免误改目标架构）。未来 Reviewer Agent 通过此接口回写等级。
    """

    level: int | None = Field(default=None, ge=0, le=5)
    evidence: list[str] | None = None
