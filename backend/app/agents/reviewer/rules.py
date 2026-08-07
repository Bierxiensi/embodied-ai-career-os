"""Reviewer 评估规则（纯函数，可单测）。

Evidence Score 评分体系（Day7 v1，rule-based）：
    Task 完成        30 分
    学习日志（≥20字） 20 分
    Artifact 链接    30 分
    反思关键词       20 分
    ─────────────────────
    合计            100 分

决策：
    >= 80  → level +1（不超过 target_level），confidence = score/100
    50-79  → level 不变，evidence 追加，confidence = score/100
    < 50   → level 不变，无 evidence 追加，reason = "insufficient evidence"

设计原则：
- 纯函数，无副作用，便于单测
- 确定性：相同输入永远相同输出（Day6 测试验证过此模式的价值）
- Phase2 接 LLM 时，仅替换 evaluate_evidence 节点，规则函数保留作为兜底
"""

from __future__ import annotations

# 评分项分值
SCORE_TASK_DONE = 30
SCORE_LOG_SUFFICIENT = 20
SCORE_ARTIFACT = 30
SCORE_REFLECTION = 20

# 日志最低字数阈值
MIN_LOG_LENGTH = 20

# 反思关键词（命中任一即给分）
REFLECTION_KEYWORDS = ["总结", "反思", "学到", "问题", "改进", "收获", "难点", "下一步"]

# 决策阈值
THRESHOLD_LEVEL_UP = 80      # >= 80 升级
THRESHOLD_EVIDENCE = 50      # >= 50 追加 evidence


def score_evidence(task: dict, learning_log: dict) -> int:
    """计算证据得分。

    Args:
        task: 任务字典（需含 status）
        learning_log: 学习日志字典（需含 content，可选 artifact_url）

    Returns:
        证据得分 0-100
    """
    score = 0

    # 1. Task 完成状态（30 分）
    if task.get("status") == "done":
        score += SCORE_TASK_DONE

    # 2. 学习日志内容充分（20 分）：非空且 >= 20 字
    content = learning_log.get("content", "") or ""
    if len(content.strip()) >= MIN_LOG_LENGTH:
        score += SCORE_LOG_SUFFICIENT

    # 3. Artifact 链接（30 分）：非空 URL
    artifact_url = learning_log.get("artifact_url", "") or ""
    if artifact_url.strip():
        score += SCORE_ARTIFACT

    # 4. 反思关键词（20 分）：content 命中任一关键词
    if any(kw in content for kw in REFLECTION_KEYWORDS):
        score += SCORE_REFLECTION

    return score


def decide_level(
    score: int, old_level: int, target_level: int
) -> tuple[int, float, str, bool]:
    """根据得分决策新等级。

    Args:
        score: 证据得分 0-100
        old_level: 当前等级 0-5
        target_level: 目标等级 0-5（上限，不超过）

    Returns:
        (new_level, confidence, reason, evidence_should_append)
        - new_level: 决策后等级
        - confidence: 置信度 0-1
        - reason: 人类可读理由
        - evidence_should_append: 是否追加 evidence（artifact_url）
    """
    confidence = round(score / 100, 2)

    if score >= THRESHOLD_LEVEL_UP:
        # 证据充分，候选升级
        if old_level >= target_level:
            # 已达目标，不再升级
            return (
                old_level,
                confidence,
                f"已达目标等级 {target_level}，维持现状",
                True,  # 仍追加 evidence 记录学习成果
            )
        new_level = old_level + 1
        return (
            new_level,
            confidence,
            f"证据充分（{score}分），等级 {old_level} → {new_level}",
            True,
        )

    if score >= THRESHOLD_EVIDENCE:
        # 证据部分充分，维持等级但记录 evidence
        return (
            old_level,
            confidence,
            f"证据部分充分（{score}分），维持等级 {old_level}",
            True,
        )

    # 证据不足
    return (
        old_level,
        confidence,
        "insufficient evidence",
        False,
    )


def build_evidence_entry(task: dict, learning_log: dict) -> str:
    """构建追加到 Skill.evidence 的条目。

    格式：任务标题 + artifact（如有）
    例："完成 Isaac Sim 基础环境搭建 | https://github.com/xxx"
    """
    title = task.get("title", "未知任务")
    artifact = learning_log.get("artifact_url", "")
    if artifact:
        return f"{title} | {artifact}"
    return title
