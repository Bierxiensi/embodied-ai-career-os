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

import re
import uuid

from app.research.paper_agent.schema import PaperChunk, PaperMeta

# ===== 分块参数 =====
# RAG #2 修复：800 超过 all-MiniLM-L6-v2 的 256 token 截断上限，
# 超长 chunk 会被模型截断导致尾部语义丢失。改为 256 对齐模型上限。
MAX_TOKENS = 256              # 单 chunk 最大 token 数
OVERLAP_TOKENS = 100          # 滑窗重叠 token 数
MIN_CHUNK_TOKENS = 50         # 小于此值合并到上一 chunk（避免碎片）

# ===== 章节标题识别 =====
#
# 🔴 为什么不用"正则直接匹配 Abstract/Introduction/... 这些词"（2026-09-24 重构）：
#
#   PDF 抽取会把 LaTeX 的小体大写（\textsc{}）**拆开**——首字母与其余字母之间多出一个空格。
#   实测本语料（NeurIPS/ICLR 风格的 \textsc 标题）：
#       真实标题                      pypdf 抽取结果
#       1 Introduction            →  1 I NTRODUCTION
#       4 Our Method              →  4 O UR METHOD
#       5 Empirical Experiments   →  5 E MPIRICAL EXPERIMENTS
#       8 Conclusion and Future Work → 8 C ONCLUSION AND FUTURE WORK
#   于是"词面匹配"全部落空，只有不用小体大写的 ABSTRACT 能命中 ——
#   后果是整篇只剩 abstract 一个 section 吞掉全文（实测 LoRA：abstract 段占了 28531 字符，
#   把 Introduction / Problem Statement 全裹进去了）。
#
#   修法：先按"行"取候选标题，再把标题**压成纯字母小写**后与规范名做子串比对
#   （"O UR METHOD" → "ourmethod" → 命中 method）。对空格不敏感，自然免疫上述拆分。
#
# 候选行正则：可选编号 + 标题文字。**不做**"任意短行都算标题"——正文/表格行会大量误判。
_HEADING_LINE = re.compile(
    r"^[ \t]*(?:(\d+(?:\.\d+)*)\.?[ \t]+)?([^\n]{1,60}?)[ \t]*$",
    re.MULTILINE,
)

# 规范章节名 → 归一化桶。**单一真源**，匹配与展示都读它。
_SECTION_NORMALIZE: dict[str, str] = {
    "abstract": "abstract",
    "introduction": "introduction",
    "related work": "introduction",
    "background": "introduction",
    "preliminaries": "introduction",
    "method": "method",
    "methods": "method",
    "approach": "method",
    "methodology": "method",
    "experiment": "experiment",
    "experiments": "experiment",
    "evaluation": "experiment",
    "results": "experiment",
    "analysis": "experiment",
    "ablation": "experiment",
    "conclusion": "conclusion",
    "discussion": "conclusion",
    "future work": "conclusion",
}

# 候选标题的形态约束（用来把正文行/表格行挡在外面）
_MAX_TITLE_CHARS = 50
_MAX_TITLE_WORDS = 8
_UPPER_START = re.compile(r"^[A-Z]")

# 预编译：规范名的"纯字母小写"形式，供子串比对
_FLAT_CANONICAL: list[tuple[str, str]] = [
    (re.sub(r"[^a-z]", "", k), v) for k, v in _SECTION_NORMALIZE.items()
]


def _flatten(title: str) -> str:
    """标题 → 纯字母小写（去空格/标点/数字）。用于免疫小体大写拆分。"""
    return re.sub(r"[^a-z]", "", title.lower())


def _canonical_of(title: str) -> str | None:
    """把标题匹配到规范章节名；匹配不上返回 None。

    "O UR METHOD" → "ourmethod" → 含 "method" → method
    "I NTRODUCTION" → "introduction" → introduction
    """
    flat = _flatten(title)
    if len(flat) < 3:
        return None
    for flat_key, canon in _FLAT_CANONICAL:
        if flat_key and flat_key in flat:
            return canon
    return None


