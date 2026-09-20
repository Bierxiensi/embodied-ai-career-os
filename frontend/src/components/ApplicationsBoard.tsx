"use client";

/** 投递管理看板（/jobs/applications）。

 * 功能：漏斗统计 / 新增投递 / 状态流转 / 删除
 * 数据来源：/api/job-applications (CRUD)
 *
 * 从 JobsBoard 中提取并增强，独立页面更宽敞。
 */

import { useCallback, useMemo, useState } from "react";

import type { JobAppStatus, JobApplication, JobApplicationCreate } from "@/types";
import {
  createApplication,
  deleteApplication,
  updateApplication,
} from "@/services/jobHuntService";

/* ───────────────────────── 常量 ───────────────────────── */

const APP_STATUS_META: Record<JobAppStatus, { label: string; color: string; soft: string }> = {
  applied: { label: "已投递", color: "#86868B", soft: "var(--color-zinc-100)" },
  screening: { label: "筛选中", color: "#0EA5E9", soft: "rgba(14,165,233,0.10)" },
  interview: { label: "面试中", color: "#8B5CF6", soft: "rgba(139,92,246,0.10)" },
  offer: { label: "已拿offer", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  rejected: { label: "已挂", color: "var(--color-rose)", soft: "var(--color-rose-soft)" },
};

const STATUS_ORDER: JobAppStatus[] = ["applied", "screening", "interview", "offer", "rejected"];

const TRACK_LABEL: Record<string, string> = {
  agent: "Agent",
  embodied: "具身智能",
  "robot-software": "机器人软件",
  other: "其他",
};

/* ───────────────────────── 样式 ───────────────────────── */

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
};

const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-item-md)",
  background: "var(--color-card)",
  fontSize: 13,
  color: "var(--color-ink)",
  flex: "1 1 140px",
  minWidth: 120,
};

/* ───────────────────────── 组件 ───────────────────────── */

