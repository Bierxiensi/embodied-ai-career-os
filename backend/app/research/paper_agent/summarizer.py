"""论文摘要生成器：chunks → PaperSummary。

Day 1 用规则（关键词匹配 + section 抽取）：
    - title：首行 / 文件名 / <title> 标签
    - method：Method section 首段 + 关键词（"we propose" / "our method"）
    - dataset：匹配 "dataset" / "benchmark" / "SO101" / "LeRobot"
    - contribution：匹配 "contribution" / "we show" / "state-of-the-art"
    - relation_to_my_project：匹配 SO101 / LeRobot / Isaac / ACT / VLA 关键词

Week 2 接 LLM 后：本函数替换为 LLM 调用，签名不变。
"""

from __future__ import annotations

import re

from app.research.paper_agent.schema import PaperChunk, PaperMeta, PaperSummary

# ===== 关键词表 =====
# 方法描述句触发词
_METHOD_KEYWORDS = [
    "we propose", "we present", "our method", "we introduce",
    "we develop", "in this paper", "in this work", "we design",
]

# 数据集触发词
_DATASET_KEYWORDS = [
    "dataset", "benchmark", "data collection", "training data",
    "we collect", "we use", "evaluation on",
]

# 贡献触发词
_CONTRIBUTION_KEYWORDS = [
    "contribution", "we show", "we demonstrate", "state-of-the-art",
    "outperform", "novel", "first to", "our key",
]

# 项目关联关键词（Phase 3 特色：与具身智能项目关联）
_PROJECT_KEYWORDS = {
    "SO101": ["so101", "so-101", "so 101"],
    "LeRobot": ["lerobot", "le-robot", "le robot"],
    "Isaac": ["isaac sim", "isaac lab", "isaac gym", "isaacgym"],
    "ACT": ["action chunking", "act policy", "act "],
    "VLA": ["vision-language-action", "vla ", "openvla", "rt-2", "rt-1"],
    "ROS2": ["ros2", "ros 2", "rclpy"],
    "PyTorch": ["pytorch", "torch "],
    "Imitation Learning": ["imitation learning", "behavior cloning", "bc "],
    "Reinforcement Learning": ["reinforcement learning", "rl ", "policy gradient"],
    # 主流机器人硬件 + 仿真框架（Day 4 多论文对比需要）
    "Franka": ["franka", "franka panda", "panda robot"],
    "Robomimic": ["robomimic"],
    "Robosuite": ["robosuite"],
}


def summarize(
    chunks: list[PaperChunk],
    meta: PaperMeta,
) -> PaperSummary:
    """从 chunks 抽取结构化摘要。

    Args:
        chunks: chunker 产出的 chunk 列表
        meta: 论文元数据（含 title_hint / arxiv_id）

    Returns:
        PaperSummary：title / method / dataset / contribution / relation_to_my_project
    """
    if not chunks:
        return PaperSummary(
            title=meta.get("title_hint", "Unknown"),
            method="",
            dataset="",
            contribution="",
            relation_to_my_project="",
            confidence="low",
        )

    # 按 section 分组
    sections = _group_by_section(chunks)

    # 1. 标题：优先从 abstract 首句提取，否则用 meta.title_hint
    title = _extract_title(sections, meta)

    # 2. 方法：优先 method section，无则全篇回落（方法章节常以技术命名）
    method = _extract_method(sections, chunks)

    # 3. 数据集：扫描全chunks
    dataset = _extract_dataset(chunks)

    # 4. 贡献：扫描全chunks
    contribution = _extract_contribution(chunks)

    # 5. 项目关联：匹配具身智能关键词
    relation = _extract_project_relation(chunks)

    # 6. 置信度：根据提取完整度评估
    confidence = _assess_confidence(title, method, dataset, contribution, relation)

    return PaperSummary(
        title=title,
        method=method,
        dataset=dataset,
        contribution=contribution,
        relation_to_my_project=relation,
        confidence=confidence,
    )


def _group_by_section(chunks: list[PaperChunk]) -> dict[str, list[PaperChunk]]:
    """按 section 分组 chunks。"""
    groups: dict[str, list[PaperChunk]] = {}
    for c in chunks:
        section = c.get("section", "unknown")
        groups.setdefault(section, []).append(c)
    return groups


def _extract_title(
    sections: dict[str, list[PaperChunk]],
    meta: PaperMeta,
) -> str:
    """提取标题。

    策略：
    1. 优先用 meta.title_hint（parser 已从 H1 / 文件名 / 首行尽力提取）
    2. title_hint 缺失或为占位符时，从 abstract 首句兜底

    说明：章节识别后 abstract 首 chunk 是正文首句（如 "We propose ..."），
    直接当标题会失真，因此 title_hint 优先。
    """
    hint = (meta.get("title_hint") or "").strip()
    if hint and hint != "Unknown":
        return hint

    abstract = sections.get("abstract", [])
    if abstract:
        first_line = abstract[0].get("text", "").strip().split("\n")[0].strip()
        # 去除常见前缀
        first_line = re.sub(
            r"^(title|paper title)\s*[:：]\s*", "", first_line, flags=re.IGNORECASE
        )
        if first_line and len(first_line) < 200:
            return first_line

    return hint or "Unknown"


