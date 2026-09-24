"""summarizer 的 method 抽取测试（2026-09-24 重写后新增）。

背景：
    · 命中率：原实现只在 `method` section 里找，而论文的方法章节常以技术命名
      （"3 QLoRA Finetuning"、"4 Direct Preference Optimization"），规范章节名盖不住
      → 实测 10 篇里 8 篇 method 为空。加了"全篇回落"后 10/10 有值。
    · 质量：只按关键词取句会把附录提示词模板、公式碎片当成方法描述
      （实测 DPO 抽到 "Response B: <the other response>"）。加 `_is_prose_like` 闸门。
"""

from __future__ import annotations

import pytest

from app.research.paper_agent.summarizer import _extract_method, _is_prose_like


def _chunk(text: str, section: str = "method") -> dict:
    """造一个 PaperChunk（字段与 schema 对齐）。"""
    return {
        "chunk_id": f"c-{abs(hash(text)) % 10**6}",
        "paper_id": "p1",
        "section": section,
        "page": 1,
        "text": text,
        "token_count": len(text) // 4,
    }


# ============================================================
# _is_prose_like：质量闸门
# ============================================================

@pytest.mark.parametrize(
    "text",
    [
        "Response B:",                                      # 提示词模板（太短）
        "<the other response>",                             # 模板占位符 + 太短
        "SFT q,o~P sft(Q,O) - 1 RFT q~P sft(Q),o~π sft(O|q)",  # 公式碎片（无空格、符号多）
        "We propose X.",                                    # 太短
        "| Method | Acc |",                                 # 表格残留
    ],
)
def test_prose_gate_rejects_non_prose(text):
    """模板/公式/表格残留必须被挡掉（宁可返回空，不返回垃圾）。"""
    assert not _is_prose_like(text), f"应被拒绝：{text!r}"


@pytest.mark.parametrize(
    "text",
    [
        "We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained "
        "model weights and injects trainable rank decomposition matrices.",
        "In this work, we develop and release Llama 2, a collection of pretrained "
        "and fine-tuned large language models ranging from 7 to 70 billion parameters.",
    ],
)
def test_prose_gate_accepts_real_method_sentences(text):
    assert _is_prose_like(text), f"应被接受：{text[:50]!r}"


# ============================================================
# _extract_method：三级策略
# ============================================================

def test_method_prefers_method_section():
    """有 method section 且含合格句 → 直接用，不去扫全篇。"""
    sections = {"method": [_chunk("We propose a simple and effective method for adaptation.")]}
    all_chunks = [_chunk("We propose something much worse in the appendix section.", "conclusion")]

    out = _extract_method(sections, all_chunks)

    assert "simple and effective method" in out


def test_method_falls_back_to_all_chunks_when_no_method_section():
    """🔴 回归：无 method section 时必须全篇回落。

    这是命中率从 2/10 提到 10/10 的关键 —— 方法章节以技术命名时（如
    "3 QLoRA Finetuning"），`sections["method"]` 是空的。
    """
    sections = {"introduction": [_chunk("Intro text about the problem.", "introduction")]}
    all_chunks = [
        _chunk("Introduction text that is long enough to look like prose here.", "introduction"),
        _chunk(
            "We present QLoRA, an efficient finetuning approach that reduces memory "
            "usage enough to finetune a 65B parameter model on a single GPU.",
            "unknown",
        ),
    ]

    out = _extract_method(sections, all_chunks)

    assert "QLoRA" in out, f"应回落到全篇扫描并找到 QLoRA 句，实际 {out!r}"


def test_method_skips_junk_then_uses_next_candidate():
    """闸门生效：模板句被跳过后，应继续找下一个合格句。"""
    sections = {
        "method": [
            _chunk("Response B: FIRST provide a one-sentence comparison."),
            _chunk(
                "In this paper we introduce a new parameterization of the reward model "
                "that enables extraction of the optimal policy in closed form."
            ),
        ]
    }

    out = _extract_method(sections, sections["method"])

    assert "parameterization" in out
    assert "Response B" not in out


def test_method_returns_empty_when_nothing_qualifies():
    """全无合格句 → 返回空串（不足 40 字符的碎片也不算）。"""
    sections = {"method": [_chunk("We propose X.")]}
    assert _extract_method(sections, sections["method"]) == ""


def test_method_caps_length_at_300():
    """超长句截断到 300 字符（与既有契约一致）。"""
    long_sentence = "We propose " + ("a very detailed mechanism " * 40) + "."
    sections = {"method": [_chunk(long_sentence)]}
    assert len(_extract_method(sections, sections["method"])) <= 300
