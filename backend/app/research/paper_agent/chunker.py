"""论文分块器：文本 → 语义 chunk。

分块策略（优先级从高到低）：
    1. 结构切分：按 Abstract / Introduction / Method / Experiment / Conclusion 标题切
    2. 段落切分：结构内按双换行分段
    3. 滑窗兜底：单段超 MAX_TOKENS 时按滑窗切（含 overlap）

设计要点：
- 结构优先：论文有明确章节标题，按 section 切比纯滑窗更利于 Day 2 检索
- chunk metadata：每个 chunk 带 section + page，Day 2 向量检索可按 section 过滤
- token 估算：用 len(text) // 4 粗估（英文约 4 char/token），避免引入 tokenizer 依赖
"""

from __future__ import annotations

import uuid

from app.research.paper_agent.schema import PaperChunk, PaperMeta

# ===== 分块参数 =====
MAX_TOKENS = 800              # 单 chunk 最大 token 数
OVERLAP_TOKENS = 100          # 滑窗重叠 token 数
MIN_CHUNK_TOKENS = 50         # 小于此值合并到上一 chunk（避免碎片）

# 章节标题正则（大小写不敏感，支持数字编号 + Markdown # 前缀）
# 匹配：Abstract / 1. Introduction / II. METHOD / 3.2 Experiment / ## Method 等
# Markdown 的 #/##/### 作为可选前缀
_MD_PREFIX = r"(?:#{1,6}\s+)?"  # 1-6 个 # 作为 Markdown 标题前缀
_SECTION_PATTERNS = [
    rf"(?:^|\n)\s*{_MD_PREFIX}(?:\d+\.?\s*|I+\.?\s*)?Abstract\s*(?:\n|$)",
    rf"(?:^|\n)\s*{_MD_PREFIX}(?:\d+\.?\s*|I+\.?\s*)?Introduction\s*(?:\n|$)",
    rf"(?:^|\n)\s*{_MD_PREFIX}(?:\d+\.?\s*|I+\.?\s*)?(?:Related\s+Work|Background)\s*(?:\n|$)",
    rf"(?:^|\n)\s*{_MD_PREFIX}(?:\d+\.?\s*|I+\.?\s*)?(?:Method|Methods|Approach|Methodology)\s*(?:\n|$)",
    rf"(?:^|\n)\s*{_MD_PREFIX}(?:\d+\.?\s*|I+\.?\s*)?(?:Experiment|Experiments|Evaluation|Results)\s*(?:\n|$)",
    rf"(?:^|\n)\s*{_MD_PREFIX}(?:\d+\.?\s*|I+\.?\s*)?(?:Conclusion|Discussion|Future\s+Work)\s*(?:\n|$)",
]

# 章节名标准化映射
_SECTION_NORMALIZE = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "introduction",
    "background": "introduction",
    "method": "method",
    "methods": "method",
    "approach": "method",
    "methodology": "method",
    "experiment": "experiment",
    "experiments": "experiment",
    "evaluation": "experiment",
    "results": "experiment",
    "conclusion": "conclusion",
    "discussion": "conclusion",
    "future work": "conclusion",
}


def chunk(
    text: str,
    meta: PaperMeta,
    paper_id: str,
) -> list[PaperChunk]:
    """按论文结构语义分块。

    Args:
        text: parser 提取的全文
        meta: 论文元数据（用 page_count 估算页码）
        paper_id: 关联的 Paper.id

    Returns:
        chunk 列表，每个含 text / section / page / char_offset / token_count
    """
    if not text or not text.strip():
        return []

    # 1. 结构切分：按章节标题分割
    sections = _split_by_sections(text)

    # 2. 段落 + 滑窗切分
    chunks: list[PaperChunk] = []
    char_cursor = 0  # 全局字符偏移游标
    page_count = meta.get("page_count", 1) or 1

    for section_name, section_text, section_offset in sections:
        # 段落切分（双换行）
        paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]

        for para in paragraphs:
            para_tokens = _estimate_tokens(para)

            if para_tokens <= MAX_TOKENS:
                # 单段不超限，直接成 chunk
                if para_tokens >= MIN_CHUNK_TOKENS or not chunks:
                    chunks.append(_make_chunk(
                        para, section_name, paper_id,
                        char_offset=section_offset,
                        page_count=page_count,
                        full_text=text,
                    ))
            else:
                # 单段超限，滑窗切分
                for sub in _sliding_window(para):
                    chunks.append(_make_chunk(
                        sub, section_name, paper_id,
                        char_offset=section_offset,
                        page_count=page_count,
                        full_text=text,
                    ))

    return chunks


