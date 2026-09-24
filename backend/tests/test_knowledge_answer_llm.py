"""知识库组答的 LLM 路径测试（2026-09-23 接通 LLM 后新增）。

契约（与 agents/research、agents/supervisor 的 `_xxx_with_llm` 同款）：
    LLM 可用 → 成句回答，answer_mode="llm"
    LLM 不可用（未配置 provider / 调用异常 / 返回空）→ 回落片段拼接，answer_mode="rule"

⚠️ 本文件**不依赖** `.env` 的 provider（conftest 已钉死 mock）。
   需要"真实 LLM 可用"的场景，一律 monkeypatch `app.llm.get_llm`，
   因为 `nodes.py` 是在函数体内 `from app.llm import get_llm`，故 patch 模块属性即可生效。
"""

from __future__ import annotations

import pytest

import app.llm as llm_pkg
from app.agents.knowledge.nodes import answer_node
from app.llm.providers import MockClient

CHUNKS = [
    {
        "chunk_id": "c1", "paper_id": "p1", "paper_title": "ACT Paper",
        "section": "method", "page": 2, "score": 0.8,
        "text": "We propose ACT, a CVAE transformer for action chunking.",
    },
    {
        "chunk_id": "c2", "paper_id": "p1", "paper_title": "ACT Paper",
        "section": "experiment", "page": 5, "score": 0.6,
        "text": "ACT achieves 80% success on the task suite.",
    },
]


class _FakeLLM:
    """非 MockClient 的假 LLM：返回固定成句回答。"""

    def __init__(self, reply: str = "ACT 是一种基于 CVAE 的动作分块方法。") -> None:
        self._reply = reply
        self.calls: list[list] = []

    @property
    def model_name(self) -> str:
        return "fake-llm"

    def chat(self, messages):
        self.calls.append(messages)
        return self._reply


class _EmptyLLM(_FakeLLM):
    def __init__(self) -> None:
        super().__init__(reply="")


class _RaisingLLM(_FakeLLM):
    def chat(self, messages):  # noqa: D102
        raise RuntimeError("upstream 503")


@pytest.fixture(autouse=True)
def _restore_get_llm():
    """用例改了 app.llm.get_llm 后必须还原（同文件其他用例会依赖原值）。"""
    original = llm_pkg.get_llm
    yield
    llm_pkg.get_llm = original


# ============================================================
# LLM 路径
# ============================================================

def test_llm_path_returns_sentence_answer(monkeypatch):
    """有真 LLM → 用 LLM 的成句回答，且 answer_mode 标为 llm。"""
    fake = _FakeLLM()
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: fake)

    ans = answer_node({"question": "what is ACT", "retrieved_chunks": CHUNKS})["answer"]

    assert ans["answer_mode"] == "llm"
    assert ans["answer"] == "ACT 是一种基于 CVAE 的动作分块方法。"
    # 不再是片段堆叠
    assert "[method]" not in ans["answer"]
    assert len(fake.calls) == 1, "应恰好调用一次 LLM"


def test_llm_receives_retrieved_context(monkeypatch):
    """喂给 LLM 的 prompt 必须含检索到的原文（保证 grounded，不是凭空作答）。"""
    fake = _FakeLLM()
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: fake)

    answer_node({"question": "what is ACT", "retrieved_chunks": CHUNKS})

    user_msg = [m for m in fake.calls[0] if m.role == "user"][0]
    assert "action chunking" in user_msg.content, "prompt 应含检索原文"
    assert "what is ACT" in user_msg.content, "prompt 应含用户问题"
    sys_msg = [m for m in fake.calls[0] if m.role == "system"][0]
    assert "资料中未提及" in sys_msg.content, "system 应约束不得臆造"


def test_citations_are_identical_in_both_modes(monkeypatch):
    """引用恒来自检索结果（可追溯），不因走 LLM 而改变。"""
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: _FakeLLM())
    llm_ans = answer_node({"question": "q", "retrieved_chunks": CHUNKS})["answer"]

    monkeypatch.setattr(llm_pkg, "get_llm", lambda: MockClient())
    rule_ans = answer_node({"question": "q", "retrieved_chunks": CHUNKS})["answer"]

    assert llm_ans["citations"] == rule_ans["citations"]
    assert [c["chunk_id"] for c in llm_ans["citations"]] == ["c1", "c2"]
    assert llm_ans["hit_count"] == rule_ans["hit_count"] == 2
    # 置信度恒基于检索质量，与组答方式无关
    assert llm_ans["confidence"] == rule_ans["confidence"]


