"use client";

import type { ReactNode } from "react";

type Size = "sm" | "md" | "lg";

interface StatProps {
  label: string;
  value: string | number;
  change?: { value: number; direction: "up" | "down" };
  icon?: ReactNode;
  size?: Size;
  className?: string;
  style?: React.CSSProperties;
}

const sizeMap: Record<Size, { valueSize: number; labelSize: number }> = {
  sm: { valueSize: 20, labelSize: 11 },
  md: { valueSize: 28, labelSize: 12 },
  lg: { valueSize: 36, labelSize: 13 },
};

export default function Stat({ label, value, change, icon, size = "md", className, style }: StatProps) {
  const s = sizeMap[size];

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", gap: 4, ...style }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {icon && <span style={{ color: "var(--text-muted)" }}>{icon}</span>}
        <span style={{ fontSize: s.labelSize, color: "var(--text-muted)", fontWeight: 500 }}>{label}</span>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span
          style={{
            fontSize: s.valueSize,
            fontWeight: 700,
            color: "var(--text-primary)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {value}
        </span>
        {change && (
          <span
            style={{
              fontSize: s.labelSize,
              fontWeight: 600,
              color: change.direction === "up" ? "var(--accent-success)" : "var(--accent-danger)",
            }}
          >
            {change.direction === "up" ? "↑" : "↓"} {change.value}%
          </span>
        )}
      </div>
    </div>
  );
}
