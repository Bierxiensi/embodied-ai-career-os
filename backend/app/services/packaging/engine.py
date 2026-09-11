"""求职包装引擎（P4）。

把「证据链」组装成两份**可导出、可润色**的成品骨架：

1. ``build_readme_skeleton`` —— 论文体 README 骨架（plan_30d Day 24 的 13 节要求）。
   数据能填的（里程碑 / 涉及技能及证据 / 实验记录）由证据链自动填；
   只有人能写的（Motivation / Failure Cases / Lessons Learned …）留**带提示的占位**，
   而不是留空白 —— 目标是「导出 + 润色」，不是「从空白开始写」。

2. ``build_skill_lines`` —— 简历技能行，**只收录有真实证据（gate ≥ 1）的技能**。
   自评较强（level ≥ 3）但尚无证据的技能进 ``pending`` 列表 —— 它们正是"防虚构"要盯住的行：
   现在写进简历就是虚构。

纯函数、不碰 DB、可单测 —— 与 Match / Resume / Interview / Report 四个引擎同一取向
（见 JOB_SEARCH_AGENT_DESIGN.md §0.1.3 的有意偏离说明）。"从哪取数"交给 ``service.py``。
"""

from __future__ import annotations

# ───────────────────────────── README 骨架 ─────────────────────────────

# plan_30d.py Day 24「README 写成论文」明确的结构（顺序即上方元组顺序）。
README_SECTIONS: tuple[str, ...] = (
    "Motivation",
    "Architecture",
    "Environment",
    "Dataset",
    "Training",
    "LoRA & QLoRA",
    "VLM",
    "Evaluation",
    "Inference Benchmark",
    "Results",
    "Failure Cases",
    "Lessons Learned",
    "Future Work",
)

# 每个章节的写作提示。有提示的占位 >> 空标题：让人知道这一节该写什么、写到什么颗粒度。
SECTION_HINTS: dict[str, str] = {
    "Motivation": "为什么做这个项目 —— 从真实痛点或论文缺口出发。不要写「为了学习 X」。",
    "Architecture": "系统结构与数据流；每个关键模块一句话说明它负责什么。",
    "Environment": "硬件 / 驱动 / 软件栈 / 版本（模型、CUDA、显存、量化位宽）。",
    "Dataset": "数据来源、规模、切分方式、标注口径；有没有自己造的评测集。",
    "Training": "训练配置与关键决策（学习率 / batch / 轮数 / 早停口径）。",
    "LoRA & QLoRA": "两种 PEFT 的对照设置（秩、target_modules、是否 4bit）与取舍理由。",
    "VLM": "多模态部分的输入输出形态、视觉编码器如何接到语言模型、对齐方式。",
    "Evaluation": "评测指标口径与基线；同一口径下谁能比、谁不能比。",
    "Inference Benchmark": "TTFT / Throughput / 峰值显存 等推理侧指标与测试条件。",
    "Results": "主结果表：数字 + 与 baseline 的差值 + 结论一句话。",
    "Failure Cases": "失败与翻车记录（哪次不收敛、哪个假设被推翻、怎么定位的）。**这一节不得留空。**",
    "Lessons Learned": "可迁移的经验（下次会怎么做、踩的坑的根因）。**这一节不得留空。**",
    "Future Work": "下一步方向与判断依据。",
}

# 「不得留空」的章节 —— 面试官最看重，单独标红提示
REQUIRED_SECTIONS: tuple[str, ...] = ("Failure Cases", "Lessons Learned")

_MILESTONE_ICON: dict[str, str] = {
    "completed": "✅",
    "in_progress": "🔄",
    "doing": "🔄",
    "locked": "🔒",
    "todo": "⬜",
}


def _placeholder(section: str) -> str:
    """生成带提示的占位段落。"""

    hint = SECTION_HINTS.get(section, "（待补）")
    if section in REQUIRED_SECTIONS:
        return f"> ⚠️ **必填** —— {hint}"
    return f"> 📝 待补：{hint}"


