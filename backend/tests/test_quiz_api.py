"""小测验端点测试（``/api/interview/quiz/start`` 与 ``/api/interview/quiz/{id}/result``）。

背景
----
这两个端点此前**零测试覆盖**：整套 quiz 能力（约 250 行，含"用 LLM 把一道题
改写成 choice/judge/fill 变体"）长期没有任何前端入口，所以也没人验证过它。
2026-09-22 把它接上题库页时补上本文件。

覆盖
----
  A. ``_keyword_score`` 的 choice 判分容错（纯函数）
  B. 无真实 LLM（默认 MockClient）时的**降级契约**：
     题型必须诚实退化成 open，不得标着 choice/judge 却不给选项
  C. 配置真实 LLM（测试里用假 LLM）时的生成契约：
     变体题型、选项、真实答案都要落库，且**真实答案不得随响应下发**
  D. 判分必须回查该会话下发的题（生成题的真实答案只存在 quiz_session_questions）
  E. 结果聚合与 404 分支

隔离
----
由 ``tests/conftest.py`` 提供会话级临时库。本文件用**独占 skill_name**
把抽题池限制在自己造的题上，测完删除自己造的题与记录。绝不碰开发库。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.practice import _keyword_score, _same_answer
from app.db.base import SessionLocal
from app.main import app
from app.models.interview_question import InterviewQuestion
from app.models.practice_record import PracticeRecord
from app.models.quiz_question import QuizSessionQuestion

client = TestClient(app)


# ============================================================
# 造题 / 清理
# ============================================================


def _make_questions(n: int, skill: str, category: str = "LLM") -> list[int]:
    """建 n 道题并把抽题池限制在 ``skill`` 上，返回题目 id。"""

    ids = []
    for i in range(n):
        resp = client.post(
            "/api/interview-questions",
            json={
                "category": category,
                "question": f"quiz 测试题 {skill} #{i}：Transformer 的注意力怎么算？",
                "skill_name": skill,
                "source_day_seq": 1,
                "answer_outline": "要点一：QKV 计算\n要点二：KV Cache 缓存历史",
            },
        )
        assert resp.status_code == 200, resp.text
        ids.append(resp.json()["data"]["id"])
    return ids


def _cleanup(question_ids: list[int], session_ids: list[str]) -> None:
    """按外键依赖顺序清理：练习记录 → 会话题目 → 题目。"""

    db = SessionLocal()
    try:
        db.query(PracticeRecord).filter(
            PracticeRecord.question_id.in_(question_ids)
        ).delete(synchronize_session=False)
        db.query(QuizSessionQuestion).filter(
            QuizSessionQuestion.session_id.in_(session_ids)
        ).delete(synchronize_session=False)
        db.query(InterviewQuestion).filter(
            InterviewQuestion.id.in_(question_ids)
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def bank():
    """独占一个 skill 的题池，用完清掉（含会话与练习记录）。"""

    skill = f"QUIZTEST_{uuid.uuid4().hex[:8]}"
    ids = _make_questions(4, skill)
    sessions: list[str] = []
    try:
        yield skill, ids, sessions
    finally:
        _cleanup(ids, sessions)


# ============================================================
# 假 LLM
# ============================================================


class _FakeLLM:
    """按 prompt 内容分别返回「出题」与「判分」JSON，并记录收到的 prompt。"""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    @property
    def model_name(self) -> str:
        return "fake-llm"

    def chat(self, messages) -> str:  # pragma: no cover - chat_json 已覆盖
        return "{}"

    def chat_json(self, messages, output_schema=None) -> dict:
        text = "\n".join(m.content for m in messages)
        self.prompts.append(text)

        if "出题专家" in text:
            if "一道choice题" in text:
                return {
                    "question": "假选择题：KV Cache 的主要作用是？",
                    "correct_answer": "B",
                    "options": [
                        "A. 加速反向传播",
                        "B. 缓存历史 K/V 以避免重复计算",
                        "C. 压缩模型权重",
                        "D. 做数据增强",
                    ],
                }
            if "一道judge题" in text:
                return {
                    "question": "假判断题：KV Cache 会缓存历史 token 的 K 与 V。",
                    "correct_answer": "正确",
                    "options": ["正确", "错误"],
                }
            if "一道fill题" in text:
                return {
                    "question": "KV Cache 缓存的是历史 token 的 ___。",
                    "correct_answer": "K/V",
                    "options": None,
                }

        # 判分 prompt
        return {
            "correct": True,
            "score": 100,
            "feedback": "假判分",
            "correct_answer": "B",
            "outline_covered": [],
            "outline_missed": [],
        }


def _patched_llm(monkeypatch) -> _FakeLLM:
    """把 ``get_llm`` 换成假 LLM。

    注意：practice.py 在函数内部 `from app.llm import get_llm`，
    是**调用时**才解析模块属性，所以 patch ``app.llm.get_llm`` 即生效。
    """

    fake = _FakeLLM()
    monkeypatch.setattr("app.llm.get_llm", lambda: fake)
    return fake


# ============================================================
# A. 纯函数：choice 判分容错
# ============================================================


def test_same_answer_tolerates_letter_vs_full_option_text():
    """前端回传字母 "B"，LLM 可能回 "B" 或完整选项文本 —— 两者都该判对。"""

    assert _same_answer("B", "B")
    assert _same_answer("b", "B")
    assert _same_answer("B", "B. 缓存历史 K/V")
    assert _same_answer("B. 缓存历史 K/V", "B")
    assert not _same_answer("A", "B")
    # 普通文本不应被当成选项字母误判
    assert not _same_answer("attention", "a")
    assert not _same_answer("B", "键值缓存")


def test_keyword_score_choice_uses_correct_answer():
    """有正确答案时走全等/字母比对，而不是退到要点覆盖率。"""

    ok = _keyword_score(None, "choice", "B", "B. 缓存历史 K/V")
    assert ok["correct"] is True and ok["score"] == 100

    bad = _keyword_score(None, "choice", "A", "B")
    assert bad["correct"] is False and bad["score"] == 0


# ============================================================
# B. 降级契约（无真实 LLM）
# ============================================================


def test_start_degrades_to_open_when_llm_unavailable(bank):
    """MockClient 下题型必须诚实退化成 open。

    此前 `_generate_question_type` 直接 return `llm.chat_json(...)`，
    把 ``{"_parse_error": True}`` 当成功结果 → 题目标着 choice/judge/fill
    却没有选项，前端标题写「单选题」实际渲染简答框。
    """

    skill, _ids, sessions = bank

    resp = client.post("/api/interview/quiz/start", json={"skill_name": skill, "count": 4})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    sessions.append(data["session_id"])

    assert data["count"] == 4
    for q in data["questions"]:
        assert q["question_type"] == "open", f"未降级：{q}"
        assert q["options"] is None
        assert "correct_answer" not in q, "真实答案不得随响应下发"


def test_start_persists_every_question_it_hands_out(bank):
    """下发的每道题都要落库，且行数一致（否则判分回查不到）。"""

    skill, _ids, sessions = bank

    data = client.post(
        "/api/interview/quiz/start", json={"skill_name": skill, "count": 3}
    ).json()["data"]
    sid = data["session_id"]
    sessions.append(sid)

    db = SessionLocal()
    try:
        rows = (
            db.query(QuizSessionQuestion)
            .filter(QuizSessionQuestion.session_id == sid)
            .order_by(QuizSessionQuestion.position)
            .all()
        )
    finally:
        db.close()

    assert len(rows) == data["count"] == 3
    assert [r.position for r in rows] == [0, 1, 2]
    assert {r.question_type for r in rows} == {"open"}
    assert {r.question for r in rows} == {q["question"] for q in data["questions"]}


def test_start_with_unknown_skill_returns_404(bank):
    resp = client.post(
        "/api/interview/quiz/start", json={"skill_name": "NO_SUCH_SKILL_XYZ", "count": 3}
    )
    assert resp.status_code == 404


# ============================================================
# C/D. 有真实 LLM 时的生成契约与判分回查
# ============================================================


def test_start_generates_variants_and_persists_answers(bank, monkeypatch):
    """有 LLM 时：choice/judge/fill 变体 + 选项 + 真实答案都要落库。

    count=3 的题型分配是 choice / judge / fill（各 1 道）。
    """

    skill, _ids, sessions = bank
    _patched_llm(monkeypatch)

    data = client.post(
        "/api/interview/quiz/start", json={"skill_name": skill, "count": 3}
    ).json()["data"]
    sid = data["session_id"]
    sessions.append(sid)

    assert [q["question_type"] for q in data["questions"]] == ["choice", "judge", "fill"]
    # 选项随题下发（作答要用），真实答案不下发
    assert data["questions"][0]["options"][1].startswith("B.")
    assert data["questions"][1]["options"] == ["正确", "错误"]
    for q in data["questions"]:
        assert "correct_answer" not in q

    db = SessionLocal()
    try:
        rows = (
            db.query(QuizSessionQuestion)
            .filter(QuizSessionQuestion.session_id == sid)
            .order_by(QuizSessionQuestion.position)
            .all()
        )
    finally:
        db.close()

    assert [r.question_type for r in rows] == ["choice", "judge", "fill"]
    assert [r.correct_answer for r in rows] == ["B", "正确", "K/V"]
    assert rows[0].option_list()[1].startswith("B.")
    # fill 题没有选项
    assert rows[2].option_list() is None


def test_answer_uses_persisted_answer_for_generated_question(bank, monkeypatch):
    """判分必须回查该会话下发的题 —— 生成题的真实答案只存在库表里。

    做法：捕获假 LLM 收到的 prompt，断言里面出现了库中存的正确答案。
    若没回查，(生成题) 题库原题的 options 为 NULL → prompt 里不会有「正确答案」。
    """

    skill, _ids, sessions = bank
    fake = _patched_llm(monkeypatch)

    data = client.post(
        "/api/interview/quiz/start", json={"skill_name": skill, "count": 1}
    ).json()["data"]
    sid = data["session_id"]
    sessions.append(sid)

    q = data["questions"][0]
    assert q["question_type"] == "choice"  # count=1 → 定额给 choice

    resp = client.post(
        "/api/interview/practice",
        json={
            "question_id": q["id"],
            "question_type": q["question_type"],
            "user_answer": "B",
            "generated_options": q["options"],
            "skill_name": skill,
            "mode": "quiz",
            "session_id": sid,
        },
    )
    assert resp.status_code == 200, resp.text

    scoring_prompts = [p for p in fake.prompts if "面试评分专家" in p]
    assert scoring_prompts, "判分 prompt 未被捕获"
    assert "正确答案：B" in scoring_prompts[-1], "判分时没有带上生成题的真实答案"

    # 题目题干也应是「本次下发的变体」，不是题库原题
    assert "假选择题" in scoring_prompts[-1]


def test_answer_without_session_falls_back_to_bank_options(bank, monkeypatch):
    """单题练习（mode=single）不受会话回查影响，仍走题库原题的答案。"""

    skill, ids, _sessions = bank
    _patched_llm(monkeypatch)

    resp = client.post(
        "/api/interview/practice",
        json={
            "question_id": ids[0],
            "question_type": "open",
            "user_answer": "QKV 计算，KV Cache 缓存历史",
            "skill_name": skill,
            "mode": "single",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["score"] == 100


# ============================================================
# E. 结果聚合 / 404
# ============================================================


def test_result_aggregates_and_unknown_session_is_404(bank):
    skill, _ids, sessions = bank

    data = client.post(
        "/api/interview/quiz/start", json={"skill_name": skill, "count": 2}
    ).json()["data"]
    sid = data["session_id"]
    sessions.append(sid)

    for q in data["questions"]:
        r = client.post(
            "/api/interview/practice",
            json={
                "question_id": q["id"],
                "question_type": q["question_type"],
                "user_answer": "QKV 计算",
                "skill_name": skill,
                "mode": "quiz",
                "session_id": sid,
            },
        )
        assert r.status_code == 200, r.text

    res = client.get(f"/api/interview/quiz/{sid}/result")
    assert res.status_code == 200, res.text
    out = res.json()["data"]

    assert out["session_id"] == sid
    assert out["count"] == 2
    assert len(out["records"]) == 2
    assert out["by_type"]["open"]["count"] == 2
    assert out["correct_count"] == sum(1 for r in out["records"] if r["correct"])
    # 每道题的题干与用户答案都要能对上
    assert {r["question_id"] for r in out["records"]} == {q["id"] for q in data["questions"]}
    assert all(r["user_answer"] == "QKV 计算" for r in out["records"])

    miss = client.get("/api/interview/quiz/quiz_nope/result")
    assert miss.status_code == 404
