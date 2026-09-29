"use client";

/** 投递管理看板（/jobs/applications）。

 * 功能：漏斗统计 / 投递记录只读展示（2026-09-29 撤表单：登记与状态流转收起）
 * 数据来源：/api/job-applications（只读 GET；写口留在阶段页之外，见 STYLE.md 不变量 3）
 *
 * 从 JobsBoard 中提取并增强，独立页面更宽敞。
 */

import { useMemo } from "react";

import type { JobAppStatus, JobApplication } from "@/types";

/* ───────────────────────── 常量 ───────────────────────── */

const APP_STATUS_META: Record<JobAppStatus, { label: string; color: string; soft: string }> = {
  applied: { label: "已投递", color: "#86868B", soft: "var(--color-zinc-100)" },
  screening: { label: "筛选中", color: "var(--color-sky)", soft: "rgba(14,165,233,0.10)" },
  interview: { label: "面试中", color: "var(--color-violet)", soft: "rgba(139,92,246,0.10)" },
  offer: { label: "已拿offer", color: "var(--accent-success)", soft: "var(--accent-success-soft)" },
  rejected: { label: "已挂", color: "var(--accent-danger)", soft: "var(--accent-danger-soft)" },
};

const TRACK_LABEL: Record<string, string> = {
  agent: "Agent",
  embodied: "具身智能",
  "robot-software": "机器人软件",
  other: "其他",
};

/* ───────────────────────── 样式 ───────────────────────── */

const cardStyle: React.CSSProperties = {
  padding: 24,
  background: "var(--surface-card)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
};

/* ───────────────────────── 组件 ───────────────────────── */

export default function ApplicationsBoard({
  initialApplications,
}: {
  initialApplications: JobApplication[];
}) {
  const apps = initialApplications;

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
          color: "var(--text-primary)",
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
          <FunnelStat label="筛选中" value={funnel.by.screening} color="var(--color-sky)" />
          <FunnelStat label="面试中" value={funnel.by.interview} color="var(--color-violet)" />
          <FunnelStat label="已拿offer" value={funnel.by.offer} color="var(--accent-success)" />
          <FunnelStat label="已挂" value={funnel.by.rejected} color="var(--accent-danger)" />
          <FunnelStat label="回复率" value={`${funnel.responseRate}%`} color="var(--accent-primary)" />
        </div>

        {/* 记录数（归档线只读：登记入口已收起） */}
        <div className="flex items-center" style={{ marginBottom: 14 }}>
          <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
            共 {apps.length} 条记录 · 归档线只读，登记入口已收起
          </span>
        </div>

        {/* 投递列表 */}
        <div className="flex flex-col" style={{ gap: 8 }}>
          {apps.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--text-muted)", textAlign: "center", padding: 24 }}>
              暂无投递记录（归档线只读，数据保留）。
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
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                    flexWrap: "wrap",
                  }}
                >
                  <div className="flex flex-col" style={{ gap: 2, minWidth: 180, flex: 1 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                      {a.company}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      {a.role}
                      {a.salaryRange ? ` · ${a.salaryRange}` : ""}
                    </span>
                  </div>
                  <Pill
                    label={TRACK_LABEL[a.track] || a.track}
                    color="var(--text-muted)"
                    soft="var(--color-zinc-100)"
                  />
                  {a.appliedAt ? (
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{a.appliedAt}</span>
                  ) : null}
                  {a.nextAction ? (
                    <span
                      style={{
                        fontSize: 12,
                        color: "var(--accent-warning)",
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
        borderRadius: "var(--radius-md)",
        background: "var(--color-zinc-100)",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{label}</div>
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
