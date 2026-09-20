"""career_mode 用例层：模式物化、当前模式解析、模式切换、切换历史。

分层（docs/CODEX_MODULAR_DESIGN_STANDARD.md §2）：
    api/career_mode.py  →  本模块  →  models/career_mode.py
本模块是"当前模式"的**唯一写入口**，三条不变量都在这里兜住：

1. **恒有且仅有一个当前模式。**
   ``sync_career_modes`` 在"一个当前模式都没有"时自愈回默认模式；"至多一个"
   由数据库上的部分唯一索引（``ux_career_modes_current``）物理保证 —— 靠服务层
   自觉是不够的，读侧一旦遇到两行为真就会静默挑一条，页面与库里状态不一致
   却毫无提示。
2. **切换只写模式自身。**
   ``switch_mode`` 只改 ``career_modes.is_current`` 并追加一条 ``mode_transitions``，
   不触碰岗位 / 任务 / 投递 / 面试 / 技能的任何一张表。
3. **模式定义以 presets.py 为单一来源。**
   本模块把定义物化（materialize）到表里，与 ``skills`` ← ``core/skill_profile.py``
   是同一范式：配置是权威，表是副本。因此改 presets.py 或 target_roles.py 后
   重启后端（``init_db`` → ``sync_career_modes``）即可对齐，不需要手写 UPDATE。

本模块不导入 FastAPI、不抛 HTTPException —— HTTP 语义（状态码）由 API 层翻译，
这样切换规则可以在不启动 Web 服务的情况下单测。
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.career_mode import CareerMode, ModeTransition
from app.services.career_mode.presets import (
    CAREER_MODE_PRESETS,
    DEFAULT_MODE_KEY,
    INITIAL_ACTIVATION_NOTE,
    CareerModePreset,
    preset_keys,
    preset_order_index,
)


class UnknownCareerModeError(LookupError):
    """请求切换到一个未定义的模式。"""

    def __init__(self, mode_key: str) -> None:
        self.mode_key = mode_key
        self.available_keys = preset_keys()
        super().__init__(
            f"未知的模式：{mode_key}。可选：{'、'.join(self.available_keys)}"
        )


class ModeAlreadyCurrentError(ValueError):
    """当前已处于目标模式，无需切换。"""

    def __init__(self, mode_key: str) -> None:
        self.mode_key = mode_key
        super().__init__(f"当前已经是该模式（{mode_key}），未做任何变更")


# ============================================================
# 读
# ============================================================


def list_modes(db: Session) -> list[CareerMode]:
    """全部模式，按 presets.py 的声明顺序（即 UI 展示顺序）。"""

    rows = db.query(CareerMode).all()
    rows.sort(key=lambda row: (preset_order_index(row.key), row.id))
    return rows


def get_current_mode(db: Session) -> CareerMode:
    """当前生效模式。

    正常路径只读一次；只有当库里没有任何 ``is_current`` 标记时（例如手工清过
    表、或迁移先于种子执行）才按预置自愈补种，避免接口返回空让前端崩在渲染处。
    """

    current = _find_current_mode(db)
    if current is not None:
        return current

    for mode in sync_career_modes(db):
        if mode.is_current:
            return mode

    # sync_career_modes 结束必然存在一个当前模式；走到这里说明预置配置本身
    # 被改坏了（DEFAULT_MODE_KEY 不在 CAREER_MODE_PRESETS 里）。这是配置错误，
    # 不是用户输入错误，因此抛运行时异常（HTTP 500）而不是 4xx。
    raise RuntimeError(
        "没有可用的当前模式：请检查 app/services/career_mode/presets.py "
        f"中的 DEFAULT_MODE_KEY（当前为 {DEFAULT_MODE_KEY}）是否在 CAREER_MODE_PRESETS 中"
    )


def list_transitions(db: Session) -> list[ModeTransition]:
    """切换历史，最近的在前。

    按 ``transitioned_at`` 降序、``id`` 降序兜底：同一秒内连续切换时
    （测试里很常见）时间戳可能相同，用自增 id 保证顺序稳定。
    """

    return (
        db.query(ModeTransition)
        .order_by(
            ModeTransition.transitioned_at.desc(),
            ModeTransition.id.desc(),
        )
        .all()
    )


# ============================================================
# 写
# ============================================================


def sync_career_modes(db: Session) -> list[CareerMode]:
    """把预置模式物化到 career_modes（幂等，可重复调用）。

    行为，逐条对应一种"库与配置不一致"的情形：

    - 配置里有、库里没有 → 插入（首次启动 / 新增模式）
    - 库里已有 → 校正 name / objective / deadline / 赛道策略，使其与
      presets.py 一致。**不触碰 is_current** —— 否则用户切换后的选择会被
      下一次重启悄悄抹掉，而 PRD 要求"切换后刷新页面仍保持"。
    - 库里有、配置里没有 → 保留不动（宁可多一条也不静默删数据）
    - 一个当前模式都没有 → 把默认模式置为当前，并追加一条
      ``from_mode=None`` 的初始激活记录（只在真的没有当前模式时发生）
    """

    rows = {row.key: row for row in db.query(CareerMode).all()}

    for preset in CAREER_MODE_PRESETS:
        row = rows.get(preset.key)
        if row is None:
            rows[preset.key] = _insert_preset_row(db, preset)
        else:
            _align_row_with_preset(row, preset)

    # 新插入的行需要先落盘拿到 id，后续才谈得上被引用 / 被 UI 展示
    db.flush()

    if _find_current_mode(db) is None:
        # DEFAULT_MODE_KEY 必在预置中（依赖 CAREER_MODE_PRESETS 的定义），
        # 上面的循环保证了它一定在 rows 里。
        _activate_default_mode(db, rows[DEFAULT_MODE_KEY])

    db.commit()
    return list_modes(db)


def switch_mode(
    db: Session, mode_key: str, note: str | None = None
) -> tuple[CareerMode, ModeTransition]:
    """切换到 ``mode_key``，并留下一条切换记录。

    返回 ``(切换后的模式行, 本次切换记录)``。失败语义（由 API 层翻译成状态码）：

    - 未知模式 key → :class:`UnknownCareerModeError`
    - 当前已是该模式 → :class:`ModeAlreadyCurrentError`（不写历史，
      否则反复点同一个选项会刷出一串无意义的空切换记录）

    事务边界（一次 commit，全成或全不成）：
    清旧标记 → ``flush`` → 置新标记 → 追加历史记录。

    ``flush`` 是必需的：SQLAlchemy 的工作单元不保证多条 UPDATE 的落盘顺序，
    若"置新标记"先于"清旧标记"落盘，会瞬时出现两行 ``is_current`` 为真而撞上
    唯一索引，切换随机失败。
    """

    sync_career_modes(db)

    target = db.query(CareerMode).filter(CareerMode.key == mode_key).first()
    if target is None:
        raise UnknownCareerModeError(mode_key)

    current = _find_current_mode(db)
    if current is not None and current.key == target.key:
        raise ModeAlreadyCurrentError(mode_key)

    from_key = current.key if current is not None else None
    if current is not None:
        current.is_current = False
        db.flush()

    target.is_current = True
    transition = ModeTransition(
        from_mode=from_key,
        to_mode=target.key,
        transitioned_at=datetime.utcnow(),
        note=note,
    )
    db.add(transition)
    db.commit()

    db.refresh(target)
    db.refresh(transition)
    return target, transition


# ============================================================
# 内部实现
# ============================================================


def _find_current_mode(db: Session) -> CareerMode | None:
    """读当前模式行；无则返回 None。

    "至多一行"由 ux_career_modes_current 保证，所以这里的 .first() 不会
    在多个候选中做静默取舍。
    """

    return db.query(CareerMode).filter(CareerMode.is_current.is_(True)).first()


def _insert_preset_row(db: Session, preset: CareerModePreset) -> CareerMode:
    """按预置插入一行（不含 is_current，由当前模式判定单独处理）。"""

    row = CareerMode(
        key=preset.key,
        name=preset.name,
        objective=preset.objective,
        deadline=_parse_preset_deadline(preset.deadline),
        active_track_keys=list(preset.active_track_keys),
        frozen_track_keys=list(preset.frozen_track_keys),
        is_current=False,
    )
    db.add(row)
    return row


def _align_row_with_preset(row: CareerMode, preset: CareerModePreset) -> None:
    """把已有行校正成预置的样子（不含 is_current）。"""

    row.name = preset.name
    row.objective = preset.objective
    row.deadline = _parse_preset_deadline(preset.deadline)
    row.active_track_keys = list(preset.active_track_keys)
    row.frozen_track_keys = list(preset.frozen_track_keys)


def _activate_default_mode(db: Session, default_row: CareerMode) -> None:
    """把默认模式置为当前，并补一条初始激活记录（无来源模式）。"""

    default_row.is_current = True
    db.add(
        ModeTransition(
            from_mode=None,
            to_mode=default_row.key,
            transitioned_at=datetime.utcnow(),
            note=INITIAL_ACTIVATION_NOTE,
        )
    )


def _parse_preset_deadline(iso_date: str | None) -> date | None:
    """预置里的 ISO 日期字符串 → ``date``；None 表示该阶段无硬截止。"""

    if iso_date is None:
        return None
    return date.fromisoformat(iso_date)
