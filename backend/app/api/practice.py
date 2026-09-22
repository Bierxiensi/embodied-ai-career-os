"""题库练习 API（单题答题 + 小测验 + 练习统计）。

端点：
- POST /api/interview/practice          — 单题答题 + LLM 评分
- POST /api/interview/quiz/start        — 开始小测验
- GET  /api/interview/quiz/{id}/result  — 测验结果
- GET  /api/interview/practice/stats    — 练习总统计
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.base import get_db
from app.models.interview_question import InterviewQuestion
from app.models.practice_record import PracticeRecord
from app.models.quiz_question import QuizSessionQuestion
from app.schemas.practice import (
    PracticeIn,
    PracticeOut,
    PracticeSessionSummary,
    PracticeSkillStats,
    PracticeStatsOut,
    PracticeTypeStats,
    QuizQuestionOut,
    QuizRecordOut,
    QuizResultOut,
    QuizStartIn,
    QuizStartOut,
    QuizTypeStats,
)

router = APIRouter(prefix="/interview", tags=["practice"])


# ─── LLM 评分 ───────────────────────────────────────────────


# 形如「A」「A.」「A、」「A)」的选项字母；用于 choice 题的容错比对
_OPTION_LETTER = re.compile(r"^([a-d])(?:[.\u3001\uff0e)\uff09:]|\s|$)")


def _same_answer(user_answer: str, correct_answer: str) -> bool:
    """choice / judge 题的答案比对（全等 or 选项字母一致）。

    为什么要容错：前端 ChoiceQuestion 回传的是**字母**（"A"），而 LLM 生成的
    ``correct_answer`` 有时是字母、有时是完整选项文本（"B. xxx"）。只做全等会
    把「同一个选项」判成错。仅在两边都形如选项字母时才退化到字母比对，
    避免把普通文本误判（例如正确答案是 "a"，用户答 "attention"）。
    """

    u = user_answer.strip().lower()
    c = correct_answer.strip().lower()
    if u == c:
        return True

    m_u = _OPTION_LETTER.match(u)
    m_c = _OPTION_LETTER.match(c)
    if m_u and m_c:
        return m_u.group(1) == m_c.group(1)
    return False


def _keyword_score(
    answer_outline: str | None,
    question_type: str,
    user_answer: str,
    correct_answer: str | None = None,
) -> dict:
    """关键词匹配降级评分（LLM 不可用时）。"""
    user_lower = user_answer.strip().lower()

    # 选择/判断题：精确匹配（choice 容忍「字母 ↔ 完整选项」两种写法）
    if question_type in ("choice", "judge") and correct_answer:
        is_correct = _same_answer(user_answer, correct_answer)
        return {
            "correct": is_correct,
            "score": 100 if is_correct else 0,
            "feedback": "答案正确" if is_correct else f"正确答案是 {correct_answer}",
            "correct_answer": correct_answer,
            "outline_covered": [] if not is_correct else ["答案匹配"],
            "outline_missed": ["答案匹配"] if not is_correct else [],
        }

    # 填空题：模糊包含
    if question_type == "fill" and correct_answer:
        is_correct = correct_answer.strip().lower() in user_lower or user_lower in correct_answer.strip().lower()
        return {
            "correct": is_correct,
            "score": 100 if is_correct else 0,
            "feedback": "答案正确" if is_correct else f"参考答案：{correct_answer}",
            "correct_answer": correct_answer,
            "outline_covered": [] if not is_correct else ["关键词匹配"],
            "outline_missed": ["关键词匹配"] if not is_correct else [],
        }

    # 开放题：按要点关键词覆盖率
    if answer_outline:
        # 按行/逗号/分号拆分要点
        points = re.split(r'[\n;；]', answer_outline)
        points = [p.strip().lstrip("0123456789.、").strip() for p in points if p.strip()]
        covered = [p for p in points if any(kw in user_lower for kw in p.lower().split()[:3] if len(kw) > 1)]
        missed = [p for p in points if p not in covered]
        ratio = len(covered) / len(points) if points else 0
        score = round(ratio * 100)
        return {
            "correct": score >= 60,
            "score": score,
            "feedback": f"覆盖了 {len(covered)}/{len(points)} 个要点" + ("（关键词匹配，接入 LLM 后更精确）" if True else ""),
            "correct_answer": answer_outline,
            "outline_covered": covered,
            "outline_missed": missed,
        }

    # 无参考答案
    return {
        "correct": False,
        "score": 0,
        "feedback": "无参考答案，无法评分",
        "correct_answer": "",
        "outline_covered": [],
        "outline_missed": [],
    }


def _llm_score(
    question: str,
    answer_outline: str | None,
    question_type: str,
    user_answer: str,
    correct_answer: str | None = None,
    options: list[str] | None = None,
) -> dict:
    """调用 LLM 评分，返回 {correct, score, feedback, outline_covered, outline_missed, correct_answer}。"""
    from app.llm import ChatMessage, get_llm

    outline_text = answer_outline or "（无参考答案）"
    options_text = ""
    if options:
        options_text = f"\n选项：{json.dumps(options, ensure_ascii=False)}"
    if correct_answer:
        options_text += f"\n正确答案：{correct_answer}"

    prompt = f"""你是一位面试评分专家。评判用户对面试题的回答。

