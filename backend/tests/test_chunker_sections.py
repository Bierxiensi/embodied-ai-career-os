r"""分节器回归测试：学术 PDF 的标题必须能识别（两种典型形态）。

背景一（2026-09-23 实测缺陷）：无点编号标题
    论文 PDF 经 pypdf 抽出的标题形态是 `1 Introduction` / `6 Experiments`
    （数字后**没有点**，学术排版常态）。原实现的两处口径不一致：
      · 匹配侧允许无点编号（`\d+\.?\s*`）
      · 但剥编号的正则 `^[\dIVXLC]+\.\s*` **要求必须有点**
    → 无点标题被匹配到却剥不掉编号 → 归一化失败 → 被丢弃。
      后果：整篇 PDF 只剩无编号的 "Abstract"，其 section 一直延伸到文末，
      滑窗切成 N 块全部标成 abstract（实测 DPO 论文 147 块里 146 块是 abstract）。

背景二（2026-09-24 实测缺陷）：小体大写被 PDF 抽取拆开
    LaTeX 的 `\textsc{}` 标题抽取后会多出空格：真实 `1 Introduction` 变成
    `1 I NTRODUCTION`、`4 Our Method` 变成 `4 O UR METHOD`。
    于是"按词面匹配章节名"全部落空，整篇只剩 `ABSTRACT` 一个 section
    （实测 LoRA：abstract 段占 28531 字符，把 Introduction/Problem Statement 全裹进去了）。
    修法：标题**压成纯字母小写**后与规范名做子串比对（`ourmethod` 含 `method`），
    对空格不敏感，自然免疫拆分。

本文件还守住修复时**刻意避开的一个坑**：
    若剥编号写成"点可选且无空白要求"，则首字母落在罗马数字集里的标题会被吃掉
    —— "Introduction" 的 I、"Conclusion" 的 C（C=100）。故必须有空白兜底。
"""

from __future__ import annotations

import pytest

from app.research.paper_agent.chunker import chunk

META = {
    "source_path": "test.pdf",
    "file_type": "pdf",
    "page_count": 1,
    "title_hint": "Test Paper",
    "arxiv_id": "",
}

# 每段正文都要足够长，避免被 MIN_CHUNK_TOKENS 合并掉
_BODY = "This section contains enough body text to survive chunking. " * 12


def _sections(text: str) -> set[str]:
    chunks = chunk(text, META, "chunker-test")
    return {c["section"] for c in chunks}


@pytest.mark.parametrize(
    "heading,expected",
    [
        ("1 Introduction", "introduction"),          # ← 修复前会丢
        ("6 Experiments", "experiment"),             # ← 修复前会丢
        ("7 Discussion", "conclusion"),              # ← 修复前会丢
        ("1. Introduction", "introduction"),         # 有点编号（原本就能过）
        ("2. Method", "method"),
        ("II. METHOD", "method"),                    # 罗马数字
        ("## Abstract", "abstract"),                 # Markdown（原有用例形态）
        ("### Related Work", "introduction"),
    ],
)
def test_numbered_headings_are_recognized(heading, expected):
    """无点/有点编号、罗马数字、Markdown 前缀 —— 都必须识别出预期 section。"""
    text = f"{heading}\n{_BODY}\n"
    assert expected in _sections(text), f"标题 {heading!r} 未被识别为 {expected}"


@pytest.mark.parametrize("heading", ["Introduction", "Conclusion", "Methods"])
def test_headings_starting_with_roman_letters_are_not_mangled(heading):
    r"""回归坑：剥编号的正则不得吃掉首字母为 I/V/X/L/C 的标题。

    "Conclusion" 的 C、"Introduction" 的 I 都在 [IVXLC] 里（C 是罗马数字 100）。
    若剥编号写成"点可选且无空白要求"，标题会被截成 "onclusion"/"ntroduction" → 变 unknown。
    必须有空白兜底才能既接受 `1 Introduction` 又不误伤 `Introduction`。
    """
    text = f"{heading}\n{_BODY}\n"
    assert "unknown" not in _sections(text), f"{heading!r} 被错误截断成 unknown"