def build_readme_skeleton(
    *,
    name: str,
    goal: str,
    description: str | None = None,
    github_url: str | None = None,
    status: str = "active",
    current_version: str = "V0",
    milestones: list[dict] | None = None,
    skills: list[str] | None = None,
    evidence_by_skill: dict[str, dict] | None = None,
    experiments: list[dict] | None = None,
) -> str:
    """从证据链生成论文体 README 骨架。

    Args:
        name / goal / description / github_url / status / current_version: 项目本身字段。
        milestones: ``[{version, title, goal, status}]``（顺序即展示顺序）。
        skills: 项目涉及技能名列表。
        evidence_by_skill: ``{技能名: {"gate_level": int, "evidence": [{level,label,ref}]}}``。
        experiments: ``[{name, kind, variant_count, conclusion}]``。

    Returns:
        markdown 字符串。
    """

    milestones = milestones or []
    skills = skills or []
    evidence_by_skill = evidence_by_skill or {}
    experiments = experiments or []

    lines: list[str] = [f"# {name}", "", f"> {goal}", ""]

    meta: list[str] = [f"**状态**：{status}", f"**版本**：{current_version}"]
    if github_url:
        meta.append(f"**仓库**：{github_url}")
    lines.append(" · ".join(meta))
    lines.append("")

    if description:
        lines.extend([description.strip(), ""])

    lines.extend([
        "<!-- 本骨架由 Embodied AI Career OS 从证据链生成（P4）。",
        "     📝 待补 = 需要你补写；带数据的段落已自动填好，请核对数字后润色。",
        "     🎯 验收标准：像论文，不像课程作业。 -->",
        "",
    ])

    for section in README_SECTIONS:
        lines.extend([f"## {section}", "", _placeholder(section), ""])

        # 里程碑进度（挂在 Architecture 之后，作为「做到了哪一步」的客观记录）
        if section == "Architecture":
            lines.extend(_render_milestones(milestones))

        # 实验记录（Results 的证据来源；没有实验记录就不硬编）
        if section == "Results":
            lines.extend(_render_experiments(experiments))

    # ── 附录：证据链（技能 → 真实产出）──
    lines.extend(["---", "", "## 附录 · 技能证据链", ""])
    lines.extend(_render_skill_evidence(skills, evidence_by_skill))

    lines.extend([
        "",
        "---",
        "*骨架由 Embodied AI Career OS 生成 · 请在此基础上润色（勿从空白开始写）*",
    ])

    return "\n".join(lines)


def _render_milestones(milestones: list[dict]) -> list[str]:
    """渲染里程碑进度表；无数据时给出「怎么才会有数据」的提示。"""

    if not milestones:
        return [
            "### 里程碑进度",
            "",
            "> 📝 待补：本项目尚未录入里程碑。在 `/projects` 下添加里程碑后，这里会自动生成进度表。",
            "",
        ]

    out = ["### 里程碑进度", ""]
    done = sum(1 for m in milestones if m.get("status") == "completed")
    out.append(f"进度 **{done}/{len(milestones)}**（{round(done / len(milestones) * 100)}%）")
    out.append("")
    for m in milestones:
        icon = _MILESTONE_ICON.get(m.get("status", ""), "⬜")
        title = m.get("title") or m.get("version") or "（未命名）"
        goal = m.get("goal") or ""
        version = m.get("version") or ""
        suffix = f" — {goal}" if goal else ""
        out.append(f"- {icon} **{version}** {title}{suffix}")
    out.append("")
    return out


def _render_experiments(experiments: list[dict]) -> list[str]:
    """渲染实验记录对比表；无数据时给出「怎么才会有数据」的提示。"""

    if not experiments:
        return [
            "### 实验记录",
            "",
            "> 📝 待补：尚无实验记录。在 `/experiments` 记一条（多变体实验即为 L3/L4 证据），"
            "这里会自动生成对比表。",
            "",
        ]

    out = [
        "### 实验记录",
        "",
        "| 实验 | 类型 | 变体数 | 结论 |",
        "|---|---|---|---|",
    ]
    for e in experiments:
        conclusion = (e.get("conclusion") or "—").replace("\n", " ").strip()
        out.append(
            f"| {e.get('name', '—')} | {e.get('kind', '—')} | "
            f"{e.get('variant_count', 0)} | {conclusion} |"
        )
    out.append("")
    return out


