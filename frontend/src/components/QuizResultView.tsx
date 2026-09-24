"use client";

import type { QuizResult } from "@/types";
import { questionTypeLabel } from "@/lib/questionType";

/**
 * 一轮小测验的成绩单。
 *
 * 只做展示：总分 / 逐题明细 / 按题型 / 本轮暴露的弱技能。
 * 长期学情（跨轮正确率、薄弱点趋势）由 PracticeStatsCard 负责，
 * 这里刻意只讲「这一轮」。
 */

interface Props {
  result: QuizResult;
  onClose: () => void;
}

const cardStyle: React.CSSProperties = {
  padding: 22,
  background: "var(--surface-card)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
};

const metaStyle: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text-muted)",
};

const chipStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 9px",
  borderRadius: "var(--radius-pill)",
  fontSize: 12,
  fontWeight: 500,
};

/** 得分 → 颜色（>=80 绿 / >=60 蓝 / 其余红，与 ResultCard 的判定保持一致）。 */
function scoreColor(score: number): { fg: string; bg: string } {
  if (score >= 80) return { fg: "var(--accent-success)", bg: "var(--accent-success-soft)" };
  if (score >= 60) return { fg: "var(--accent-primary)", bg: "var(--accent-primary-soft)" };
  return { fg: "var(--accent-danger)", bg: "var(--accent-danger-soft)" };
}

export default function QuizResultView({ result, onClose }: Props) {
  const score = Math.round(result.totalScore);

  return (
    <div style={cardStyle}>
      <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 10 }}>
        <h2 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)" }}>
          本轮成绩单
        </h2>
        <button
          onClick={onClose}
          style={{
            padding: "6px 14px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-default)",
            background: "transparent",
            color: "var(--text-secondary)",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          再来一轮
        </button>
      </div>

      {/* 总分 */}
      <div className="flex items-end" style={{ gap: 14, marginTop: 14, flexWrap: "wrap" }}>
        <div
          style={{
            fontSize: 40,
            fontWeight: 600,
            lineHeight: 1,
            fontVariantNumeric: "tabular-nums",
            color: scoreColor(score).fg,
          }}
        >
          {score}
        </div>
        <div style={{ ...metaStyle, paddingBottom: 4 }}>
          均分（满分 100） · 答对 {result.correctCount}/{result.count} 题
        </div>
      </div>

      {/* 按题型 */}
      {Object.keys(result.byType).length > 0 && (
        <div className="flex" style={{ gap: 8, flexWrap: "wrap", marginTop: 14 }}>
          {Object.entries(result.byType).map(([t, s]) => (
            <span key={t} style={{ ...chipStyle, ...scoreColor(s.avgScore), background: scoreColor(s.avgScore).bg }}>
              {questionTypeLabel(t)} {s.correct}/{s.count} · 均分 {Math.round(s.avgScore)}
            </span>
          ))}
        </div>
      )}

      {/* 本轮暴露的弱项 */}
      {result.weakSkills.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ ...metaStyle, marginBottom: 6 }}>本轮偏弱的技能（均分 &lt; 50）</div>
          <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
            {result.weakSkills.map((s) => (
              <span
                key={s}
                style={{
                  ...chipStyle,
                  color: "var(--accent-danger)",
                  background: "var(--accent-danger-soft)",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 逐题明细 */}
      <div className="flex flex-col" style={{ gap: 10, marginTop: 18 }}>
        {result.records.map((r, i) => {
          const c = scoreColor(r.score);
          return (
            <div
              key={`${r.questionId}-${i}`}
              style={{
                padding: "12px 14px",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                background: "var(--color-item-bg)",
              }}
            >
              <div className="flex items-center" style={{ gap: 8, flexWrap: "wrap" }}>
                <span style={{ ...chipStyle, color: c.fg, background: c.bg }}>
                  {r.score} 分
                </span>
                <span style={{ ...metaStyle }}>{questionTypeLabel(r.questionType)}</span>
                <span style={{ fontSize: 13, color: "var(--text-primary)", flex: 1, minWidth: 180 }}>
                  {r.question}
                </span>
              </div>

              <div style={{ marginTop: 8, fontSize: 12, lineHeight: 1.7, color: "var(--text-secondary)" }}>
                <div>
                  <span style={{ color: "var(--text-muted)" }}>你的答案：</span>
                  {r.userAnswer || "（空）"}
                </div>
                {r.correctAnswer && (
                  <div>
                    <span style={{ color: "var(--text-muted)" }}>参考答案：</span>
                    {r.correctAnswer}
                  </div>
                )}
                {r.feedback && (
                  <div style={{ color: "var(--text-muted)" }}>{r.feedback}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
