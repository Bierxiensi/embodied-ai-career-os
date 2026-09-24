"use client";

import { useState } from "react";
import type { QuestionType, QuizQuestion, QuizResult, QuizStart } from "@/types";
import { getQuizResult, startQuiz } from "@/services/interviewService";
import QuestionCard, { type PracticeCardQuestion } from "./QuestionCard";
import QuizResultView from "./QuizResultView";

/**
 * 小测验：抽题 → 逐题作答 → 本轮成绩单。
 *
 * 与「模拟面试 · 抽题」的区别：抽题只给你题和要点、答不了；这里要真答、真判分，
 * 并把一轮的结果汇总起来（总分 / 逐题 / 按题型），最终汇入学情统计。
 *
 * 数据链路：
 *   startQuiz        → POST /api/interview/quiz/start     （下发题 + session_id）
 *   QuestionCard     → POST /api/interview/practice       （mode=quiz，带 session_id）
 *   getQuizResult    → GET  /api/interview/quiz/{id}/result
 */

interface Props {
  /** 分类下拉项（由父组件传入，避免各处各写一份分类名） */
  categoryOptions: { value: string; label: string }[];
  /** 可关联的技能行（来自覆盖率矩阵） */
  skillOptions: string[];
  /** 一轮测验结束（答完或中途结束）时回调 —— 父组件借此刷新学情统计 */
  onQuizEnd?: () => void;
}

type Phase = "setup" | "running" | "result";

const cardStyle: React.CSSProperties = {
  padding: 24,
  background: "var(--surface-card)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
};

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-primary)",
  fontSize: 13,
};

const primaryBtn: React.CSSProperties = {
  padding: "8px 18px",
  borderRadius: "var(--radius-sm)",
  border: "none",
  background: "var(--accent-primary)",
  color: "var(--text-inverse)",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};

const linkBtn: React.CSSProperties = {
  padding: 0,
  border: "none",
  background: "transparent",
  color: "var(--text-muted)",
  fontSize: 12,
  cursor: "pointer",
};

/** 小测验下发的那道题 → QuestionCard 需要的形状。 */
function toCardQuestion(q: QuizQuestion): PracticeCardQuestion {
  return {
    id: String(q.id),
    question: q.question,
    questionType: q.questionType as QuestionType,
    // 选项走 overrideOptions（后端给的是 string[]，不是题库的 {choices, correct}）
    options: null,
    skillName: q.skillName,
    // 参考答案由服务端按题库原题的要点给出，前端不需要也不该拿到
    answerOutline: null,
  };
}

export default function QuizRunner({ categoryOptions, skillOptions, onQuizEnd }: Props) {
  const [phase, setPhase] = useState<Phase>("setup");
  const [category, setCategory] = useState("");
  const [skill, setSkill] = useState("");
  const [count, setCount] = useState("5");
  const [quiz, setQuiz] = useState<QuizStart | null>(null);
  const [index, setIndex] = useState(0);
  const [summary, setSummary] = useState<QuizResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const total = quiz?.questions.length ?? 0;
  const current = quiz?.questions[index] ?? null;

  async function handleStart() {
    setBusy(true);
    setError(null);
    try {
      const res = await startQuiz({
        category: category || null,
        skillName: skill || null,
        count: Number(count) || 5,
      });
      setQuiz(res);
      setIndex(0);
      setSummary(null);
      setPhase("running");
    } catch (e) {
      setError(e instanceof Error ? e.message : "抽题失败");
    } finally {
      setBusy(false);
    }
  }

  /** 「下一题」——已是最后一题则结算。 */
  async function handleNext() {
    if (!quiz) return;
    if (index + 1 < total) {
      setIndex(index + 1);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setSummary(await getQuizResult(quiz.sessionId));
      setPhase("result");
    } catch (e) {
      setError(e instanceof Error ? e.message : "取成绩单失败");
    } finally {
      setBusy(false);
      onQuizEnd?.();
    }
  }

  /** 中途结束：已答的题已经计入练习记录，所以也要刷新学情。 */
  function handleAbort() {
    setPhase("setup");
    setQuiz(null);
    setIndex(0);
    onQuizEnd?.();
  }

  function handleReset() {
    setPhase("setup");
    setQuiz(null);
    setSummary(null);
    setIndex(0);
  }

  // ── 成绩单 ────────────────────────────────────────────────
  if (phase === "result" && summary) {
    return (
      <div className="flex flex-col" style={{ gap: 12 }}>
        <QuizResultView result={summary} onClose={handleReset} />
      </div>
    );
  }

  // ── 答题中 ────────────────────────────────────────────────
  if (phase === "running" && current) {
    return (
      <div style={cardStyle}>
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 10 }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
            小测验 · 第 {index + 1}/{total} 题
          </h2>
          <button onClick={handleAbort} style={linkBtn}>
            结束本轮
          </button>
        </div>

        {/* 进度条：只表示"走到哪儿了"，不代表对错 */}
        <div
          style={{
            height: 4,
            borderRadius: "var(--radius-pill)",
            background: "var(--color-zinc-100)",
            marginTop: 12,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${((index + 1) / Math.max(1, total)) * 100}%`,
              height: "100%",
              background: "var(--accent-primary)",
              transition: "width .2s ease",
            }}
          />
        </div>

        <div style={{ marginTop: 18 }}>
          <QuestionCard
            key={`${quiz?.sessionId}-${current.id}-${index}`}
            question={toCardQuestion(current)}
            overrideType={current.questionType as QuestionType}
            overrideOptions={current.options}
            sessionId={quiz?.sessionId}
            onContinue={handleNext}
            continueLabel={index + 1 < total ? "下一题" : "看成绩"}
          />
        </div>

        {busy && (
          <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-muted)" }}>
            正在生成本轮成绩单…
          </div>
        )}
        {error && (
          <div style={{ marginTop: 12, fontSize: 12, color: "var(--accent-danger)" }}>{error}</div>
        )}
      </div>
    );
  }

  // ── 设置 ──────────────────────────────────────────────────
  return (
    <div style={cardStyle}>
      <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 10 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>小测验 · 抽几道答一答</h2>
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
          逐题作答 → 出本轮成绩单，并计入上面那张学情卡
        </span>
      </div>

      <div className="flex items-center" style={{ gap: 10, marginTop: 14, flexWrap: "wrap" }}>
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={inputStyle}>
          <option value="">全部分类</option>
          {categoryOptions.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
        <select value={skill} onChange={(e) => setSkill(e.target.value)} style={inputStyle}>
          <option value="">不限技能</option>
          {skillOptions.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <input
          value={count}
          onChange={(e) => setCount(e.target.value)}
          style={{ ...inputStyle, width: 80 }}
          placeholder="题数"
        />
        <button onClick={handleStart} disabled={busy} style={{ ...primaryBtn, opacity: busy ? 0.6 : 1 }}>
          {busy ? "抽题中…" : "开始测验"}
        </button>
      </div>

      <p style={{ fontSize: 12, lineHeight: 1.7, color: "var(--text-muted)", marginTop: 10 }}>
        题型：配置了真实 LLM（<code>LLM_PROVIDER</code>）时会把题目改写成选择 / 判断 / 填空题；
        未配置时统一出简答题，按答题要点的关键词覆盖率评分 —— 没接模型也不会让判分失效。
      </p>

      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: "var(--accent-danger)" }}>{error}</div>
      )}
    </div>
  );
}