export default function ApplicationsBoard({
  initialApplications,
}: {
  initialApplications: JobApplication[];
}) {
  const [apps, setApps] = useState<JobApplication[]>(initialApplications);
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<JobApplicationCreate>({
    company: "",
    role: "",
    track: "other",
    source: null,
    status: "applied",
    salaryRange: null,
    appliedAt: null,
    nextAction: null,
    notes: null,
  });

  /* ── 漏斗统计（纯前端，从 apps 实时计算） ── */
  const funnel = useMemo(() => {
    const by: Record<JobAppStatus, number> = {
      applied: 0,
      screening: 0,
      interview: 0,
      offer: 0,
      rejected: 0,
    };
    apps.forEach((a) => {
      by[a.status] = (by[a.status] || 0) + 1;
    });
    const responded = by.screening + by.interview + by.offer;
    return {
      by,
      responseRate: apps.length ? Math.round((responded / apps.length) * 100) : 0,
    };
  }, [apps]);

  /* ── 新增投递 ── */
  const handleCreate = useCallback(async () => {
    if (!form.company.trim() || !form.role.trim()) return;
    setBusy(true);
    try {
      const created = await createApplication(form);
      setApps((prev) => [created, ...prev]);
      setForm({
        company: "",
        role: "",
        track: "other",
        source: null,
        status: "applied",
        salaryRange: null,
        appliedAt: null,
        nextAction: null,
        notes: null,
      });
      setShowForm(false);
    } catch (e) {
      console.error("新增投递失败:", e);
    } finally {
      setBusy(false);
    }
  }, [form]);

  /* ── 状态流转 ── */
  const handleStatusChange = useCallback(
    async (id: string, newStatus: JobAppStatus) => {
      try {
        const updated = await updateApplication(id, { status: newStatus });
        setApps((prev) => prev.map((a) => (a.id === id ? updated : a)));
      } catch (e) {
        console.error("更新状态失败:", e);
      }
    },
    []
  );

  /* ── 删除 ── */
  const handleDelete = useCallback(async (id: string) => {
    try {
      await deleteApplication(id);
      setApps((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      console.error("删除失败:", e);
    }
  }, []);

  return (
    <div
      style={{
        maxWidth: 960,
        margin: "0 auto",
        padding: "32px clamp(16px, 4vw, 48px)",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      <h1
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: "var(--color-ink)",
          margin: 0,
        }}
      >
        投递管理
      </h1>

      <div style={cardStyle}>
        {/* 漏斗统计 */}
        <div
          className="grid"
          style={{
            gap: 10,
            gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))",
            marginBottom: 16,
          }}
        >
          <FunnelStat label="已投递" value={funnel.by.applied} color="#86868B" />
          <FunnelStat label="筛选中" value={funnel.by.screening} color="#0EA5E9" />
          <FunnelStat label="面试中" value={funnel.by.interview} color="#8B5CF6" />
          <FunnelStat label="已拿offer" value={funnel.by.offer} color="var(--color-emerald)" />
          <FunnelStat label="已挂" value={funnel.by.rejected} color="var(--color-rose)" />
          <FunnelStat label="回复率" value={`${funnel.responseRate}%`} color="var(--color-primary)" />
        </div>

        {/* 新增按钮 */}
        <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
          <span style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
            共 {apps.length} 条记录
          </span>
          <button
            onClick={() => setShowForm((v) => !v)}
            style={{
              padding: "6px 14px",
              borderRadius: "var(--radius-pill)",
              border: "1px solid var(--color-primary)",
              background: showForm ? "var(--color-primary)" : "transparent",
              color: showForm ? "#fff" : "var(--color-primary)",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {showForm ? "收起" : "＋ 新增投递"}
          </button>
        </div>

        {/* 新增表单 */}
        {showForm ? (
          <div
            className="flex flex-col"
            style={{
              gap: 10,
              padding: 16,
              marginBottom: 16,
              background: "var(--color-zinc-100)",
              borderRadius: "var(--radius-item-md)",
            }}
          >
            <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
              <input
                placeholder="公司 *"
                value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })}
                style={inputStyle}
              />
              <input
                placeholder="岗位 *"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                style={inputStyle}
              />
              <select
                value={form.track}
                onChange={(e) => setForm({ ...form, track: e.target.value })}
                style={inputStyle}
              >
                {Object.entries(TRACK_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
              <input
                placeholder="来源（Boss/内推/猎聘…）"
                value={form.source ?? ""}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
                style={inputStyle}
              />
              <input
                placeholder="薪资范围 如 36-42K"
                value={form.salaryRange ?? ""}
                onChange={(e) => setForm({ ...form, salaryRange: e.target.value })}
                style={inputStyle}
              />
              <input
                type="date"
                value={form.appliedAt ?? ""}
                onChange={(e) => setForm({ ...form, appliedAt: e.target.value || null })}
                style={inputStyle}
              />
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value as JobAppStatus })}
                style={inputStyle}
              >
                {STATUS_ORDER.map((s) => (
                  <option key={s} value={s}>
                    {APP_STATUS_META[s].label}
                  </option>
                ))}
              </select>
            </div>
            <input
              placeholder="下一步动作（如 9/12 前发感谢信）"
              value={form.nextAction ?? ""}
              onChange={(e) => setForm({ ...form, nextAction: e.target.value })}
              style={inputStyle}
            />
            <div className="flex" style={{ gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={handleCreate}
                disabled={busy}
                style={{
                  padding: "8px 20px",
                  borderRadius: "var(--radius-pill)",
                  border: "none",
                  background: "var(--color-primary)",
                  color: "#fff",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: busy ? "not-allowed" : "pointer",
                  opacity: busy ? 0.6 : 1,
                }}
              >
                {busy ? "添加中…" : "添加记录"}
              </button>
            </div>
          </div>
        ) : null}

        {/* 投递列表 */}
        <div className="flex flex-col" style={{ gap: 8 }}>
          {apps.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--color-ink-48)", textAlign: "center", padding: 24 }}>
              暂无投递记录，点击「＋ 新增投递」开始跟踪。
            </p>
          ) : (
            apps.map((a) => {
              const meta = APP_STATUS_META[a.status];
              return (
                <div
                  key={a.id}
                  className="flex items-center"
                  style={{
                    gap: 12,
                    padding: "12px 14px",
                    border: "1px solid var(--color-hairline-soft)",
                    borderRadius: "var(--radius-item-md)",
                    flexWrap: "wrap",
                  }}
                >
                  <div className="flex flex-col" style={{ gap: 2, minWidth: 180, flex: 1 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>
                      {a.company}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
                      {a.role}
                      {a.salaryRange ? ` · ${a.salaryRange}` : ""}
                    </span>
                  </div>
                  <Pill
                    label={TRACK_LABEL[a.track] || a.track}
                    color="var(--color-ink-48)"
                    soft="var(--color-zinc-100)"
                  />
                  {a.appliedAt ? (
                    <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{a.appliedAt}</span>
                  ) : null}
                  {a.nextAction ? (
                    <span
                      style={{
                        fontSize: 12,
                        color: "var(--color-amber-deep)",
                        flex: "1 1 160px",
                        minWidth: 120,
                      }}
                    >
                      → {a.nextAction}
                    </span>
                  ) : null}
                  <span
                    style={{
                      padding: "3px 10px",
                      borderRadius: "var(--radius-pill)",
                      fontSize: 12,
                      fontWeight: 600,
                      color: meta.color,
                      background: meta.soft,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {meta.label}
                  </span>
                  <select
                    value={a.status}
                    onChange={(e) => handleStatusChange(a.id, e.target.value as JobAppStatus)}
                    style={{ ...inputStyle, width: 110, padding: "4px 8px", fontSize: 12 }}
                  >
                    {STATUS_ORDER.map((s) => (
                      <option key={s} value={s}>
                        {APP_STATUS_META[s].label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => handleDelete(a.id)}
                    title="删除"
                    style={{
                      border: "none",
                      background: "transparent",
                      color: "var(--color-ink-48)",
                      cursor: "pointer",
                      fontSize: 16,
                      lineHeight: 1,
                      padding: "2px 6px",
                    }}
                  >
                    ×
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────── 子组件 ───────────────────────── */

function FunnelStat({
  label,
  value,
  color,
}: {
  label: string;
  value: number | string;
  color: string;
}) {
  return (
    <div
      style={{
        padding: "10px 8px",
        borderRadius: "var(--radius-item-md)",
        background: "var(--color-zinc-100)",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--color-ink-48)", marginTop: 2 }}>{label}</div>
    </div>
  );
}

function Pill({ label, color, soft }: { label: string; color: string; soft: string }) {
  return (
    <span
      style={{
        padding: "2px 10px",
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
