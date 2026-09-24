"use client";

import type { ReactNode } from "react";

type Status = "done" | "current" | "pending";

interface TimelineItem {
  title: string;
  description?: string;
  time?: string;
  icon?: ReactNode;
  status?: Status;
}

interface TimelineProps {
  items: TimelineItem[];
  className?: string;
  style?: React.CSSProperties;
}

const statusColors: Record<Status, { bg: string; fg: string; line: string }> = {
  done: { bg: "var(--accent-success-soft)", fg: "var(--accent-success)", line: "var(--accent-success)" },
  current: { bg: "var(--accent-primary-soft)", fg: "var(--accent-primary)", line: "var(--border-subtle)" },
  pending: { bg: "var(--border-subtle)", fg: "var(--text-muted)", line: "var(--border-subtle)" },
};

export default function Timeline({ items, className, style }: TimelineProps) {
  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", ...style }}>
      {items.map((item, i) => {
        const status = item.status ?? "pending";
        const c = statusColors[status];
        const isLast = i === items.length - 1;

        return (
          <div key={i} style={{ display: "flex", gap: 12 }}>
            {/* 节点列 */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 28 }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  background: c.bg,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {item.icon ? (
                  <span style={{ color: c.fg, fontSize: 12, display: "flex" }}>{item.icon}</span>
                ) : (
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: c.fg,
                    }}
                  />
                )}
              </div>
              {!isLast && (
                <div
                  style={{
                    width: 2,
                    flex: 1,
                    background: c.line,
                    minHeight: 16,
                  }}
                />
              )}
            </div>

            {/* 内容列 */}
            <div style={{ paddingBottom: isLast ? 0 : 16, flex: 1 }}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: status === "current" ? 600 : 500,
                    color: status === "pending" ? "var(--text-muted)" : "var(--text-primary)",
                  }}
                >
                  {item.title}
                </span>
                {item.time && (
                  <span style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0 }}>
                    {item.time}
                  </span>
                )}
              </div>
              {item.description && (
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0", lineHeight: 1.5 }}>
                  {item.description}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