题目：{question}
题型：{question_type}
参考答案要点：{outline_text}{options_text}

用户答案：{user_answer}

评分标准：
- choice：用户选的选项与正确答案一致 → correct=true, score=100；不一致 → correct=false, score=0
- judge：用户判断与正确答案一致 → correct=true, score=100；不一致 → correct=false, score=0
- fill：语义等价 → correct=true, score=100；部分相关 → score=50；错误 → score=0
- open：按要点覆盖率评分（覆盖 N/M 个要点 → N/M * 100，四舍五入）

请严格返回 JSON（不要 markdown 代码块）：
{{"correct": true/false, "score": 0-100, "feedback": "一句话解释", "correct_answer": "正确答案文本", "outline_covered": ["覆盖的要点1"], "outline_missed": ["遗漏的要点1"]}}"""

    try:
        llm = get_llm()
        messages = [ChatMessage(role="user", content=prompt)]
        result = llm.chat_json(messages)

        # 如果 LLM 返回解析错误（如 mock provider），做关键词匹配降级
        if result.get("_parse_error"):
            return _keyword_score(answer_outline, question_type, user_answer, correct_answer)

        return {
            "correct": bool(result.get("correct", False)),
            "score": int(result.get("score", 0)),
            "feedback": str(result.get("feedback", "")),
            "correct_answer": str(result.get("correct_answer", correct_answer or "")),
            "outline_covered": result.get("outline_covered", []),
            "outline_missed": result.get("outline_missed", []),
        }
    except Exception as e:
        return _keyword_score(answer_outline, question_type, user_answer, correct_answer)


def _get_correct_answer_from_options(question: InterviewQuestion) -> str | None:
    """从题目手动配置的 options 中提取正确答案。"""
    if not question.options:
        return None
    try:
        parsed = json.loads(question.options)
        if isinstance(parsed, dict):
            return parsed.get("correct")
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _get_choices_from_options(question: InterviewQuestion) -> list[str] | None:
    """从题目手动配置的 options 中提取选项列表。"""
    if not question.options:
        return None
    try:
        parsed = json.loads(question.options)
        if isinstance(parsed, dict):
            return parsed.get("choices")
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ─── POST /api/interview/practice ────────────────────────────


@router.post("/practice")
def practice_answer(payload: PracticeIn, db: Session = Depends(get_db)):
    """单题答题 + LLM 评分。"""
    q = db.query(InterviewQuestion).filter(InterviewQuestion.id == payload.question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")

    # 确定正确答案和选项
    correct_answer = _get_correct_answer_from_options(q)
    choices = _get_choices_from_options(q)
    question_text = q.question

    # 测验模式：优先用「本次测验实际下发的那道题」。
    # 生成题（choice/judge/fill 变体）的真实答案只存在于 quiz_session_questions，
    # 不回查就只能拿到题库原题的 options（生成题恒为 NULL）→ 判分必错。
    if payload.mode == "quiz" and payload.session_id:
        quiz_q = (
            db.query(QuizSessionQuestion)
            .filter(
                QuizSessionQuestion.session_id == payload.session_id,
                QuizSessionQuestion.question_id == q.id,
            )
            .first()
        )
        if quiz_q is not None:
            question_text = quiz_q.question
            quiz_options = quiz_q.option_list()
            if quiz_options:
                choices = quiz_options
            if quiz_q.correct_answer:
                correct_answer = quiz_q.correct_answer

    # 如果有 LLM 生成的选项（前端回传）而库里没有，兜底用前端那份
    if payload.generated_options and not choices:
        choices = payload.generated_options

    # 调用 LLM 评分
    score_result = _llm_score(
        question=question_text,
        answer_outline=q.answer_outline,
        question_type=payload.question_type,
        user_answer=payload.user_answer,
        correct_answer=correct_answer,
        options=choices if payload.question_type == "choice" else None,
    )

    # 持久化记录
    record = PracticeRecord(
        question_id=q.id,
        question_type=payload.question_type,
        user_answer=payload.user_answer,
        correct_answer=score_result["correct_answer"],
        correct=score_result["correct"],
        score=score_result["score"],
        feedback=score_result["feedback"],
        outline_covered=json.dumps(score_result["outline_covered"], ensure_ascii=False),
        outline_missed=json.dumps(score_result["outline_missed"], ensure_ascii=False),
        skill_name=payload.skill_name or q.skill_name,
        mode=payload.mode,
        session_id=payload.session_id,
    )
    db.add(record)

    # 更新题目统计
    q.hit_count = (q.hit_count or 0) + 1
    if score_result["score"] >= 80 and not q.is_verified:
        q.is_verified = True

    db.commit()
    db.refresh(record)

    return ok(PracticeOut(
        correct=score_result["correct"],
        score=score_result["score"],
        max_score=100,
        feedback=score_result["feedback"],
        correct_answer=score_result["correct_answer"],
        outline_covered=score_result["outline_covered"],
        outline_missed=score_result["outline_missed"],
        record_id=record.id,
    ).model_dump(), "答题成功")


# ─── POST /api/interview/quiz/start ─────────────────────────


def _generate_question_type(
    question: str, answer_outline: str | None, target_type: str
) -> dict | None:
    """用 LLM 为一道题生成指定题型的内容。返回 {question, correct_answer, options} 或 None。"""
    from app.llm import ChatMessage, get_llm

    if target_type == "open":
        return None  # 开放题不需要生成

    outline_text = answer_outline or "（无参考答案）"

    type_instructions = {
        "choice": "生成 4 个选项（A/B/C/D），其中 1 个正确（来自 answer_outline），3 个有迷惑性但可排除。",
        "judge": "生成一个陈述句，50% 概率正确（直接来自要点），50% 概率错误（轻微篡改关键细节）。",
        "fill": "从 answer_outline 中选 1-2 个关键术语挖空，生成题目文本。",
    }

    prompt = f"""你是一位 AI 面试出题专家。根据以下面试题和参考答案，生成一道{target_type}题。