# ============================================================
# 回落路径
# ============================================================

def test_mock_client_falls_back_to_rule(monkeypatch):
    """未配置真实 provider（拿到 MockClient）→ 必须回落规则拼接。

    Mock 的固定模板文案（"Mock LLM 回复：…"）绝不能当成知识库答案返回给用户。
    """
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: MockClient())

    ans = answer_node({"question": "what is ACT", "retrieved_chunks": CHUNKS})["answer"]

    assert ans["answer_mode"] == "rule"
    assert "Mock LLM" not in ans["answer"], "不得把 Mock 模板当答案"
    assert "action chunking" in ans["answer"], "应含检索原文"


def test_llm_exception_falls_back_to_rule_with_warning(monkeypatch):
    """LLM 抛异常 → 回落规则拼接 + 发 warning（不静默）。"""
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: _RaisingLLM())

    with pytest.warns(UserWarning, match="回落规则组答"):
        ans = answer_node({"question": "q", "retrieved_chunks": CHUNKS})["answer"]

    assert ans["answer_mode"] == "rule"
    assert "action chunking" in ans["answer"]


def test_empty_llm_reply_falls_back_to_rule(monkeypatch):
    """LLM 返回空串 → 回落规则拼接（不允许返回空答案）。"""
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: _EmptyLLM())

    ans = answer_node({"question": "q", "retrieved_chunks": CHUNKS})["answer"]

    assert ans["answer_mode"] == "rule"
    assert ans["answer"], "答案不得为空"


def test_get_llm_raising_at_construction_falls_back(monkeypatch):
    """连客户端都构造不出来 → 同样回落，不得抛给调用方。"""
    def _boom():
        raise ValueError("未知 LLM_PROVIDER")

    monkeypatch.setattr(llm_pkg, "get_llm", _boom)

    with pytest.warns(UserWarning):
        ans = answer_node({"question": "q", "retrieved_chunks": CHUNKS})["answer"]

    assert ans["answer_mode"] == "rule"


# ============================================================
# 无命中（两路都不走）
# ============================================================

def test_no_hits_short_circuits_without_calling_llm(monkeypatch):
    """无检索命中时不得调用 LLM（省一次无意义的往返），直接给兜底文案。"""
    fake = _FakeLLM()
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: fake)

    ans = answer_node({"question": "q", "retrieved_chunks": []})["answer"]

    assert ans["hit_count"] == 0
    assert ans["confidence"] == "low"
    assert ans["answer_mode"] == "rule"
    assert "未在知识库" in ans["answer"]
    assert fake.calls == [], "无命中不应调用 LLM"


# ============================================================
# 置信度标定（2026-09-23 修 bug 后新增）
# ============================================================

def _chunks_with_top_score(score: float, n: int = 5) -> list[dict]:
    """造 n 条命中，最高分 = score。"""
    return [
        {
            "chunk_id": f"c{i}", "paper_id": "p1", "paper_title": "T",
            "section": "abstract", "page": 1,
            "score": score if i == 0 else score * 0.9,
            "text": f"chunk number {i}",
        }
        for i in range(n)
    ]


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.75, "high"),    # 相关问题的实测区间上沿
        (0.50, "high"),    # 阈值边界（含）
        (0.45, "medium"),
        (0.35, "medium"),  # 阈值边界（含）
        (0.34, "low"),
        (0.20, "low"),     # 语料外问题的实测区间
    ],
)
def test_confidence_follows_top_score(monkeypatch, score, expected):
    """置信度只由 top score 决定，阈值 0.50 / 0.35。"""
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: MockClient())

    ans = answer_node({"question": "q", "retrieved_chunks": _chunks_with_top_score(score)})["answer"]

    assert ans["confidence"] == expected, f"score={score} 应 {expected}"


def test_many_low_score_hits_are_not_high(monkeypatch):
    """🔴 回归：命中条数多**不能**把置信度抬成 high。

    原实现是 `if top_score >= 0.35 or len(chunks) >= 3: high` ——
    检索总是返回 top_k 条（默认 5），故 `len(chunks) >= 3` 恒真，
    导致"如何修复 React 内存泄漏"这种语料外问题也报 high。此用例守住修复。
    """
    monkeypatch.setattr(llm_pkg, "get_llm", lambda: MockClient())

    ans = answer_node(
        {"question": "How do I fix a memory leak in React?",
         "retrieved_chunks": _chunks_with_top_score(0.21, n=10)}
    )["answer"]

    assert ans["hit_count"] == 10
    assert ans["confidence"] == "low", "命中多但分数低，必须 low"