def _is_prose_like(sentence: str) -> bool:
    """粗过滤：判断候选句是否像"正文散文"，用于挡掉公式碎片/表格残留/提示词模板。

    为什么要这道闸门（2026-09-24 实测）：只按关键词取句时，PDF 里的
    `Response B:` / `<the other response>` / `SFT 𝑞,𝑜∼𝑃𝑠𝑓𝑡(𝑄,𝑂)` 这类
    附录模板与公式碎片会被当成"方法描述"（DPO 论文就抽到了提示词模板）。

    判据（宁缺勿滥，宁可返回空也不返回垃圾）：
      - 长度 40-400 字符
      - 至少 6 个词
      - 字母占比 ≥ 0.55（公式/符号串会远低于此）
      - 不含明显的非正文标记（尖括号、竖线、LaTeX 转义）
    """
    s = sentence.strip()
    if not (40 <= len(s) <= 400):
        return False
    if len(s.split()) < 6:
        return False
    if any(ch in s for ch in "<>|\\"):
        return False
    letters = sum(ch.isalpha() for ch in s)
    return letters / len(s) >= 0.55


def _extract_method(
    sections: dict[str, list[PaperChunk]], all_chunks: list[PaperChunk]
) -> str:
    """提取方法描述。

    三级策略（2026-09-24 重写）：
      1. 在 method section 里找含方法关键词且"像散文"的句子
      2. **全篇回落**：论文的方法章节常以技术命名（如 "3 QLoRA Finetuning"、
         "4 Direct Preference Optimization"），规范章节名盖不住，
         此时按关键词在全篇扫（这是命中率从 2/10 提到 10/10 的关键）
      3. 最后兜底：method section 首块前 200 字符 —— **同样过 `_is_prose_like` 闸门**。
         三级都不合格时返回空串：宁可留空，也不把公式/模板当方法描述。

    ⚠️ 第 3 级最初没设闸门，与"宁缺勿滥"的目标自相矛盾（由测试发现）。
    """
    for c in sections.get("method", []):
        sentence = _find_sentence_with_keywords(c.get("text", ""), _METHOD_KEYWORDS)
        if _is_prose_like(sentence):
            return sentence.strip()[:300]

    for c in all_chunks:
        sentence = _find_sentence_with_keywords(c.get("text", ""), _METHOD_KEYWORDS)
        if _is_prose_like(sentence):
            return sentence.strip()[:300]

    method_chunks = sections.get("method", [])
    if method_chunks:
        head = method_chunks[0].get("text", "")[:200].strip()
        if _is_prose_like(head):
            return head

    return ""


def _extract_dataset(chunks: list[PaperChunk]) -> str:
    """提取数据集信息。

    扫描所有 chunks，找含 dataset 关键词的句子。
    """
    for c in chunks:
        text = c.get("text", "")
        sentence = _find_sentence_with_keywords(text, _DATASET_KEYWORDS)
        if sentence:
            return sentence[:300]
    return ""


def _extract_contribution(chunks: list[PaperChunk]) -> str:
    """提取核心贡献。

    扫描所有 chunks，找含贡献关键词的句子。
    """
    for c in chunks:
        text = c.get("text", "")
        sentence = _find_sentence_with_keywords(text, _CONTRIBUTION_KEYWORDS)
        if sentence:
            return sentence[:300]
    return ""


def _extract_project_relation(chunks: list[PaperChunk]) -> str:
    """提取与具身智能项目的关联。

    匹配 SO101 / LeRobot / Isaac / ACT / VLA 等关键词，
    返回命中的项目列表 + 首个命中句。
    """
    hit_projects: list[str] = []
    first_sentence = ""

    for project, keywords in _PROJECT_KEYWORDS.items():
        for c in chunks:
            text = c.get("text", "").lower()
            if any(kw in text for kw in keywords):
                if project not in hit_projects:
                    hit_projects.append(project)
                if not first_sentence:
                    first_sentence = _find_sentence_with_keywords(
                        c.get("text", ""),
                        [kw for kw in keywords if len(kw) > 3],  # 避免短关键词误匹配
                    )
                break

    if not hit_projects:
        # RAG #13 修复：无命中时返回空字符串，而非 17 字默认文案。
        # _assess_confidence 的 `if v and len(v) > 5` 会把默认文案计入"已填充"，
        # 导致置信度虚高（即使其他字段全空也算 medium）。返回空串让其不计入。
        return ""

    relation = f"相关项目: {', '.join(hit_projects)}"
    if first_sentence:
        relation += f"。命中描述: {first_sentence[:200]}"
    return relation


def _find_sentence_with_keywords(text: str, keywords: list[str]) -> str:
    """在文本中找含任一关键词的句子。

    按句号/换行切句，返回首个命中句。
    """
    if not text:
        return ""

    # 按句号、换行、问号切句
    sentences = re.split(r"[.。\n!?！？]", text)
    text_lower = text.lower()

    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            # 找含此关键词的句子
            for s in sentences:
                if kw_lower in s.lower():
                    return s.strip()

    return ""


def _assess_confidence(
    title: str,
    method: str,
    dataset: str,
    contribution: str,
    relation: str,
) -> str:
    """评估摘要置信度。

    根据提取字段完整度：4-5 项有内容为 high，2-3 项为 medium，0-1 项为 low。
    """
    filled = sum(1 for v in [title, method, dataset, contribution, relation] if v and len(v) > 5)
    if filled >= 4:
        return "high"
    elif filled >= 2:
        return "medium"
    else:
        return "low"