题目：{question}
参考答案要点：{outline_text}

要求：{type_instructions.get(target_type, "")}

请严格返回 JSON（不要 markdown 代码块）：
{{"question": "生成的题目文本", "correct_answer": "正确答案", "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"]}}

注意：
- judge 题的 options 固定为 ["正确", "错误"]
- fill 题的 options 为 null
- choice 题必须有 4 个选项"""

    try:
        llm = get_llm()
        messages = [ChatMessage(role="user", content=prompt)]
        result = llm.chat_json(messages)

        # ⚠️ LLM 未配置/不可用时（默认 MockClient）chat_json 返回
        # {"_parse_error": True, "raw": ...}。此前这里是 `return llm.chat_json(...)`，
        # 把这个 dict 当成**成功结果**返回 → 调用方 `if generated:` 恒真 →
        # 题目被打上 choice/judge/fill 标签却没有选项，前端标题写「单选题」
        # 实际渲染成简答框。生成失败必须显式返回 None，让调用方降级为 open。
        if not isinstance(result, dict) or result.get("_parse_error"):
            return None
        if not str(result.get("question") or "").strip():
            return None

        # judge 题的选项固定为「正确/错误」，模型偶尔会漏
        if target_type == "judge" and not result.get("options"):
            result["options"] = ["正确", "错误"]
        # choice 题没有选项就无法作答 → 视为生成失败（宁可降级成 open，也不下发错配的题）
        if target_type == "choice" and not result.get("options"):
            return None
        # fill 题拿不到答案就无法判分 → 同样降级
        if target_type == "fill" and not str(result.get("correct_answer") or "").strip():
            return None

        return result
    except Exception:
        return None


@router.post("/quiz/start")
def quiz_start(payload: QuizStartIn, db: Session = Depends(get_db)):
    """开始小测验：从题库抽题，为每道题生成指定题型。"""
    from app.agents.interview.engine import pick_questions

    # 查询题库转为 dict 列表（pick_questions 接收 list[dict]）
    query = db.query(InterviewQuestion)
    if payload.category:
        query = query.filter(InterviewQuestion.category == payload.category)
    if payload.skill_name:
        query = query.filter(InterviewQuestion.skill_name == payload.skill_name)
    all_questions = query.all()

    items = [
        {
            "id": q.id,
            "category": q.category,
            "question": q.question,
            "difficulty": q.difficulty,
            "hit_count": q.hit_count or 0,
            "skill_name": q.skill_name,
            "answer_outline": q.answer_outline,
        }
        for q in all_questions
    ]

    # 抽题
    picked_items = pick_questions(items, limit=payload.count)
    if not picked_items:
        raise HTTPException(status_code=404, detail="没有符合条件的题目")

    # 回查完整 ORM 对象
    picked_ids = [it["id"] for it in picked_items]
    questions = (
        db.query(InterviewQuestion)
        .filter(InterviewQuestion.id.in_(picked_ids))
        .all()
    )
    # 保持 pick_questions 的排序
    q_map = {q.id: q for q in questions}
    questions = [q_map[i] for i in picked_ids if i in q_map]
    if not questions:
        raise HTTPException(status_code=404, detail="没有符合条件的题目")

    session_id = f"quiz_{uuid.uuid4().hex[:12]}"

    # 题型分配：选择 30% + 判断 30% + 填空 20% + 开放 20%
    count = len(questions)
    type_plan = (
        ["choice"] * max(1, count * 3 // 10)
        + ["judge"] * max(1, count * 3 // 10)
        + ["fill"] * max(1, count * 2 // 10)
        + ["open"] * max(1, count * 2 // 10)
    )
    # 补齐或截断到实际数量
    while len(type_plan) < count:
        type_plan.append("choice")
    type_plan = type_plan[:count]

    quiz_questions: list[QuizQuestionOut] = []
    persisted: list[QuizSessionQuestion] = []

    def _emit(
        position: int,
        q: InterviewQuestion,
        qtype: str,
        text: str,
        options: list[str] | None,
        correct: str | None,
    ) -> None:
        """登记一道下发给用户的题：进响应体 + 进 quiz_session_questions。

        真实答案只进库、不进响应体 —— 所以前端拿不到"哪个选项是对的"。
        """
        quiz_questions.append(
            QuizQuestionOut(
                id=q.id,
                question=text,
                question_type=qtype,
                options=options,
                skill_name=q.skill_name,
                difficulty=q.difficulty,
            )
        )
        persisted.append(
            QuizSessionQuestion(
                session_id=session_id,
                question_id=q.id,
                question_type=qtype,
                question=text,
                options=QuizSessionQuestion.dump_options(options),
                correct_answer=correct,
                skill_name=q.skill_name,
                difficulty=q.difficulty,
                position=position,
            )
        )

    for position, (q, qtype) in enumerate(zip(questions, type_plan)):
        manual_choices = _get_choices_from_options(q)
        manual_correct = _get_correct_answer_from_options(q)

        if qtype == "open":
            # 开放题：判分时用题库原题的 answer_outline 做要点覆盖，无需另存答案
            _emit(position, q, "open", q.question, None, None)
            continue

        if manual_choices and q.question_type == qtype:
            # 题库里已手动配好选项的题，直接用原版（正确答案也在原题里）
            _emit(position, q, qtype, q.question, manual_choices, manual_correct)
            continue

        # LLM 动态生成题型变体
        generated = _generate_question_type(q.question, q.answer_outline, qtype)
        if generated:
            _emit(
                position,
                q,
                qtype,
                str(generated.get("question") or q.question),
                generated.get("options"),
                generated.get("correct_answer") or None,
            )
        else:
            # 降级：LLM 未配置/生成失败 → 退化成开放题。
            # 刻意**不保留原 qtype**：留着就会出现「标题写单选题、实际是简答框」的错配。
            _emit(position, q, "open", q.question, None, None)

    db.add_all(persisted)
    db.commit()

    return ok(QuizStartOut(
        session_id=session_id,
        questions=quiz_questions,
        count=len(quiz_questions),
    ).model_dump(), "测验开始")


# ─── GET /api/interview/quiz/{session_id}/result ─────────────


@router.get("/quiz/{session_id}/result")
def quiz_result(session_id: str, db: Session = Depends(get_db)):
    """获取小测验结果。"""
    records = (
        db.query(PracticeRecord)
        .filter(PracticeRecord.session_id == session_id)
        .order_by(PracticeRecord.created_at)
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail="测验记录不存在")

    # 题目信息
    question_ids = {r.question_id for r in records}
    questions = {
        q.id: q
        for q in db.query(InterviewQuestion).filter(InterviewQuestion.id.in_(question_ids)).all()
    }

    # 统计
    total_score = sum(r.score for r in records) / len(records) if records else 0
    correct_count = sum(1 for r in records if r.correct)

    by_type: dict[str, list[PracticeRecord]] = {}
    for r in records:
        by_type.setdefault(r.question_type, []).append(r)

    type_stats = {}
    for ttype, trecords in by_type.items():
        type_stats[ttype] = QuizTypeStats(
            count=len(trecords),
            correct=sum(1 for r in trecords if r.correct),
            avg_score=round(sum(r.score for r in trecords) / len(trecords), 1) if trecords else 0,
        )

    # 薄弱技能
    skill_scores: dict[str, list[int]] = {}
    for r in records:
        if r.skill_name:
            skill_scores.setdefault(r.skill_name, []).append(r.score)
    weak_skills = [
        skill
        for skill, scores in skill_scores.items()
        if sum(scores) / len(scores) < 50
    ]

    quiz_records = []
    for r in records:
        q = questions.get(r.question_id)
        quiz_records.append(
            QuizRecordOut(
                question_id=r.question_id,
                question_type=r.question_type,
                question=q.question if q else "",
                user_answer=r.user_answer,
                correct_answer=r.correct_answer,
                correct=r.correct,
                score=r.score,
                feedback=r.feedback,
            )
        )

    return ok(QuizResultOut(
        session_id=session_id,
        total_score=round(total_score, 1),
        count=len(records),
        correct_count=correct_count,
        by_type=type_stats,
        weak_skills=weak_skills,
        records=quiz_records,
    ).model_dump(), "测验结果")


# ─── GET /api/interview/practice/stats ───────────────────────


@router.get("/practice/stats")
def practice_stats(db: Session = Depends(get_db)):
    """练习总统计。"""
    records = db.query(PracticeRecord).all()
    if not records:
        # ⚠️ 必须走 ok() 包装：apiClient 以 `if (!body.success) throw` 解包，
        # 裸返回 Pydantic 模型会让「零练习记录」的新用户整页报错。
        # （2026-09-22 自测统计接入前端时由 test_practice_stats.py 抓出）
        return ok(PracticeStatsOut(
            total_practiced=0,
            total_correct=0,
            accuracy=0,
            by_type={},
            by_skill=[],
            weak_skills=[],
            weak_types=[],
            recent_sessions=[],
        ).model_dump(), "暂无练习记录")

    total = len(records)
    correct = sum(1 for r in records if r.correct)
    accuracy = round(correct / total * 100, 1) if total else 0

    # 按题型
    by_type: dict[str, list[PracticeRecord]] = {}
    for r in records:
        by_type.setdefault(r.question_type, []).append(r)

    type_stats = {}
    for ttype, trecords in by_type.items():
        tcorrect = sum(1 for r in trecords if r.correct)
        type_stats[ttype] = PracticeTypeStats(
            practiced=len(trecords),
            correct=tcorrect,
            accuracy=round(tcorrect / len(trecords) * 100, 1) if trecords else 0,
        )

    # 按技能
    by_skill: dict[str, list[PracticeRecord]] = {}
    for r in records:
        if r.skill_name:
            by_skill.setdefault(r.skill_name, []).append(r)

    skill_stats = []
    for skill, srecords in by_skill.items():
        scorrect = sum(1 for r in srecords if r.correct)
        skill_stats.append(
            PracticeSkillStats(
                skill=skill,
                practiced=len(srecords),
                correct=scorrect,
                accuracy=round(scorrect / len(srecords) * 100, 1) if srecords else 0,
            )
        )
    skill_stats.sort(key=lambda s: s.accuracy)

    weak_skills = [s.skill for s in skill_stats if s.accuracy < 50]
    weak_types = [t for t, s in type_stats.items() if s.accuracy < 50]

    # 最近测验
    recent = (
        db.query(PracticeRecord.session_id, func.min(PracticeRecord.created_at))
        .filter(PracticeRecord.session_id.isnot(None))
        .group_by(PracticeRecord.session_id)
        .order_by(func.min(PracticeRecord.created_at).desc())
        .limit(5)
        .all()
    )

    recent_sessions = []
    for sid, created_at in recent:
        srecords = [r for r in records if r.session_id == sid]
        avg_score = sum(r.score for r in srecords) / len(srecords) if srecords else 0
        recent_sessions.append(
            PracticeSessionSummary(
                session_id=sid,
                date=created_at.strftime("%Y-%m-%d") if created_at else "",
                score=round(avg_score, 1),
                count=len(srecords),
            )
        )

    return ok(PracticeStatsOut(
        total_practiced=total,
        total_correct=correct,
        accuracy=accuracy,
        by_type=type_stats,
        by_skill=skill_stats,
        weak_skills=weak_skills,
        weak_types=weak_types,
        recent_sessions=recent_sessions,
    ).model_dump(), "统计成功")