def _render_skill_evidence(
    skills: list[str], evidence_by_skill: dict[str, dict]
) -> list[str]:
    """渲染「技能 → 证据」附录。gate ≥ 1 的技能列真实产出，gate 0 的明确标为无证据。"""

    if not skills:
        return [
            "> 📝 待补：本项目尚未关联技能。给里程碑下的任务填 `skill_name` 后，",
            "> 这里会自动列出「哪项技能、凭什么证据」。",
            "",
        ]

    out: list[str] = []
    gated = [s for s in skills if (evidence_by_skill.get(s) or {}).get("gate_level", 0) >= 1]
    ungated = [s for s in skills if s not in gated]

    if gated:
        out.append("以下技能已有**可核验证据**（Level 越高越硬）：")
        out.append("")
        for s in gated:
            info = evidence_by_skill.get(s) or {}
            gate = info.get("gate_level", 0)
            out.append(f"- **{s}**（证据 L{gate}）")
            for item in info.get("evidence") or []:
                out.append(
                    f"  - `L{item.get('level', '?')}` {item.get('label', '')}："
                    f"{item.get('ref', '')}"
                )
        out.append("")

    if ungated:
        out.append("以下技能**已声明但尚无自动可核验证据**（按 P2 规则需笔记/代码/实验支撑）：")
        out.append("")
        for s in ungated:
            out.append(f"- {s}")
        out.append("")

    return out


# ───────────────────────────── 简历技能行 ─────────────────────────────

# gate = 0 时缺的第一步证据（与 core/evidence.py 的 L1 口径对齐）
MISSING_FIRST_STEP = "缺 L1 证据：该技能映射课程日的笔记，或一道关联面试题"


def build_skill_lines(
    *,
    skills: list[dict],
    evidence_by_skill: dict[str, dict],
    pending_min_level: int = 3,
) -> dict:
    """生成「简历技能行」。

    简历行**只收录有真实证据的技能**（``evidence_gate >= 1``），每行附证据清单，
    对应 plan_30d Day 25 验收：「简历技能行每一项都能点开对应证据（代码 / 实验 / 论文）」。

    自评 level ≥ ``pending_min_level`` 却尚无证据的技能进 ``pending`` —— 它们是
    写进简历即构成虚构风险的候选，需要先去补证据。

    ``pending`` 不截断：其条数受技能总数约束（48），且 ``summary.pending`` 必须与
    返回列表长度一致 —— 曾经截断到 12 但与 summary 不符，前端会显示"16 项却只有 12 个"。

    Args:
        skills: ``[{name, level, category}]``。
        evidence_by_skill: ``{技能名: {"gate_level": int, "evidence": [{level,label,ref}]}}``。

    Returns:
        ``{"ready": [...], "pending": [...], "summary": {...}}``
    """

    ready: list[dict] = []
    pending: list[dict] = []

    for sk in skills:
        name = sk.get("name")
        if not name:
            continue
        level = int(sk.get("level") or 0)
        info = evidence_by_skill.get(name) or {}
        gate = int(info.get("gate_level") or 0)
        items = list(info.get("evidence") or [])
        # 取最高一级证据作为行内引用（gate 与 items 由同一函数产出，保持一致）
        top = max(items, key=lambda i: i.get("level", 0)) if items else None
        top_ref = (top or {}).get("ref", "")

        if gate >= 1:
            ready.append(
                {
                    "skill": name,
                    "level": level,
                    "category": sk.get("category"),
                    "gate_level": gate,
                    "line": f"{name}（L{level}）：{top_ref}" if top_ref else f"{name}（L{level}）",
                    "refs": items,
                }
            )
        elif level >= pending_min_level:
            pending.append(
                {
                    "skill": name,
                    "level": level,
                    "category": sk.get("category"),
                    "gate_level": gate,
                    "missing": MISSING_FIRST_STEP,
                }
            )

    ready.sort(key=lambda r: (-r["gate_level"], -r["level"], r["skill"]))
    pending.sort(key=lambda p: (-p["level"], p["skill"]))

    return {
        "ready": ready,
        "pending": pending,
        "summary": {
            "total": len(skills),
            "ready": len(ready),
            "pending": len(pending),
            "pending_min_level": pending_min_level,
        },
    }