def test_pdf_style_paper_yields_multiple_sections():
    """整篇文档级断言：不再是"只剩一个 abstract 吞掉全文"。"""
    text = (
        "Abstract\n" + _BODY + "\n"
        "1 Introduction\n" + _BODY + "\n"
        "2 Method\n" + _BODY + "\n"
        "6 Experiments\n" + _BODY + "\n"
        "7 Conclusion\n" + _BODY + "\n"
    )
    sections = _sections(text)
    assert {"abstract", "introduction", "method", "experiment", "conclusion"} <= sections, (
        f"应识别出 5 个章节，实际 {sections}"
    )


# ============================================================
# 小体大写被 PDF 抽取拆开（2026-09-24 修复）
# ============================================================

@pytest.mark.parametrize(
    "heading,expected",
    [
        # LaTeX \textsc{} 抽取后首字母与其余字母之间多一个空格
        ("1 I NTRODUCTION", "introduction"),
        ("4 O UR METHOD", "method"),
        ("5 E MPIRICAL EXPERIMENTS", "experiment"),
        ("8 C ONCLUSION AND FUTURE WORK", "conclusion"),
        ("2 R ELATED WORK", "introduction"),
        ("3 P RELIMINARIES", "introduction"),
        # 全大写但未被拆开（LoRA/QLoRA 的 ABSTRACT 就是这样）
        ("ABSTRACT", "abstract"),
    ],
)
def test_smallcaps_split_headings_are_recognized(heading, expected):
    r"""小体大写拆分标题必须能识别。

    实测：`\textsc{}` 标题经 pypdf 抽取后变成 "I NTRODUCTION" / "O UR METHOD"，
    词面匹配全部落空 → 整篇只剩 ABSTRACT 一个 section（LoRA 的 abstract 段
    曾占 28531 字符，把 Introduction/Problem Statement 全裹进去）。
    修法是标题**压平**（去空格标点后小写）再与规范名做子串比对。
    """
    text = f"{heading}\n{_BODY}\n"
    assert expected in _sections(text), f"标题 {heading!r} 未被识别为 {expected}"


def test_subsection_inherits_parent_label():
    """带点子节未命中规范名时，应继承父章节标签。"""
    text = (
        "4 O UR METHOD\n" + _BODY + "\n"
        "4.1 L OW-R ANK -PARAMETRIZED UPDATE MATRICES\n" + _BODY + "\n"
        "4.2 A PPLYING LORA TO TRANSFORMER\n" + _BODY + "\n"
    )
    sections = _sections(text)
    assert sections == {"method"}, f"父子节应统一为 method，实际 {sections}"


def test_unrecognized_toplevel_section_does_not_inherit_previous_label():
    """🔴 回归：技术命名的顶层章节**不得**沿用上一节标签。

    实测 QLoRA 的 "3 QLoRA Finetuning"（方法章节，以技术命名，任何规范词表都盖不住）
    曾让后续 133 个分块全部被标成 introduction。正确行为是标 unknown —— 不准确，
    但**不撒谎**。
    """
    text = (
        "1 Introduction\n" + _BODY + "\n"
        "2 Background\n" + _BODY + "\n"
        "3 QLoRA Finetuning\n" + _BODY + "\n"
    )
    sections = _sections(text)
    assert "introduction" in sections      # 前两节仍然正确
    assert "unknown" in sections, "技术命名的顶层章节应标 unknown，而不是沿用 introduction"


@pytest.mark.parametrize(
    "junk_line",
    [
        "175 billion trainable parameters.1",   # 小写开头 + 含句号
        "2 of the first quantization",          # 小写开头
        "1 . We use 8-bit Floats",              # 以句号开头
        "6 7 8 9 10 11",                        # 非字母开头
        "2101.00121 arXiv: 2101.00121.",        # 含句号（参考文献行）
    ],
)
def test_body_lines_are_not_treated_as_headings(junk_line):
    """正文行/表格行不得被误判成章节边界（否则会把正文切碎并标成 unknown）。"""
    text = (
        "4 O UR METHOD\n" + _BODY + "\n"
        f"{junk_line}\n" + _BODY + "\n"
    )
    # 该行若被当边界，会出现 unknown；不应发生
    assert _sections(text) == {"method"}, (
        f"正文行 {junk_line!r} 被误判为章节边界"
    )
