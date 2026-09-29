"""Teach-Back 判定（Learn FASTER 机制，spec §3.2/§4.2）。

纪律：LLM 优先判对错，规则关键词兜底；Mock 不参与判定（直接走规则）。
判定只输出布尔——**不改写用户口述**，日志内容永远是用户原话。
"""

from __future__ import annotations


def _is_mock() -> bool:
    from app.llm import get_llm

    return type(get_llm()).__name__ == "MockClient"


def judge_answer(question: str, reference: str, spoken: str) -> bool:
    text = (spoken or "").strip().lower()
    ref = (reference or "").strip().lower()
    if not text or not ref:
        return False

    if not _is_mock():
        try:
            from app.llm import ChatMessage, get_llm

            llm = get_llm()
            result = llm.chat_json([
                ChatMessage(role="system", content="你是口述判分器。只输出 JSON。"),
                ChatMessage(
                    role="user",
                    content=(
                        f"问题：{question}\n参考答案：{reference}\n用户口述：{spoken}\n"
                        '判断口述是否覆盖参考答案核心点。返回 {"passed": true/false}'
                    ),
                ),
            ])
            if isinstance(result, dict) and "passed" in result:
                return bool(result["passed"])
        except Exception:
            pass

    # 规则兜底：参考答案核心词被口述覆盖 ≥ 一半即通过
    keywords = [w for w in ref.replace("/", " ").split() if len(w) >= 2]
    if not keywords:
        return False
    hits = sum(1 for w in keywords if w in text)
    return hits >= max(1, (len(keywords) + 1) // 2)
