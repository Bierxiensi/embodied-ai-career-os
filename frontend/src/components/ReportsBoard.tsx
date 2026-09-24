"use client";

import { useState } from "react";
import type {
  Followup,
  FollowupResult,
  Report,
  ReportKind,
  ReportLog,
  ReportSchedule,
} from "@/types";
import { getHistory, sendReport } from "@/services/reportService";

/* ───────────────────────── 元数据 ───────────────────────── */

const WEEKDAY_LABEL: Record<string, string> = {
  mon: "周一",
  tue: "周二",
  wed: "周三",
  thu: "周四",
  fri: "周五",
  sat: "周六",
  sun: "周日",
};

const STATUS_LABEL: Record<string, string> = {
  applied: "已投递",
  screening: "沟通中",
  interview: "面试中",
  offer: "Offer",
  rejected: "已挂",
};

/* ───────────────────────── 复用样式 ───────────────────────── */

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

const primaryBtn: React.CSSProperties = {
  padding: "8px 20px",
  borderRadius: "var(--radius-pill)",
  border: "none",
  background: "var(--accent-primary)",
  color: "var(--text-inverse)",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};

const ghostBtn: React.CSSProperties = {
  padding: "6px 14px",
  borderRadius: "var(--radius-pill)",
  border: "1px solid var(--border-default)",
  background: "var(--surface-card)",
  color: "var(--text-primary)",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
};

/* ───────────────────────── 小组件 ───────────────────────── */

