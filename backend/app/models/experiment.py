"""实验记录模型（Experiment）。

对应 docs/platform-direction-30day.md 决策 4：「实验记录是一等公民」。

计划里 Day 12（LoRA vs QLoRA）、Day 22（SFT/LoRA/QLoRA 四组对比）、
Day 23（Transformers vs vLLM benchmark）全部落这张表，而不是停在文档里。

设计要点：
- day_seq 不可变课程序号（与 plan_days.seq 对齐），plan_day_id 仅用于外键关联展示
- variants / metrics 用 JSON 存结构化表格数据，前端直接渲染成对比表
- skill_name 用于「技能晋级 evidence-gated」（P2-D）：一条 Experiment 即该技能 L3 证据
- kind ∈ finetune / benchmark / ablation，ablation 或多变体视为「对比实验」（L4 前置）
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# 实验类型
EXPERIMENT_KIND_FINETUNE = "finetune"
EXPERIMENT_KIND_BENCHMARK = "benchmark"
EXPERIMENT_KIND_ABLATION = "ablation"

EXPERIMENT_KINDS: list[str] = [
    EXPERIMENT_KIND_FINETUNE,
    EXPERIMENT_KIND_BENCHMARK,
    EXPERIMENT_KIND_ABLATION,
]


class Experiment(Base):
    """一条实验记录（多变体 + 多指标）。"""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联课程日（外键，可空：实验也可不在固定课程日内）
    plan_day_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("plan_days.id", ondelete="SET NULL"), nullable=True
    )

    # 课程序号 1..30（冗余存一份，便于不 join 直接展示 / 排序）
    day_seq: Mapped[int] = mapped_column(Integer, nullable=False)

    # 实验名（如 "LoRA vs QLoRA"）
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # 实验类型
    kind: Mapped[str] = mapped_column(String(30), default=EXPERIMENT_KIND_FINETUNE, nullable=False)

    # 关联技能名（evidence-gated 用，如 "LoRA/QLoRA"）
    skill_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 变体列表：[{name, trainable_params, gpu_mem, time, result, ...}]
    variants: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 指标列表：[{name, value, unit}]
    metrics: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 结论（自由文本）
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 关联产出 id（day_artifacts.id / 仓库链接等）
    artifact_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