def _looks_like_heading_title(title: str) -> bool:
    """判断候选行的"标题部分"是否像个章节名（用于未识别章节的边界判定）。

    要求：首字母大写、无句号、词数 ≤ 8、长度 ≤ 50。
    这样能挡住正文行与表格行，例如
      "175 billion trainable parameters.1"（小写开头 + 含句号）
      "2 of the first quantization"（小写开头）
      "1 . We use 8-bit Floats ..."（以句号开头）
      "6 7 8 9 10 11" / "2101.00121 arXiv: ..."（非字母开头 / 含句号）
    而放过真正的标题，如 "3 QLoRA Finetuning"、"2 Problem Statement"。
    """
    title = title.strip()
    if not title or len(title) > _MAX_TITLE_CHARS:
        return False
    if "." in title or len(title.split()) > _MAX_TITLE_WORDS:
        return False
    return bool(_UPPER_START.match(title))



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
    page_count = meta.get("page_count", 1) or 1

    for section_name, section_text, section_offset in sections:
        # RAG #3 修复：char_cursor 同步到 section 起始，再按段落递增 len(para)，
        # 使 char_offset 反映 chunk 在原文中的真实位置。
        # 原实现所有段落共用 section_offset，导致同 section 内多个 chunk 偏移失真。
        char_cursor = section_offset
        # 段落切分（双换行）
        paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]

        for para in paragraphs:
            para_tokens = _estimate_tokens(para)

            if para_tokens <= MAX_TOKENS:
                # 单段不超限
                if para_tokens >= MIN_CHUNK_TOKENS or not chunks:
                    # 正常成 chunk（RAG #3: 用 char_cursor 而非 section_offset）
                    chunks.append(_make_chunk(
                        para, section_name, paper_id,
                        char_offset=char_cursor,
                        page_count=page_count,
                        full_text=text,
                    ))
                else:
                    # RAG #1 修复：小段落（< MIN_CHUNK_TOKENS）且已有上一 chunk 时，
                    # 合并到上一 chunk（追加文本 + 更新 token 计数），而非丢弃。
                    # 原实现落入 else 分支什么也不做，导致短段落信息丢失。
                    last = chunks[-1]
                    last["text"] = last.get("text", "") + "\n\n" + para
                    last["token_count"] = _estimate_tokens(last["text"])
            else:
                # 单段超限，滑窗切分
                for sub in _sliding_window(para):
                    chunks.append(_make_chunk(
                        sub, section_name, paper_id,
                        char_offset=char_cursor,
                        page_count=page_count,
                        full_text=text,
                    ))

            # RAG #3 修复：每个段落后递增 char_cursor（按 para 实际长度）
            char_cursor += len(para)

    return chunks


def _split_by_sections(text: str) -> list[tuple[str, str, int]]:
    """按章节标题分割全文。

    流程（2026-09-24 重构为"按行取候选 → 压平比对"）：
      1. 用 `_HEADING_LINE` 逐行取候选（可选编号 + 标题文字）
      2. 标题压成纯字母小写后与规范名做子串比对（免疫小体大写拆分）
      3. 命中 → 该行成为边界；顶层编号（无点）会更新"父章节标签"
      4. 带点编号的子节未命中 → **继承父标签**（子节标题多为描述性，规范名盖不住）
      5. 顶层编号但未命中 + 形态像标题 → 边界，标签 unknown
         （不再让"上一节的标签"一路吞到文末；也不会把正文行误当标题 —— 见 _looks_like_heading_title）

    Returns:
        [(section_name, section_text, char_offset), ...]
        section_name ∈ abstract/introduction/method/experiment/conclusion/unknown
    """
    # matches: (标题起始, 标题结束, 归一化标签)
    #   标题结束位置 = 该行末尾，section_text 从此处开始（剥离标题本身）
    matches: list[tuple[int, int, str]] = []
    parent_label = "unknown"  # 当前顶层章节标签，供子节继承

    for m in _HEADING_LINE.finditer(text):
        number = m.group(1)
        title = (m.group(2) or "").strip()
        if not title:
            continue

        canon = _canonical_of(title)
        is_sub = bool(number) and "." in number

        if canon is not None:
            label = canon
            if number and not is_sub:
                parent_label = canon
        elif is_sub:
            # 子节未命中 → 继承父标签（如 "4.1 Low-Rank ..." 属于 "4 Our Method"）
            label = parent_label
        elif number and _looks_like_heading_title(title):
            # 顶层、名字不在规范表里（如 "3 QLoRA Finetuning"）→ 仍是边界，
            # 但**不能**沿用上一节标签，否则 method 内容会被标成 introduction
            parent_label = "unknown"
            label = "unknown"
        else:
            continue  # 无编号且不认识 → 不是标题

        matches.append((m.start(), m.end(), label))

    if not matches:
        # 无章节标题，整体作为 unknown
        return [("unknown", text, 0)]

    sections: list[tuple[str, str, int]] = []

    # 第一个标题前的内容（论文标题/作者/Abstract 之前的页眉等）归为 unknown
    pre = text[: matches[0][0]]
    if pre.strip():
        sections.append(("unknown", pre, 0))

    for i, (start, title_end, label) in enumerate(matches):
        next_start = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        # section_text 从标题行之后开始（剥离标题本身，避免标题污染 chunk 内容）
        section_text = text[title_end:next_start].lstrip("\n")
        sections.append((label, section_text, start))

    return sections


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
