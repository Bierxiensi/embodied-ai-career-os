"use client";

import { useState } from "react";
import type { AgentRunRecord } from "@/types";
import { agentColorToken, agentLabel } from "@/lib/agentTheme";
import AgentActivityCard from "./AgentActivityCard";

type Props = {
  runs: AgentRunRecord[];
};

/** 已知的 Agent 清单（与后端 agent_name 对齐）。 */
const KNOWN_AGENTS = ["planner", "reviewer", "career", "research", "supervisor"] as const;

function calcStats(runs: AgentRunRecord[]) {
  const total = runs.length;
  const success = runs.filter((r) => r.status === "success").length;
  const rate = total > 0 ? Math.round((success / total) * 100) : 0;
  const avgMs =
    total > 0 ? Math.round(runs.reduce((s, r) => s + r.durationMs, 0) / total) : 0;
  return { total, success, rate, avgMs };
}

/** Agent 应用一级页面主体：Agent 总览 + 可过滤的执行动态。 */
export default function AgentOverview({ runs }: Props) {
  const [filter, setFilter] = useState<string | null>(null);

  const visible = filter ? runs.filter((r) => r.agentName === filter) : runs;
  const overview = calcStats(runs);

  return (
    <div className="flex flex-col" style={{ gap: "var(--spacing-lg)" }}>
      {/* 概览统计条 */}
      <div className="flex flex-wrap" style={{ gap: "var(--spacing-md)" }}>
        <StatCard label="总调用" value={String(overview.total)} />
        <StatCard label="成功率" value={`${overview.rate}%`} tone="emerald" />
        <StatCard label="失败数" value={String(overview.total - overview.success)} tone={overview.total - overview.success > 0 ? "rose" : undefined} />
        <StatCard label="平均耗时" value={`${(overview.avgMs / 1000).toFixed(1)}s`} />
      </div>

      {/* Agent 选择器 */}
      <div className="flex flex-wrap items-center" style={{ gap: 10 }}>
        <FilterChip
          active={filter === null}
          label="全部"
          onClick={() => setFilter(null)}
          color="var(--color-ink-48)"
        />
        {KNOWN_AGENTS.map((name) => {
          const count = runs.filter((r) => r.agentName === name).length;
          if (count === 0 && filter !== name) return null;
          return (
            <FilterChip
              key={name}
              active={filter === name}
              label={`${agentLabel(name)} · ${count}`}
              onClick={() => setFilter(filter === name ? null : name)}
              color={agentColorToken(name)}
            />
          );
        })}
      </div>

      {/* 可交互的执行动态（支持展开 trace + 失败重试） */}
      <AgentActivityCard runs={visible} interactive={true} />
    </div>
  );
}

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "emerald" | "rose";
}) {
  return (
    <div
      className="flex flex-col"
      style={{
        flex: "1 1 140px",
        gap: 6,
        padding: 18,
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <span className="text-sm" style={{ color: "var(--color-ink-48)" }}>
        {label}
      </span>
      <span
        className="font-semibold"
        style={{
          fontSize: 28,
          color:
            tone === "emerald"
              ? "var(--color-emerald-deep)"
              : tone === "rose"
                ? "var(--color-rose-deep)"
                : "var(--color-ink)",
          letterSpacing: "-0.01em",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function FilterChip({
  active,
  label,
  onClick,
  color,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  color: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center border-none"
      style={{
        gap: 8,
        height: 34,
        paddingInline: 14,
        borderRadius: "var(--radius-pill)",
        cursor: "pointer",
        background: active ? "var(--color-ink)" : "var(--color-card)",
        border: `1px solid ${active ? "var(--color-ink)" : "var(--color-hairline)"}`,
        color: active ? "var(--color-card)" : "var(--color-ink-80)",
        fontSize: 13,
        fontWeight: 500,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "var(--radius-pill)",
          background: color,
          display: "inline-block",
        }}
      />
      {label}
    </button>
  );
}