def _split_by_sections(text: str) -> list[tuple[str, str, int]]:
    """按章节标题分割全文。

    Returns:
        [(section_name, section_text, char_offset), ...]
        section_name 为标准化名（abstract/method/experiment/conclusion/introduction/unknown）
        未匹配到标题的部分归为 "unknown"
    """
    import re

    # 收集所有章节标题位置
    # matches: (title_start, title_end, normalized_name)
    #   title_end 为标题行结束位置，section_text 从此处开始（剥离标题本身）
    matches: list[tuple[int, int, str]] = []
    for pattern in _SECTION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            raw_title = m.group(0).strip().strip(".").strip()
            # 剥离 Markdown # 前缀（## Abstract → Abstract）
            raw_title = re.sub(r"^#{1,6}\s*", "", raw_title)
            # 去除前导数字/罗马数字编号（1. Introduction → Introduction）
            raw_title = re.sub(r"^[\dIVXLC]+\.\s*", "", raw_title, flags=re.IGNORECASE)
            normalized = _normalize_section(raw_title)
            # 跳过无法标准化的标题（避免误切，保留原文本流）
            if normalized == "unknown":
                continue
            matches.append((m.start(), m.end(), normalized))

    if not matches:
        # 无章节标题，整体作为 unknown
        return [("unknown", text, 0)]

    # 按标题起始位置排序、去重（同位置多 pattern 命中只保留首个）
    matches.sort(key=lambda x: x[0])
    deduped: list[tuple[int, int, str]] = []
    for m in matches:
        if deduped and m[0] == deduped[-1][0]:
            continue
        deduped.append(m)
    matches = deduped

    sections: list[tuple[str, str, int]] = []

    # 标题前的内容（如果有）归为 unknown（如 MD 的 H1 论文标题行）
    if matches[0][0] > 0:
        pre = text[: matches[0][0]]
        if pre.strip():
            sections.append(("unknown", pre, 0))

    for i, (start, title_end, normalized) in enumerate(matches):
        next_start = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        # section_text 从标题行之后开始，剥离标题本身（避免标题污染 chunk 内容）
        section_text = text[title_end:next_start].lstrip("\n")
        sections.append((normalized, section_text, start))

    return sections


def _normalize_section(raw: str) -> str:
    """标准化章节名。"""
    key = raw.lower().strip()
    return _SECTION_NORMALIZE.get(key, "unknown")


def _sliding_window(text: str) -> list[str]:
    """滑窗切分超长段落。

    按 MAX_TOKENS * 4 字符切窗，含 OVERLAP_TOKENS * 4 字符重叠。
    """
    max_chars = MAX_TOKENS * 4
    overlap_chars = OVERLAP_TOKENS * 4
    step = max_chars - overlap_chars

    result: list[str] = []
    i = 0
    while i < len(text):
        end = i + max_chars
        result.append(text[i:end])
        if end >= len(text):
            break
        i += step
    return result


def _estimate_tokens(text: str) -> int:
    """粗估 token 数（英文约 4 char/token）。"""
    return max(1, len(text) // 4)


def _make_chunk(
    text: str,
    section: str,
    paper_id: str,
    char_offset: int,
    page_count: int,
    full_text: str,
) -> PaperChunk:
    """构造单个 PaperChunk。

    page 估算：按 char_offset 在全文中的比例映射到页码。
    """
    # 估算页码：按字符位置比例
    if page_count > 1 and full_text:
        page = min(page_count, (char_offset // max(1, len(full_text) // page_count)) + 1)
    else:
        page = 1

    return PaperChunk(
        chunk_id=str(uuid.uuid4()),
        paper_id=paper_id,
        text=text,
        section=section,
        page=page,
        char_offset=char_offset,
        token_count=_estimate_tokens(text),
    )