function Pill({ label, color, soft }: { label: string; color: string; soft: string }) {
  return (
    <span
      style={{
        padding: "3px 10px",
        borderRadius: "var(--radius-pill)",
        fontSize: 12,
        fontWeight: 600,
        color,
        background: soft,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div
      style={{
        padding: 14,
        background: "var(--color-zinc-100)",
        borderRadius: "var(--radius-md)",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{label}</span>
      <span style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1.1 }}>{value}</span>
    </div>
  );
}

function ReportSections({ report }: { report: Report }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {report.sections.map((sec) => (
        <div key={sec.key} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
            {sec.title}
          </span>
          {sec.lines.length === 0 ? (
            <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>（暂无）</span>
          ) : (
            <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 5 }}>
              {sec.lines.map((line, i) => (
                <li key={i} style={{ fontSize: 12.5, color: "var(--text-muted)", lineHeight: 1.65 }}>
                  {line}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

/* ───────────────────────── 主组件 ───────────────────────── */

type Props = {
  initialDaily: Report;
  initialWeekly: Report;
  initialSchedule: ReportSchedule;
  initialFollowups: FollowupResult;
  initialHistory: ReportLog[];
};

export default function ReportsBoard({
  initialDaily,
  initialWeekly,
  initialSchedule,
  initialFollowups,
  initialHistory,
}: Props) {
  const [daily, setDaily] = useState(initialDaily);
  const [weekly, setWeekly] = useState(initialWeekly);
  const [schedule] = useState(initialSchedule);
  const [followups] = useState(initialFollowups);
  const [history, setHistory] = useState(initialHistory);

  const [activeKind, setActiveKind] = useState<ReportKind>("daily");
  const [sending, setSending] = useState<ReportKind | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const active = activeKind === "daily" ? daily : weekly;

  async function handleSend(kind: ReportKind, force: boolean) {
    setSending(kind);
    setError(null);
    setToast(null);
    try {
      const res = await sendReport(kind, force);
      if (res.sent) {
        setToast(`${kind === "daily" ? "日报" : "周报"}已推送到「${schedule.channel}」通道`);
      } else {
        setToast(res.reason || "未推送");
      }
      setHistory(await getHistory());
    } catch (e) {
      setError(e instanceof Error ? e.message : "推送失败");
    } finally {
      setSending(null);
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div
        style={{
          maxWidth: 1120,
          margin: "0 auto",
          padding: "32px 24px 64px",
          display: "flex",
          flexDirection: "column",
          gap: 24,
        }}
      >
        {/* 标题 */}
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
              日报 / 周报
            </h1>
            <p style={{ marginTop: 6, fontSize: 13, color: "var(--text-muted)" }}>
              每日 08:30 自动出日报、每周一 09:00 出周报，投递跟进每日 10:00 提醒 —— 全部走
              {" "}<strong>{schedule.channel}</strong> 通道
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              style={{ ...primaryBtn, opacity: sending ? 0.6 : 1 }}
              disabled={sending !== null}
              onClick={() => handleSend("daily", true)}
            >
              {sending === "daily" ? "推送中…" : "生成并推送日报"}
            </button>
            <button
              style={{ ...primaryBtn, opacity: sending ? 0.6 : 1 }}
              disabled={sending !== null}
              onClick={() => handleSend("weekly", true)}
            >
              {sending === "weekly" ? "推送中…" : "生成并推送周报"}
            </button>
          </div>
        </div>

        {toast && (
          <div
            style={{
              padding: "10px 16px",
              background: "var(--accent-success-soft)",
              color: "var(--accent-success)",
              borderRadius: "var(--radius-md)",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {toast}
          </div>
        )}
        {error && (
          <div
            style={{
              padding: "10px 16px",
              background: "rgba(244,63,94,0.10)",
              color: "var(--accent-danger)",
              borderRadius: "var(--radius-md)",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {error}
          </div>
        )}

        {/* 调度状态 */}
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <span style={sectionTitleStyle}>调度配置</span>
            <Pill
              label={schedule.enabled ? "已启用" : "已停用"}
              color={schedule.enabled ? "var(--accent-success)" : "var(--text-muted)"}
              soft={schedule.enabled ? "var(--accent-success-soft)" : "var(--color-zinc-100)"}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 12 }}>
            <StatCard label="日报" value={schedule.dailyTime} color="var(--accent-primary)" />
            <StatCard
              label="周报"
              value={`${WEEKDAY_LABEL[schedule.weeklyDay] || schedule.weeklyDay} ${schedule.weeklyTime}`}
              color="var(--color-violet)"
            />
            <StatCard label="跟进提醒" value={schedule.followupTime} color="var(--accent-warning)" />
            <StatCard label="停滞阈值" value={`${schedule.followupStaleDays} 天`} color="var(--text-muted)" />
          </div>

          <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 6 }}>
            {schedule.jobs.length === 0 ? (
              <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
                调度器未运行（开发态正常，接口仍可直接生成报告）
              </span>
            ) : (
              schedule.jobs.map((j) => (
                <div key={j.id} style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5 }}>
                  <code style={{ color: "var(--text-primary)" }}>{j.id}</code>
                  <span style={{ color: "var(--text-muted)" }}>
                    下次：{j.nextRun ? new Date(j.nextRun).toLocaleString("zh-CN") : "—"}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 待跟进投递 */}
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
            <span style={sectionTitleStyle}>待跟进投递</span>
            <Pill
              label={`${followups.count} 家`}
              color={followups.count > 0 ? "var(--accent-warning)" : "var(--accent-success)"}
              soft={followups.count > 0 ? "var(--accent-warning-soft)" : "var(--accent-success-soft)"}
            />
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              判定：计划到期，或投递后停滞超 {followups.staleDays} 天
            </span>
          </div>

          {followups.items.length === 0 ? (
            <span style={{ fontSize: 12.5, color: "var(--text-muted)" }}>
              无待跟进 —— 投递节奏正常
            </span>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {followups.items.map((f: Followup) => (
                <div
                  key={f.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    padding: "10px 14px",
                    background: "var(--color-zinc-100)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                      {f.company}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{f.role}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
                    <Pill
                      label={STATUS_LABEL[f.status] || f.status}
                      color="var(--text-muted)"
                      soft="var(--surface-card)"
                    />
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: f.overdue ? "var(--accent-danger)" : "var(--accent-warning)",
                      }}
                    >
                      {f.reason}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 报告正文 */}
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                style={activeKind === "daily" ? primaryBtn : ghostBtn}
                onClick={() => setActiveKind("daily")}
              >
                日报 · {daily.periodKey}
              </button>
              <button
                style={activeKind === "weekly" ? primaryBtn : ghostBtn}
                onClick={() => setActiveKind("weekly")}
              >
                周报 · {weekly.periodKey}
              </button>
            </div>
            <button style={ghostBtn} onClick={() => handleSend(activeKind, false)} disabled={sending !== null}>
              {sending === activeKind ? "推送中…" : "按幂等规则推送（已发则跳过）"}
            </button>
          </div>

          <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", marginBottom: 18 }}>
            {active.title}
          </h2>
          <ReportSections report={active} />
        </div>

        {/* 归档历史 */}
        <div style={cardStyle}>
          <span style={sectionTitleStyle}>归档历史</span>
          {history.length === 0 ? (
            <p style={{ marginTop: 12, fontSize: 12.5, color: "var(--text-muted)" }}>
              暂无归档 —— 点上方「生成并推送」会同时归档
            </p>
          ) : (
            <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              {history.map((h) => (
                <div
                  key={h.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 12,
                    padding: "9px 14px",
                    background: "var(--color-zinc-100)",
                    borderRadius: "var(--radius-md)",
                  }}
                >
                  <span style={{ fontSize: 12.5, color: "var(--text-primary)" }}>{h.title}</span>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
                    <Pill
                      label={h.sent ? "已推送" : "未推送"}
                      color={h.sent ? "var(--accent-success)" : "var(--text-muted)"}
                      soft={h.sent ? "var(--accent-success-soft)" : "var(--surface-card)"}
                    />
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      {h.generatedAt ? new Date(h.generatedAt).toLocaleString("zh-CN") : "—"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
