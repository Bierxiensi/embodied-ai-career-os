"""单元内容懒生成（spec §3.3）。

纪律（spec §5.1）：
- 打开才生成；已有条目即返回（幂等）。content_hash 仅记录生成指纹，升级/重生成路径属后续增强票。
- LLM 优先，Mock/异常一律降级 rule —— MockClient 的模板文案**绝不**冒充内容
  （同 knowledge answer_node 的 Mock 判定纪律）。
- generation_mode 落库 + 随 API 返回，UI 必须显示徽标。
- 两级模型口径（spec §3.3）：高频出题/判定走 flash、摘要 reduce 走强模型——
  由 XIAOMI_MODEL 配置层切换（改一行 + 重启），不引入 per-call 复杂度。
"""

from __future__ import annotations

import hashlib
import json

from app.models.mastery import MasteryUnit, UnitItem

# rule 兜底的题库骨架：按技能给一组固定考点（闭卷实证用）
_RULE_QUIZ = {
    "DPO": [
        ("DPO 绕过了什么显式组件？", "奖励模型", "Bradley-Terry 隐式奖励参数化"),
        ("DPO 的优化目标本质是什么？", "最大似然", "单目标函数同时完成两步工作"),
    ],
    "LoRA": [
        ("LoRA 冻结什么、训练什么？", "冻结原权重训练低秩增量", "W + BA，B/A 为低秩矩阵"),
        ("QLoRA 相比 LoRA 多了什么？", "4-bit 量化基座", "bitsandbytes NF4 + 双重量化"),
    ],
    "RLHF": [
        ("RLHF 三阶段是？", "SFT/RM/PPO", "先精调、再奖励模型、再强化学习"),
    ],
    "GRPO": [
        ("GRPO 去掉了 PPO 的什么？", "价值网络", "组内相对优势估计"),
    ],
}
_DEFAULT_QUIZ = [
    ("本单元的核心方法一句话是？", "见 summary 要点", "以 summary 的首要点为准"),
]


def _content_hash(spec_text: str) -> str:
    return hashlib.sha256(spec_text.encode("utf-8")).hexdigest()


def _is_mock() -> bool:
    from app.llm import get_llm

    return type(get_llm()).__name__ == "MockClient"


def _generate_llm(unit: MasteryUnit) -> list[dict] | None:
    """LLM 生成内容包；Mock/异常返回 None（调用方降级 rule）。"""
    if _is_mock():
        return None
    try:
        from app.llm import ChatMessage, get_llm

        llm = get_llm()
        result = llm.chat_json([
            ChatMessage(role="system", content="你是学习内容工程师。只输出 JSON。"),
            ChatMessage(
                role="user",
                content=(
                    f"为主题「{unit.title}」生成学习包，技能：{unit.skill_ids}。\n"
                    '返回 JSON：{"summary": "<120-200字摘要>", '
                    '"concepts": [{"front": "<概念>", "back": "<一句话解释>"} ... 3 个], '
                    '"quiz": [{"question": "<问题>", "answer": "<参考答案>", "rationale": "<依据>"} ... 3 个]}'
                ),
            ),
        ])
        if not isinstance(result, dict) or not result.get("summary"):
            return None
        items = [{"kind": "summary", "body": result["summary"]}]
        for c in result.get("concepts", [])[:5]:
            items.append({"kind": "concept_card", "body": c.get("front", ""), "answer": c.get("back", "")})
        for q in result.get("quiz", [])[:5]:
            items.append({
                "kind": "quiz_q",
                "body": q.get("question", ""),
                "answer": q.get("answer", ""),
                "rationale": q.get("rationale", ""),
            })
        return items
    except Exception:
        return None


def _generate_rule(unit: MasteryUnit) -> list[dict]:
    """rule 兜底：用元数据与固定考点拼内容包（诚实标注 rule，不装 LLM）。"""
    skills = json.loads(unit.skill_ids or "[]")
    quiz = _RULE_QUIZ.get(skills[0] if skills else "", _DEFAULT_QUIZ)
    summary = (
        f"「{unit.title}」学习包（规则生成）：围绕 {unit.source_ref} 的核心要点展开，"
        f"关联技能 {', '.join(skills) or '未标注'}。"
        "先读摘要建立地图，再用概念卡自测，最后做测验实证掌握。"
        "本内容由规则模板生成（generation_mode=rule），仅作学习骨架——如需 AI 生成版本，请在 LLM 可用后手动重生成。"
    )
    items = [{"kind": "summary", "body": summary}]
    for skill in skills[:3]:
        items.append({
            "kind": "concept_card",
            "body": f"{skill} 核心思想",
            "answer": f"能用自己的话讲清 {skill} 解决什么问题、不解决什么",
        })
    for question, answer, rationale in quiz:
        items.append({"kind": "quiz_q", "body": question, "answer": answer, "rationale": rationale})
    return items


def ensure_unit_content(db, unit: MasteryUnit) -> list[UnitItem]:
    """懒生成入口：已有内容直接返回；未生成则 llm|rule 生成落库。"""
    existing = (
        db.query(UnitItem).filter_by(unit_id=unit.id).order_by(UnitItem.id).all()
    )
    if existing:
        if unit.status == "locked":
            unit.status = "opened"
            db.commit()
        return existing

    spec_text = f"{unit.source_type}:{unit.source_ref}:{unit.title}:{unit.skill_ids}"
    hashed = _content_hash(spec_text)

    raw = _generate_llm(unit)
    mode = "llm"
    if raw is None:
        raw = _generate_rule(unit)
        mode = "rule"

    items = [UnitItem(unit_id=unit.id, **spec) for spec in raw]
    db.add_all(items)
    unit.generation_mode = mode
    unit.content_hash = hashed
    unit.status = "opened"
    db.commit()
    for it in items:
        db.refresh(it)
    return items
