"""职业阶段模式的预置定义（纯配置，无副作用）。

为什么单独一个文件：
    "有哪几种模式、默认是哪种、各模式推动/冻结哪些赛道"属于产品配置，
    必须与"怎么读写当前模式"（service.py）分开 —— 改配置不碰逻辑。
    本模块不导入 Session、不读写库、不依赖 FastAPI，可被种子流程、API 层与
    测试同时引用而不产生循环依赖。

赛道策略的唯一来源是 ``app/core/target_roles.py``：
    生效赛道 = 未冻结赛道（frozen=False）
    冻结赛道 = 已冻结赛道（frozen=True）
这里**不重新硬编码赛道清单**。否则 target_roles.py 一改（比如把具身解冻），
模式策略就与实际赛道配置脱节，同一件事出现两个说法
（docs/CODEX_MODULAR_DESIGN_STANDARD.md §4.2：一条业务规则只能有一个权威实现）。

同理，求职模式的期限直接取 target_roles.py 的 ``DEFAULT_OFFER_DEADLINE``，
不在这里抄一遍 2026-10-31。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.target_roles import DEFAULT_OFFER_DEADLINE, TARGET_ROLES

# 模式 key（稳定业务标识，前端与 mode_transitions 都按它引用）
JOB_HUNT_MODE_KEY = "job_hunt"
LONG_TERM_TRANSITION_MODE_KEY = "long_term_transition"

# 首期默认模式：求职冲刺（PRD §5 F1.1）
DEFAULT_MODE_KEY = JOB_HUNT_MODE_KEY

# 首次激活（建库时把默认模式置为当前）的留痕说明。
# 它不是"用户切换"，但同样进历史 —— 否则回溯时会出现"从无到有"的断点。
INITIAL_ACTIVATION_NOTE = "系统初始化：默认进入求职冲刺模式"

# 求职模式的赛道策略：直接从赛道配置派生，见模块 docstring。
_ACTIVE_TRACK_KEYS: tuple[str, ...] = tuple(
    role.key for role in TARGET_ROLES if not role.frozen
)
_FROZEN_TRACK_KEYS: tuple[str, ...] = tuple(
    role.key for role in TARGET_ROLES if role.frozen
)


@dataclass(frozen=True)
class CareerModePreset:
    """一个阶段的预置定义。

    注意 ``frozen=True``（dataclass 语义）指"这个配置对象不可变"，
    与"冻结赛道"（frozen_track_keys）没有关系，不要混读。
    """

    key: str
    name: str
    objective: str
    # ISO 日期字符串；None = 该阶段没有硬截止
    deadline: str | None
    active_track_keys: tuple[str, ...]
    frozen_track_keys: tuple[str, ...]


CAREER_MODE_PRESETS: tuple[CareerModePreset, ...] = (
    CareerModePreset(
        key=JOB_HUNT_MODE_KEY,
        name="求职冲刺模式",
        objective="在目标期限前获得符合条件的 Offer",
        deadline=DEFAULT_OFFER_DEADLINE,
        active_track_keys=_ACTIVE_TRACK_KEYS,
        frozen_track_keys=_FROZEN_TRACK_KEYS,
    ),
    CareerModePreset(
        key=LONG_TERM_TRANSITION_MODE_KEY,
        name="长期转型模式",
        objective="在公司内完成从 Agent 应用向 Post-Training / 具身智能的在职转型，并行推进博士申请",
        # 长期阶段按季度 / 学期 / 项目里程碑推进，没有硬性截止日期，
        # 前端据此显示为"长期"而不是"剩余 0 天"（PRD §4.1 规定节奏不同）。
        deadline=None,
        # v3.1（2026-09-20）：长期模式的赛道策略**首次定义**（此前为空壳）。
        # 生效赛道 = llm（Post-Training，与在职方向重合，主攻）
        #           + vlm（模型分支，卡位）
        #           + phd（长期研究目标；Phase 1 博士模块会建立独立六维匹配，本阶段只占位）。
        # 冻结赛道 = 空。原因有两条，都是硬约束：
        #   1. 长期转型期不施加赛道约束（PRD §4.2 + task_scope 排除制），所有历史 /
        #      手写任务仍可见；且 test_only_career_mode_switch_changes_the_range 硬性要求
        #      long_term 冻结集为空（冻结任务必须回到默认范围，否则该测试失败）。
        #   2. ai-algo / embodied 不在本阶段"主动推动列表"里，但仍在范围内可见，
        #      避免在职期误隐藏既有资产（SO101 / 推理工程等）。
        # 注意：phd 故意**不**进入 core/target_roles.py 的 TARGET_ROLES —— 它的就绪度是
        #       研究匹配（六维），不是技能匹配；提前进 TARGET_ROLES 会让 /api/job-hunt
        #       强行产出一张误导性的"博士申请 技能匹配度"卡片。Phase 1 博士模块落地后再正式建模。
        active_track_keys=("llm", "vlm", "phd"),
        frozen_track_keys=(),
    ),
)


def find_preset(mode_key: str) -> CareerModePreset | None:
    """按 key 找预置；未定义返回 None（由调用方决定是报错还是忽略）。"""

    return next((p for p in CAREER_MODE_PRESETS if p.key == mode_key), None)


def preset_order_index(mode_key: str) -> int:
    """模式在 UI 里的展示顺序；未在预置里定义的模式排到最后。"""

    for index, preset in enumerate(CAREER_MODE_PRESETS):
        if preset.key == mode_key:
            return index
    return len(CAREER_MODE_PRESETS)


def preset_keys() -> list[str]:
    """全部模式 key（用于错误提示与测试断言）。"""

    return [p.key for p in CAREER_MODE_PRESETS]
