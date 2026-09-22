"use client";

import Link from "next/link";
import { useState } from "react";
import type { InterviewLog, InterviewStats, TaskDraft } from "@/types";
import {
  createLog,
  deleteLog,
  getStats,
  listLogs,
  toTasks,
} from "@/services/interviewService";

/* ───────────────────────── 复用样式 ───────────────────────── */

const cardStyle: React.CSSProperties = {
  padding: 24,
  background: "var(--color-card)",
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-card-lg)",
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 600,
  color: "var(--color-ink)",
  letterSpacing: "-0.01em",
};

const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "var(--radius-item-sm)",
  border: "1px solid var(--color-hairline)",
  background: "var(--color-card)",
  fontSize: 13,
  color: "var(--color-ink)",
  outline: "none",
  minWidth: 140,
};

const primaryBtn: React.CSSProperties = {
  padding: "8px 20px",
  borderRadius: "var(--radius-pill)",
  border: "none",
  background: "var(--color-primary)",
  color: "var(--color-on-primary)",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};

const iconBtn: React.CSSProperties = {
  border: "none",
  background: "transparent",
  color: "var(--color-ink-48)",
  cursor: "pointer",
  fontSize: 16,
  lineHeight: 1,
  padding: "2px 6px",
};

/* ───────────────────────── 小组件 ───────────────────────── */

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div
      style={{
        padding: 14,
        background: "var(--color-zinc-100)",
        borderRadius: "var(--radius-item-md)",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        alignItems: "flex-start",
        minWidth: 96,
      }}
    >
      <span style={{ fontSize: 22, fontWeight: 700, color }}>{value}</span>
      <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{label}</span>
    </div>
  );
}

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{ height: 6, width: "100%", background: "var(--color-zinc-100)", borderRadius: "var(--radius-pill)", overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${Math.min(100, Math.max(0, pct))}%`, background: color, borderRadius: "var(--radius-pill)" }} />
    </div>
  );
}

/** textarea 文本 → 列表（按行拆分，兼容英文逗号）。 */
function linesToArr(s: string): string[] {
  return s
    .split(/\n|,/)
    .map((x) => x.trim())
    .filter(Boolean);
}

/* ───────────────────────── 主组件 ───────────────────────── */

type Props = {
  initialLogs: InterviewLog[];
  initialStats: InterviewStats;
};

/** 面试线：面经 → 弱项 → 学习任务（回写 Task）。
 *
 * 2026-09-11 拆分（P3）：题库与抽题独立到 `/questions`（题库生长 + 覆盖率矩阵）。
 * 本页只保留「面经复盘」闭环 —— 两个页面各司其职，不做两套实现。
 */
export default function InterviewBoard({ initialLogs, initialStats }: Props) {
  const [logs, setLogs] = useState<InterviewLog[]>(initialLogs);
  const [stats, setStats] = useState<InterviewStats>(initialStats);

  const [busy, setBusy] = useState(false);
  const [showLogForm, setShowLogForm] = useState(false);

  const [logForm, setLogForm] = useState({
    company: "",
    role: "",
    round: "一面",
    interviewedAt: "",
    askedQuestions: "",
    weakQuestions: "",
    jdGaps: "",
    knowledgeGaps: "",
    nextActions: "",
    notes: "",
  });

  const refresh = async () => {
    const [ls, st] = await Promise.all([listLogs(), getStats()]);
    setLogs(ls);
    setStats(st);
  };

  async function handleCreateLog() {
    if (!logForm.company.trim() || !logForm.role.trim()) return;
    setBusy(true);
    try {
      await createLog({
        company: logForm.company,
        role: logForm.role,
        round: logForm.round || null,
        interviewedAt: logForm.interviewedAt || null,
        askedQuestions: linesToArr(logForm.askedQuestions),
        weakQuestions: linesToArr(logForm.weakQuestions),
        jdGaps: linesToArr(logForm.jdGaps),
        knowledgeGaps: linesToArr(logForm.knowledgeGaps),
        nextActions: linesToArr(logForm.nextActions),
        notes: logForm.notes || null,
      });
      alert("已记录面经");
      setLogForm({
        company: "", role: "", round: "一面", interviewedAt: "",
        askedQuestions: "", weakQuestions: "", jdGaps: "",
        knowledgeGaps: "", nextActions: "", notes: "",
      });
      setShowLogForm(false);
      await refresh();
    } catch (e) {
      alert("记录失败：" + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteLog(id: string) {
    if (!confirm("确认删除该面经？")) return;
    try {
      await deleteLog(id);
      await refresh();
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleToTasks(id: string) {
    try {
      const res = await toTasks(id, { limit: 5, duration: 40 });
      const titles = res.created.map((d: TaskDraft) => `· ${d.title}`).join("\n");
      alert(`已回写 ${res.count} 个学习任务：\n${titles}`);
      await refresh();
    } catch (e) {
      alert("回写失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  const maxWeak = stats.weakTopics.length ? stats.weakTopics[0].count : 1;

  return (
    <div className="flex flex-1 flex-col">
      <div
        className="flex flex-col"
        style={{ gap: "var(--spacing-lg)", padding: "36px clamp(20px, 8vw, 120px) 48px" }}
      >
        {/* Header */}
        <div className="flex items-start justify-between" style={{ gap: 24 }}>
          <div className="flex flex-col" style={{ gap: 8, minWidth: 0 }}>
            <span
              className="text-xs font-semibold uppercase"
              style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
            >
              INTERVIEW · FEEDBACK LOOP
            </span>
            <h1
              className="font-semibold"
              style={{ fontSize: 40, color: "var(--color-ink)", letterSpacing: "-0.02em" }}
            >
              面试线 · 面经 → 弱项 → 任务
            </h1>
            <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
              记录面经自动聚合弱项 · 一键回写学习任务（纯规则，不依赖 LLM）
            </p>
          </div>
          <Link
            href="/questions"
            className="shrink-0 no-underline"
            style={{
              padding: "8px 16px",
              borderRadius: "var(--radius-pill)",
              border: "1px solid var(--color-primary)",
              color: "var(--color-primary)",
              fontSize: 13,
              fontWeight: 600,
              whiteSpace: "nowrap",
            }}
          >
            题库 / 覆盖率 →
          </Link>
        </div>

        {/* Stats */}
        <div className="grid" style={{ gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" }}>
          <StatCard label="面经数" value={stats.totalLogs} color="var(--color-ink)" />
          <StatCard label="弱项条目" value={stats.totalWeak} color="var(--color-rose)" />
          <StatCard label="不重复弱项" value={stats.weakTopics.length} color="var(--color-amber)" />
        </div>

        {/* 弱项排行榜 */}
        <div style={cardStyle}>
          <h2 style={{ ...sectionTitleStyle, marginBottom: 14 }}>弱项排行榜（跨面经聚合）</h2>
          {stats.weakTopics.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>暂无弱项，去记录一条面经吧。</p>
          ) : (
            <div className="flex flex-col" style={{ gap: 10 }}>
              {stats.weakTopics.map((w) => (
                <div key={w.topic} className="flex items-center" style={{ gap: 12 }}>
                  <span style={{ fontSize: 13, width: 220, color: "var(--color-ink-80)" }}>{w.topic}</span>
                  <div style={{ flex: 1 }}>
                    <Bar pct={(w.count / maxWeak) * 100} color="var(--color-rose)" />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-rose-deep)", width: 28, textAlign: "right" }}>
                    ×{w.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 面经记录 */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between">
            <h2 style={sectionTitleStyle}>面经记录</h2>
            <button
              onClick={() => setShowLogForm((v) => !v)}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--color-primary)",
                background: showLogForm ? "var(--color-primary)" : "transparent",
                color: showLogForm ? "var(--color-on-primary)" : "var(--color-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {showLogForm ? "收起" : "＋ 记录面经"}
            </button>
          </div>

          {showLogForm ? (
            <div className="flex flex-col" style={{ gap: 10, marginTop: 14 }}>
              <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
                <input placeholder="公司 *" value={logForm.company} onChange={(e) => setLogForm({ ...logForm, company: e.target.value })} style={inputStyle} />
                <input placeholder="岗位 *" value={logForm.role} onChange={(e) => setLogForm({ ...logForm, role: e.target.value })} style={inputStyle} />
                <select value={logForm.round} onChange={(e) => setLogForm({ ...logForm, round: e.target.value })} style={inputStyle}>
                  {["一面", "二面", "三面", "HR", "技术面", "交叉面", "终面"].map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <input type="date" value={logForm.interviewedAt} onChange={(e) => setLogForm({ ...logForm, interviewedAt: e.target.value })} style={inputStyle} />
              </div>
              <div className="grid" style={{ gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
                {([
                  ["askedQuestions", "被问到的问题（每行一条）"],
                  ["weakQuestions", "答得不好的问题（弱项，每行一条）"],
                  ["jdGaps", "JD 能力缺口（每行一条）"],
                  ["knowledgeGaps", "知识盲区（每行一条）"],
                  ["nextActions", "下一步行动（每行一条）"],
                ] as const).map(([key, ph]) => (
                  <textarea
                    key={key}
                    placeholder={ph}
                    value={logForm[key]}
                    onChange={(e) => setLogForm({ ...logForm, [key]: e.target.value })}
                    style={{ ...inputStyle, minHeight: 76, resize: "vertical", width: "100%" }}
                  />
                ))}
              </div>
              <textarea
                placeholder="备注 / 复盘"
                value={logForm.notes}
                onChange={(e) => setLogForm({ ...logForm, notes: e.target.value })}
                style={{ ...inputStyle, minHeight: 60, resize: "vertical", width: "100%" }}
              />
              <div className="flex" style={{ gap: 10, justifyContent: "flex-end" }}>
                <button onClick={handleCreateLog} disabled={busy} style={{ ...primaryBtn, opacity: busy ? 0.6 : 1 }}>
                  {busy ? "保存中…" : "保存面经"}
                </button>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col" style={{ gap: 8, marginTop: 14 }}>
            {logs.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>暂无面经。</p>
            ) : (
              logs.map((l) => (
                <div
                  key={l.id}
                  style={{ padding: "12px 14px", border: "1px solid var(--color-hairline-soft)", borderRadius: "var(--radius-item-md)" }}
                >
                  <div className="flex items-center" style={{ gap: 10, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>{l.company}</span>
                    <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{l.role}{l.round ? ` · ${l.round}` : ""}{l.interviewedAt ? ` · ${l.interviewedAt}` : ""}</span>
                    <div style={{ flex: 1 }} />
                    <button onClick={() => handleToTasks(l.id)} style={{ ...iconBtn, fontSize: 13, color: "var(--color-primary)" }}>
                      回写学习任务
                    </button>
                    <button onClick={() => handleDeleteLog(l.id)} title="删除" style={iconBtn}>×</button>
                  </div>
                  {l.weakQuestions.length > 0 ? (
                    <div className="flex flex-wrap" style={{ gap: 6, marginTop: 8 }}>
                      {l.weakQuestions.map((w, i) => (
                        <span key={i} style={{ padding: "2px 8px", borderRadius: "var(--radius-pill)", fontSize: 11, color: "var(--color-rose-deep)", background: "rgba(244,63,94,0.10)" }}>
                          {w}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {l.generatedTaskIds.length > 0 ? (
                    <div style={{ fontSize: 11, color: "var(--color-ink-48)", marginTop: 6 }}>
                      已回写任务 #{l.generatedTaskIds.join(", #")}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>

        <footer style={{ fontSize: 12, color: "var(--color-ink-48)", textAlign: "center", paddingTop: 8 }}>
          Career OS · 面试线 · 数据来自 /api/interviews（弱项聚合纯规则，不依赖 LLM）· 题库见 /questions
        </footer>
      </div>
    </div>
  );
}
