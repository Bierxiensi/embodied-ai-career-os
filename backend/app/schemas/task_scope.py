"""任务范围（Task Scope）响应契约。

``/api/job-hunt`` 与 ``/api/plan/today`` 共用同一个 ``task_scope`` 字段：把"这次
统计为什么不含某些任务"变成可读数据，而不是让前端或用户去猜
（docs/PRD_CAREER_OS_MODES.md §5 F5.3 / §7.2）。

两个模型分别对应两个层次：

- :class:`TaskScopeOut` —— 这次用了什么口径、排除/未归类各多少条（视图级）
- :class:`ScopedTaskRef` —— 被排除的**具体是哪几条**（条目级，PRD F5.3
  「隐藏不等于删除」要求可查看）。两个端点用同一个模型，因此"被排除项"的
  字段形状不会各自漂移。

分层说明：本模块只做"服务层值对象 → 响应模型"的**一层转换**，不含任何业务判断
（判定全在 ``services/action_planning/task_scope.py``）。之所以让 schemas 依赖
service 的纯 dataclass：这些 dataclass 是不可变值对象、无副作用，依赖它们不会
产生循环（service 不反向依赖 schemas），而把这段转换写在两个路由里才是真正的
重复。schema 依赖 ``app.models`` 的常量已有先例（schemas/resume.py 等）。
"""

from __future__ import annotations

from pydantic import BaseModel

from app.models.task import Task
from app.services.action_planning.task_scope import (
    ScopedTasks,
    TaskTrackScope,
)


class TaskScopeOut(BaseModel):
    """本次响应采用的赛道口径 + 透明度计数。

    ``scope_reason`` 是给人看的一句话；三个计数与 ``scope`` 中的声明集合同源，
    前端据此可以解释"总数为什么变小"，而不必自己推断规则。
    """

    #: 生效模式（前端据此确认口径来自哪个阶段）
    mode_key: str
    mode_name: str

    #: 本口径是否实际限缩了任务范围
    is_track_scoped: bool
    #: 本阶段推动的赛道 key
    active_track_keys: list[str]
    #: 本阶段冻结的赛道 key（= 实际被排除的赛道）
    frozen_track_keys: list[str]

    #: 口径说明（人话），前端直接展示
    scope_reason: str

    #: 纳入口径的任务数
    included: int
    #: 被排除的冻结赛道任务数
    frozen_excluded: int
    #: 其中「未归类」（track_key 为空）的任务数
    unclassified: int


class ScopedTaskRef(BaseModel):
    """一条被口径分类过的任务的最小识别信息。

    ``/api/job-hunt`` 与 ``/api/plan/today`` 都用它返回**被排除**的任务，
    目的是 PRD F5.3「隐藏不等于删除」：任务没被删、没被改，只是不进默认统计，
    用户仍能看见"被排除的是哪几条"。字段刻意只留识别所需的最小集 ——
    完整数据始终在任务表 / 任务接口里，不在这里复制一份会过期的副本。

    ``scope`` 由服务层给出（``active`` / ``frozen`` / ``unclassified``），
    前端只展示，不自行判断赛道。
    """

    id: int
    title: str
    track_key: str | None = None
    status: str
    scope: str


def to_task_scope_out(scoped: ScopedTasks) -> TaskScopeOut:
    """把服务层结果转成响应模型。

    计数直接取自 ``ScopedTasks`` 的同源字段，不重新遍历、不重新判断，
    因此响应里不可能出现"计数与列表对不上"。
    """

    scope = scoped.scope
    return TaskScopeOut(
        mode_key=scope.mode_key,
        mode_name=scope.mode_name,
        is_track_scoped=scope.is_track_scoped,
        active_track_keys=list(scope.active_track_keys),
        frozen_track_keys=list(scope.frozen_track_keys),
        scope_reason=scope.scope_reason,
        included=len(scoped.included),
        frozen_excluded=scoped.frozen_excluded,
        unclassified=scoped.unclassified,
    )


def to_scoped_task_ref(task: Task, classification: TaskTrackScope) -> ScopedTaskRef:
    """把任务 + 服务层给定归类转成最小识别信息。

    归类由调用方从服务层取（``ScopedTasks.classification_of`` / ``scope.classify``），
    **不在这里重判** —— 否则"列表用的规则"与"标注用的规则"就有了两个实现点。
    """

    return ScopedTaskRef(
        id=task.id,
        title=task.title,
        track_key=task.track_key,
        status=task.status,
        scope=classification.value,
    )

