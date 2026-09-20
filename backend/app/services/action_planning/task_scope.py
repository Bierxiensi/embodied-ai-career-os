"""任务赛道口径：由当前 CareerMode 决定"哪些任务进入默认视图"。

================================================================================
这个模块存在的唯一理由：赛道过滤只能有一个权威实现
================================================================================
在此之前，「排除冻结赛道任务」被写在 ``api/job_hunt.py`` 的路由函数里
（内联的 ``frozen_keys`` + ``or_(...)`` 过滤）。一旦 ``/api/plan/today`` 也要遵守
同一口径，在第二个路由里复制一段就是**两份真相** —— 改 ``target_roles.py`` 或改
模式策略时必有一处忘记同步，两个页面的数字从此对不上。
（docs/CODEX_MODULAR_DESIGN_STANDARD.md §4.2：一条业务规则必须只有一个权威实现。）

因此本模块是唯一入口：
- :func:`resolve_task_scope` —— 解析口径（读当前 CareerMode）
- :func:`select_tasks`       —— 执行筛选（分类 + 计数，同源生成）

路由只负责"调用 + 序列化"，前端只负责"展示结果"，任何一处都不再自行判断
``track_key``。

================================================================================
业务规则（docs/PRD_CAREER_OS_MODES.md §5 F5）
================================================================================
1. **只排除冻结赛道。** 排除集由当前 CareerMode 的 ``frozen_track_keys`` 决定；
   ``active_track_keys`` 一并返回，用于向用户解释"本阶段在推动什么"。
2. **无赛道的任务保留并标记。** ``track_key IS NULL`` 是历史 / 手写任务
   （migrations/0008 回填赛道之前的数据），PRD F5.4 要求它们继续显示但标记
   「未归类」。
3. **长期模式不施加赛道约束。** ``long_term_transition`` 的
   ``active_track_keys`` / ``frozen_track_keys`` 当前均为空 —— PRD §4.2 只固定了
   求职模式的赛道策略，本期不替长期模式发明策略。空冻结集 = 不排除任何任务，
   并以 ``scope_reason`` 说明原因，免得"展示全部"看起来像口径失效。
4. **只读，绝不写。** 本模块只构造查询与分类，不修改任何任务的字段或存在性。
   排除 ≠ 删除：被排除的任务仍完整留在库里，且会随响应一并返回（``frozen_items``），
   供用户查看 —— PRD F5.3「隐藏不等于删除」。

================================================================================
为什么"生效赛道"是排除制，而不是包含制白名单
================================================================================
``active_track_keys`` 描述"本阶段推动哪些赛道"，但它**不能**当作包含制白名单：
某条任务的 track_key 一旦不在当前模式的声明范围内（未来新增赛道、或配置漂移），
白名单制就会把它**静默隐藏** —— 直接违反 PRD F5.3「隐藏不等于删除」，也违反
CODEBUDDY_IMPLEMENTATION_CONSTRAINTS §2.3「未归类历史任务保留可见且标记，不得
静默丢弃」。

所以判定写死为：**只有明确冻结的赛道被排除，其余一律保留**。
``active_track_keys`` 只用于解释口径，不承担过滤职责。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.orm import Query, Session

from app.models.task import Task
from app.services.career_mode.service import get_current_mode


class TaskTrackScope(StrEnum):
    """一条任务相对当前阶段的归类。

    三个取值覆盖全部可能，因此调用方不需要再处理"其他情况"分支
    （``classify`` 是全函数）。
    """

    #: 已归类且未被冻结 —— 进入默认视图
    ACTIVE = "active"
    #: 冻结赛道 —— 不进默认视图，但被计数、可查看
    FROZEN = "frozen"
    #: 无赛道的历史 / 手写任务 —— 进入默认视图并标记（PRD F5.4）
    UNCLASSIFIED = "unclassified"


# 口径原因文案集中定义：措辞只在这里维护，路由层不再各写一份。
_UNSCOPED_REASON_TEMPLATE = (
    "{mode_name}暂未限制赛道：默认展示全部任务"
    "（该阶段尚未定义冻结赛道，不排除任何任务）。"
)
_SCOPED_REASON_TEMPLATE = (
    "{mode_name}：只统计生效赛道（{active}）的任务；"
    "冻结赛道（{frozen}）不计入默认统计与今日推荐，"
    "任务记录本身保留，可查看已排除项。"
)
#: 生效赛道声明为空时的占位说明（当前模式未声明，而不是"没有赛道"）
_UNDECLARED_KEYS_LABEL = "未声明"


@dataclass(frozen=True)
class TaskScope:
    """当前阶段的任务赛道口径（不可变值对象）。

    ``is_track_scoped`` 与 ``frozen_track_keys`` 都由同一个冻结集合派生，
    因此不可能互相矛盾 —— 不存在"标记为已限缩但排除集为空"的中间状态。
    """

    mode_key: str
    mode_name: str
    #: 本阶段在推动的赛道 key（用于解释口径，不参与过滤，理由见模块 docstring）
    active_track_keys: tuple[str, ...]
    #: 本阶段冻结的赛道 key（唯一的排除依据）
    frozen_track_keys: tuple[str, ...]
    #: 本口径是否实际限缩了任务范围（= 是否存在冻结赛道）
    is_track_scoped: bool
    scope_reason: str

    def classify(self, track_key: str | None) -> TaskTrackScope:
        """把一条任务的 ``track_key`` 归类。

        纯函数：不读库、不读环境，相同输入永远得到相同输出，因此可直接单测
        （见 tests/test_task_scope_service.py）。
        """

        if track_key is None or not str(track_key).strip():
            return TaskTrackScope.UNCLASSIFIED
        if track_key in self.frozen_track_keys:
            return TaskTrackScope.FROZEN
        return TaskTrackScope.ACTIVE

    def includes(self, track_key: str | None) -> bool:
        """该任务是否进入默认视图（排除制：只有冻结赛道被排除）。"""

        return self.classify(track_key) is not TaskTrackScope.FROZEN


@dataclass(frozen=True)
class ScopedTasks:
    """一次口径应用的完整结果。

    ``included`` / ``frozen_items`` / ``unclassified`` 由同一遍遍历产出，因此
    计数与列表**不可能不同源** —— 项目里曾出现"summary 报 16 项、列表只有 12 项"
    的截断 bug（见 MEMORY.md），这里用同源结构从根上排掉这类问题。
    """

    scope: TaskScope
    included: tuple[Task, ...]
    frozen_items: tuple[Task, ...]
    unclassified: int

    @property
    def frozen_excluded(self) -> int:
        """被口径排除的任务数（= 冻结赛道任务数）。"""

        return len(self.frozen_items)

    def classification_of(self, task: Task) -> TaskTrackScope:
        """取某条任务的归类。

        刻意转发给 ``scope.classify`` 而不是重新判断一次 —— 否则"列表用的规则"
        与"标注用的规则"就有了两个实现点，正是本模块要消灭的东西。
        """

        return self.scope.classify(task.track_key)


def resolve_task_scope(db: Session) -> TaskScope:
    """解析当前 CareerMode 派生的任务口径。**唯一入口**。

    读的是 ``career_mode`` 模块的当前模式（该模块是"当前阶段"的唯一权威），
    因此"改模式 → 口径随之变化"是结构性保证，不靠调用方记得同步。
    """

    mode = get_current_mode(db)
    active = _normalize_track_keys(mode.active_track_keys)
    frozen = _normalize_track_keys(mode.frozen_track_keys)

    return TaskScope(
        mode_key=mode.key,
        mode_name=mode.name,
        active_track_keys=active,
        frozen_track_keys=frozen,
        is_track_scoped=bool(frozen),
        scope_reason=_build_scope_reason(mode.name, active, frozen),
    )


def select_tasks(candidates: Query, scope: TaskScope) -> ScopedTasks:
    """按口径筛选任务候选集。**唯一入口**。

    ``candidates`` 由调用方构造：求职看板传全量任务，今日施工单传"该课程日的
    任务"。本函数**只做赛道判定**，不追加任何其他业务条件 —— "属于第几天"与
    "属于哪条赛道"是两个正交轴，各自留在自己的模块里，不在这里混成一坨。
    """

    included: list[Task] = []
    frozen: list[Task] = []
    unclassified = 0

    for task in candidates.all():
        bucket = scope.classify(task.track_key)
        if bucket is TaskTrackScope.FROZEN:
            frozen.append(task)
            continue
        included.append(task)
        if bucket is TaskTrackScope.UNCLASSIFIED:
            unclassified += 1

    return ScopedTasks(
        scope=scope,
        included=tuple(included),
        frozen_items=tuple(frozen),
        unclassified=unclassified,
    )


# ============================================================
# 内部实现
# ============================================================


def _normalize_track_keys(raw: list | None) -> tuple[str, ...]:
    """把库里的 JSON 数组规范成去空、去重、保序的 key 元组。

    库里是 JSON 列，可能是 ``None``（老数据，或未 flush 的 ORM 实例上列默认值
    尚未生效 —— 见 MEMORY.md 的 Pydantic/ORM 坑），也可能混入空串。
    在这里规范一次，后面的判定就只需处理"干净的 key"这一种情形。
    """

    if not raw:
        return ()

    keys: list[str] = []
    for item in raw:
        key = str(item or "").strip()
        if key and key not in keys:
            keys.append(key)
    return tuple(keys)


def _build_scope_reason(
    mode_name: str, active: tuple[str, ...], frozen: tuple[str, ...]
) -> str:
    """生成给人看的口径说明（前端直接展示，不再自己拼措辞）。"""

    if not frozen:
        return _UNSCOPED_REASON_TEMPLATE.format(mode_name=mode_name)

    return _SCOPED_REASON_TEMPLATE.format(
        mode_name=mode_name,
        active="、".join(active) or _UNDECLARED_KEYS_LABEL,
        frozen="、".join(frozen),
    )
