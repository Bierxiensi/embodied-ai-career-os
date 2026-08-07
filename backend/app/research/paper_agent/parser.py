"""论文解析器：文件 → 文本 + 元数据。

支持格式（按扩展名分发）：
    - .pdf  → pypdf 提取文本 + 页码
    - .md   → 直接读 + frontmatter 解析
    - .txt  → 直接读

设计要点：
- 策略模式：按扩展名分发，新增格式只加一个 _parse_xxx
- PDF 解析失败降级：pypdf 抽不出文本时返回空文本 + warning，不抛异常
    （扫描版论文兜底，避免阻塞后续 chunker / summarizer）
- 元数据统一：无论哪种格式都返回 (text, PaperMeta)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.research.paper_agent.schema import PaperMeta

# arxiv ID 正则（如 2407.01827 或 2407.01827v1）
_ARXIV_ID_PATTERN = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?)")


def parse(file_path: str) -> tuple[str, PaperMeta]:
    """解析论文文件，返回文本 + 元数据。

    Args:
        file_path: 论文文件路径（PDF / MD / TXT）

    Returns:
        (text, meta) 元组。text 为提取的纯文本，meta 含来源信息。

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件类型
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"论文文件不存在: {file_path}")

    suffix = path.suffix.lower().lstrip(".")
    if suffix == "pdf":
        return _parse_pdf(path)
    elif suffix == "md":
        return _parse_markdown(path)
    elif suffix == "txt":
        return _parse_text(path)
    else:
        raise ValueError(
            f"不支持的文件类型: .{suffix}（仅支持 pdf / md / txt）"
        )


def _parse_pdf(path: Path) -> tuple[str, PaperMeta]:
    """解析 PDF：逐页提取文本，记录页码。

    依赖 pypdf（纯 Python，无系统级依赖）。
    解析失败时降级返回空文本，不抛异常（兼容扫描版 PDF）。
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError(
            "解析 PDF 需要 pypdf，请安装: pip install pypdf"
        )

    reader = PdfReader(str(path))
    page_texts: list[str] = []
    for page in reader.pages:
        # extract_text 返回空字符串表示该页无文本层（扫描版）
        page_texts.append(page.extract_text() or "")

    text = "\n\n".join(page_texts)

    # 从文件名提取 arxiv ID（如 2407.01827.pdf）
    arxiv_id = _extract_arxiv_id(path.name)

    # 标题线索：文件名去扩展名 + 去版本号
    title_hint = path.stem
    if arxiv_id:
        title_hint = re.sub(r"v\d+$", "", title_hint.replace(arxiv_id, "")).strip(" -_")

    meta: PaperMeta = {
        "source_path": str(path),
        "file_type": "pdf",
        "page_count": len(reader.pages),
        "title_hint": title_hint or path.stem,
        "arxiv_id": arxiv_id,
    }
    return text, meta


def _parse_markdown(path: Path) -> tuple[str, PaperMeta]:
    """解析 Markdown：直接读取，剥离 frontmatter。"""
    raw = path.read_text(encoding="utf-8", errors="replace")

    # 剥离 YAML frontmatter（--- ... ---）
    text = raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            text = raw[end + 4:].lstrip("\n")

    meta: PaperMeta = {
        "source_path": str(path),
        "file_type": "md",
        "page_count": 1,
        "title_hint": _extract_title_from_md(raw) or path.stem,
        "arxiv_id": _extract_arxiv_id(path.name),
    }
    return text, meta


def _parse_text(path: Path) -> tuple[str, PaperMeta]:
    """解析 TXT：直接读取。"""
    text = path.read_text(encoding="utf-8", errors="replace")

    # 标题线索：首行非空内容（去除常见前缀）
    first_line = ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            first_line = line
            break

    meta: PaperMeta = {
        "source_path": str(path),
        "file_type": "txt",
        "page_count": 1,
        "title_hint": first_line[:80] or path.stem,
        "arxiv_id": _extract_arxiv_id(path.name),
    }
    return text, meta


def _extract_arxiv_id(filename: str) -> str:
    """从文件名提取 arxiv ID。"""
    match = _ARXIV_ID_PATTERN.search(filename)
    return match.group(1) if match else ""


def _extract_title_from_md(content: str) -> str:
    """从 Markdown 提取首个 H1 标题。"""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""
