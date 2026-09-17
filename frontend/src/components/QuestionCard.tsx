"use client";

import { useState } from "react";
import type { InterviewQuestion, PracticeResult, QuestionType } from "@/types";
import { postPractice } from "@/services/interviewService";
import ChoiceQuestion from "./questions/ChoiceQuestion";
import JudgeQuestion from "./questions/JudgeQuestion";
import FillQuestion from "./questions/FillQuestion";
import OpenQuestion from "./questions/OpenQuestion";
import ResultCard from "./ResultCard";

interface Props {
  question: InterviewQuestion;
  /** 覆盖题型（测验模式下使用 LLM 生成的题型） */
  overrideType?: QuestionType;
  /** 覆盖选项（测验模式下 LLM 生成的选项） */
  overrideOptions?: string[] | null;
  /** 答题后的回调 */
  onResult?: (result: PracticeResult) => void;
  /** 关闭回调 */
  onClose?: () => void;
  /** 小测验 session 信息 */
  sessionId?: string | null;
}

export default function QuestionCard({
  question,
  overrideType,
  overrideOptions,
  onResult,
  onClose,
  sessionId,
}: Props) {
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const questionType = overrideType || question.questionType || "open";
  const options = overrideOptions || question.options?.choices || null;

  const handleAnswer = async (answer: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await postPractice({
        questionId: Number(question.id),
        questionType,
        userAnswer: answer,
        generatedOptions: questionType === "choice" ? options : null,
        skillName: question.skillName,
        mode: sessionId ? "quiz" : "single",
        sessionId,
      });
      setResult(res);
      onResult?.(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 40, color: "#6b7280" }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
        评分中...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: 40, color: "#ef4444" }}>
        <div style={{ fontSize: 24, marginBottom: 8 }}>⚠️</div>
        {error}
        <div style={{ marginTop: 12 }}>
          <button
            onClick={() => setError(null)}
            style={{
              padding: "6px 16px",
              borderRadius: 6,
              border: "1px solid #d1d5db",
              background: "white",
              cursor: "pointer",
            }}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  if (result) {
    return <ResultCard result={result} onClose={onClose} />;
  }

  // 题型标签
  const typeLabels: Record<QuestionType, string> = {
    open: "📝 开放问答",
    choice: "🔘 单选题",
    fill: "✏️ 填空题",
    judge: "⚖️ 判断题",
  };

  return (
    <div>
      {/* 题型标签 */}
      <div
        style={{
          display: "inline-block",
          padding: "4px 10px",
          borderRadius: 6,
          background: "#f3f4f6",
          fontSize: 12,
          fontWeight: 600,
          color: "#6b7280",
          marginBottom: 12,
        }}
      >
        {typeLabels[questionType]}
        {question.skillName && (
          <span style={{ marginLeft: 8, color: "#9ca3af" }}>· {question.skillName}</span>
        )}
      </div>

      {/* 题型组件 */}
      {questionType === "choice" && options ? (
        <ChoiceQuestion question={question.question} options={options} onAnswer={handleAnswer} />
      ) : questionType === "judge" ? (
        <JudgeQuestion question={question.question} onAnswer={handleAnswer} />
      ) : questionType === "fill" ? (
        <FillQuestion question={question.question} onAnswer={handleAnswer} />
      ) : (
        <OpenQuestion
          question={question.question}
          answerOutline={question.answerOutline}
          onAnswer={handleAnswer}
        />
      )}

      {/* 关闭按钮 */}
      {onClose && !result && (
        <div style={{ marginTop: 16, textAlign: "right" }}>
          <button
            onClick={onClose}
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              background: "transparent",
              color: "#9ca3af",
              border: "none",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            跳过
          </button>
        </div>
      )}
    </div>
  );
}
