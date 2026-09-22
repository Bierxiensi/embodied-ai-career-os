"use client";

import type { PracticeResult } from "@/types";

interface Props {
  result: PracticeResult;
  onContinue?: () => void;
  /** 「继续」按钮文案。小测验最后一题传「看成绩」，默认「下一题」。 */
  continueLabel?: string;
  onClose?: () => void;
}

export default function ResultCard({ result, onContinue, continueLabel, onClose }: Props) {
  const isPass = result.score >= 80;
  return (
    <div
      style={{
        borderRadius: 12,
        border: `2px solid ${isPass ? "#22c55e" : result.correct ? "#3b82f6" : "#ef4444"}`,
        background: isPass ? "#f0fdf4" : result.correct ? "#eff6ff" : "#fef2f2",
        padding: 20,
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <span style={{ fontSize: 28 }}>{isPass ? "✅" : result.correct ? "🔵" : "❌"}</span>
        <div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>
            {result.score}
            <span style={{ fontSize: 14, fontWeight: 400, color: "#6b7280" }}>
              /{result.maxScore}
            </span>
          </div>
          <div style={{ fontSize: 13, color: "#6b7280" }}>
            {isPass ? "掌握良好" : result.correct ? "基本正确" : "需要加强"}
          </div>
        </div>
      </div>

      {/* Feedback */}
      <p style={{ fontSize: 14, lineHeight: 1.6, marginBottom: 12 }}>{result.feedback}</p>

      {/* Correct answer */}
      {result.correctAnswer && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 4 }}>
            正确答案：
          </div>
          <div
            style={{
              padding: "8px 12px",
              borderRadius: 6,
              background: "rgba(255,255,255,0.6)",
              fontSize: 14,
            }}
          >
            {result.correctAnswer}
          </div>
        </div>
      )}

      {/* Outline coverage */}
      {(result.outlineCovered.length > 0 || result.outlineMissed.length > 0) && (
        <div style={{ display: "flex", gap: 16, marginBottom: 12, fontSize: 13 }}>
          {result.outlineCovered.length > 0 && (
            <div>
              <span style={{ color: "#22c55e", fontWeight: 600 }}>✓ 覆盖：</span>{" "}
              {result.outlineCovered.join("、")}
            </div>
          )}
          {result.outlineMissed.length > 0 && (
            <div>
              <span style={{ color: "#ef4444", fontWeight: 600 }}>✗ 遗漏：</span>{" "}
              {result.outlineMissed.join("、")}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 8 }}>
        {onContinue && (
          <button
            onClick={onContinue}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              background: "#3b82f6",
              color: "white",
              border: "none",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 14,
            }}
          >
            {continueLabel ?? "下一题"}
          </button>
        )}
        {onClose && (
          <button
            onClick={onClose}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              background: "transparent",
              color: "#6b7280",
              border: "1px solid #d1d5db",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            关闭
          </button>
        )}
      </div>
    </div>
  );
}
