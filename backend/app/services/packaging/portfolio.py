"""作品集组装（spec §2.3：作品集说话）。

13 节骨架复用 packaging 既有结构（``engine.README_SECTIONS``，plan_30d Day 24 的
13 节 README 骨架）；内容全部来自**已有证据**：

- ``skills.evidence_gate >= 1`` 的技能（能力证据索引）
- ``unit_items.is_verified`` 的测验（关键结果）
- ``experiments`` 实验记录（数据与实验 / 消融与对比 / 推理基准）
- 带 ``artifact_url`` 的学习日志（可复现性 / badcase 复盘）

组装只读事实库——不生成、不美化、不虚构（AI 可润色属后续 Proposal 通道，本期不做）。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.experiment import (
    EXPERIMENT_KIND_ABLATION,
    EXPERIMENT_KIND_BENCHMARK,
    Experiment,
)
from app.models.learning_log import LearningLog
from app.models.mastery import UnitItem
from app.models.skill import Skill
from app.services.packaging.engine import (
    README_SECTIONS,
    REQUIRED_SECTIONS,
    SECTION_HINTS,
)

# 13 节骨架：import 复用 packaging 既有 SECTION 常量（与 README 骨架同源，不另起名单）
SECTIONS: tuple[str, ...] = README_SECTIONS


def _fallback(section: str) -> str:
    """无实例时的结构文本。

    允许少量节暂无实例，但必须有结构（复用 packaging 的写作提示），
    不留空白——对应 engine 的「有提示的占位 >> 空标题」口径。
    """

    hint = SECTION_HINTS.get(section, "（待补）")
    if section in REQUIRED_SECTIONS:
        return f"⚠️ 必填 —— {hint}"
    return f"📝 待补：{hint}"


def build_portfolio(db: Session) -> dict:
    """从证据库只读组装 13 节作品集。

    Returns:
        ``{"sections": [{"name", "content"} × 13], "evidence_count": int,
        "ready_skills": [str]}``
    """

    ready = db.query(Skill).filter(Skill.evidence_gate >= 1).all()
    verified = db.query(UnitItem).filter_by(is_verified=True).all()
    experiments = db.query(Experiment).all()
    logs = [row for row in db.query(LearningLog).all() if row.artifact_url]

    # 各证据池 → 展示行（字段以模型为准：Experiment.name / UnitItem.body / LearningLog.content）
    exp_line = "；".join(f"{e.name}（{e.kind}）" for e in experiments)
    ablation_line = "；".join(
        e.name for e in experiments if e.kind == EXPERIMENT_KIND_ABLATION
    )
    benchmark_line = "；".join(
        e.name for e in experiments if e.kind == EXPERIMENT_KIND_BENCHMARK
    )
    verified_line = "；".join(i.body[:40] for i in verified[:10])
    log_line = "；".join(row.content[:60] for row in logs[:5])
    artifact_line = "；".join(row.artifact_url for row in logs[:10])
    skill_line = "；".join(f"{s.name}=L{s.evidence_gate}" for s in ready)

    lines: dict[str, str] = {
        # 项目概览 + 背景与问题
        "Motivation": (
            "Mini Post-Training Lab 作品集（由证据库自动组装）。"
            "从「学过」到「考得出、拿得出」：每条能力主张都可回溯到证据。"
        ),
        # 目标与验收 + 技术方案
        "Architecture": (
            "目标：01_sft / 02_lora / 03_dpo 三模块各有 L2+ 证据。"
            "方案：SFT → LoRA/QLoRA → DPO/GRPO；评测与 badcase 闭环。"
        ),
        # 可复现性（带 artifact_url 的产出链接）+ 工程化
        "Environment": (
            f"可复跑脚本与依赖锁定随 Lab 模块仓库提交。已有产出：{artifact_line}"
            if artifact_line
            else "可复跑脚本与依赖锁定随 Lab 模块仓库提交。（证据链接待补充）"
        ),
        "Dataset": _fallback("Dataset"),
        # 数据与实验
        "Training": exp_line or _fallback("Training"),
        # 消融与对比
        "LoRA & QLoRA": ablation_line or _fallback("LoRA & QLoRA"),
        "VLM": _fallback("VLM"),
        # 能力证据索引（只列 evidence_gate >= 1 的技能）
        "Evaluation": (
            f"能力证据索引：{skill_line}" if skill_line else _fallback("Evaluation")
        ),
        "Inference Benchmark": benchmark_line or _fallback("Inference Benchmark"),
        # 关键结果（已实证测验）
        "Results": verified_line or _fallback("Results"),
        # badcase 与复盘
        "Failure Cases": log_line or _fallback("Failure Cases"),
        "Lessons Learned": (
            "可迁移经验以带产出链接的复盘日志与已实证测验为准；本节不写未实证内容。"
        ),
        # 局限与展望
        "Future Work": (
            "诚实声明：未实证项不进本作品集；下一步按 evidence-gated 缺口补证据。"
        ),
    }

    return {
        "sections": [{"name": n, "content": lines[n]} for n in SECTIONS],
        # 计数 = 四个证据池之和。含 ready：record_evidence_event 只落
        # skill.evidence_gate + SkillAssessment，不产生 verified/log/experiment 行，
        # 若不计 ready，空库上「造一条 L4 硬证据」会得到 evidence_count=0（计划缺陷修补）。
        "evidence_count": len(verified) + len(logs) + len(experiments) + len(ready),
        "ready_skills": [s.name for s in ready],
    }
