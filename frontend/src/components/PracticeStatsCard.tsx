"use client";

import type { PracticeStats } from "@/types";
import { questionTypeLabel } from "@/lib/questionType";

/**
 * 练习学情卡。
 *
 * 定位：题库已从「求职 KPI」降级为「需要时自测」的存档（2026-09-22 用户裁决），
 * 所以这里展示的是**学习效果**（练了多少 / 正确率 / 哪里薄弱），
 * 而不是「还差多少题」。
 *
 * 数据来自 GET /api/interview/practice/stats —— 该接口与 service 早已存在，
 * 但此前从未被前端调用（getPracticeStats 是死代码），本组件将其接上。
 */

const cardStyle: React.CSSProperties = {
  padding: 24,
  background: "var(--surface-card)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 600,
  color: "var(--text-primary)",
  letterSpacing: "-0.01em",
};

const metricValueStyle: React.CSSProperties = {
  fontSize: 24,
  fontWeight: 600,
  color: "var(--text-primary)",
  fontVariantNumeric: "tabular-nums",
  lineHeight: 1.2,
};

const metricLabelStyle: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text-muted)",
  marginTop: 2,
};

const hintStyle: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text-muted)",
  lineHeight: 1.7,
};

const chipStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 9px",
  borderRadius: "var(--radius-pill)",
  fontSize: 12,
  fontWeight: 500,
};

function Metric({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="flex flex-col">
      <span style={metricValueStyle}>{value}</span>
      <span style={metricLabelStyle}>{label}</span>
    </div>
  );
}

export default function PracticeStatsCard({ stats }: { stats: PracticeStats }) {
  const hasData = stats.totalPracticed > 0;

  return (
    <div style={cardStyle}>
      <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 10 }}>
        <h2 style={sectionTitleStyle}>我的练习 · 学得怎么样</h2>
        <span style={hintStyle}>
          {hasData ? `累计答过 ${stats.totalPracticed} 次` : "还没练过"}
        </span>
      </div>

      {!hasData ? (
        <p style={{ ...hintStyle, marginTop: 12 }}>
          还没练过。用下面的「模拟面试 · 抽题」抽几道，答完这里就会记下你的正确率和薄弱点
          —— 题库现在不考核进度，只在你需要的时候拿来测自己。
        </p>
      ) : (
        <>
          <div
            className="grid"
            style={{
              gap: 16,
              gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
              marginTop: 16,
            }}
          >
            <Metric value={stats.totalPracticed} label="练习次数" />
            <Metric value={stats.totalCorrect} label="答对" />
            <Metric value={`${stats.accuracy}%`} label="正确率" />
          </div>

          <div style={{ marginTop: 18 }}>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
              需要再练
            </div>
            {stats.weakSkills.length === 0 && stats.weakTypes.length === 0 ? (
              <span style={{ ...hintStyle }}>
                暂无明显弱项（按正确率 &lt; 50% 判定）。
              </span>
            ) : (
              <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
                {stats.weakSkills.map((s) => (
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
                {stats.weakTypes.map((t) => (
                  <span
                    key={`type-${t}`}
                    style={{
                      ...chipStyle,
                      color: "var(--accent-warning)",
                      background: "var(--accent-warning-soft)",
                    }}
                  >
                    {questionTypeLabel(t)} 题型
                  </span>
                ))}
              </div>
            )}
          </div>

          {stats.bySkill.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
                按技能（正确率从低到高）
              </div>
              <div className="flex flex-col" style={{ gap: 4 }}>
                {stats.bySkill.slice(0, 8).map((s) => (
                  <div
                    key={s.skill}
                    className="flex items-center justify-between"
                    style={{ fontSize: 12, color: "var(--text-secondary)" }}
                  >
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {s.skill}
                    </span>
                    <span style={{ fontVariantNumeric: "tabular-nums", color: "var(--text-muted)" }}>
                      {s.correct}/{s.practiced} · {s.accuracy}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {stats.recentSessions.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
                最近测验
              </div>
              <div className="flex flex-col" style={{ gap: 4 }}>
                {stats.recentSessions.map((s) => (
                  <div
                    key={s.sessionId}
                    className="flex items-center justify-between"
                    style={{ fontSize: 12, color: "var(--text-secondary)" }}
                  >
                    <span>{s.date}</span>
                    <span style={{ fontVariantNumeric: "tabular-nums", color: "var(--text-muted)" }}>
                      {s.count} 题 · 均分 {s.score}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
