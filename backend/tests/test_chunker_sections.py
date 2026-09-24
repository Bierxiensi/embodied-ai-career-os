"""分节器回归测试：学术 PDF 常见的"无点编号标题"必须能识别。

背景（2026-09-23 实测缺陷）：
    论文 PDF 经 pypdf 抽出的标题形态是 `1 Introduction` / `6 Experiments`
    （数字后**没有点**，这是学术排版常态）。原实现的两处不一致：
      · _SECTION_PATTERNS 允许无点编号（`\\d+\\.?\\s*`）
      · 但剥编号的正则 `^[\\dIVXLC]+\\.\\s*` **要求必须有点**
    → 无点标题被匹配到却剥不掉编号 → _normalize_section("1 introduction") = unknown
    → 被 `continue` 丢弃。后果：整篇 PDF 只剩无编号的 "Abstract"，
      其 section 一直延伸到文末，滑窗切成 N 块全部标成 abstract
      （实测 DPO 论文 147 块里 146 块是 abstract，method 永远为空）。

本文件同时守住修复时**刻意避开的一个坑**：
    若把剥编号写成 `(?:\d+|[IVXLC]+)\\.?`（点可选、无空白要求），
    则首字母落在罗马数字集里的标题会被吃掉 —— "Introduction" 的 I、
    "Conclusion" 的 C（C=100）、"Methods" 的 M 不受影响但 C/I/V/X/L 会。
    正确写法用 `\\s+` 兜底，逼出"编号后必须有空白"，从而不误伤。
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
    """回归坑：剥编号正则不得吃掉首字母为 I/V/X/L/C 的标题。

    "Conclusion" 的 C、"Introduction" 的 I 都在 [IVXLC] 里；
    若剥编号写成 `(?:\d+|[IVXLC]+)\\.?\\s*`（\s* 允许零空白），标题会被截成
    "onclusion" / "ntroduction" → 变成 unknown。必须用 `\\s+` 逼出空白分隔。
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
