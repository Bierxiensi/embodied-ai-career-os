"use client";

import type { ReactNode } from "react";

type Variant = "default" | "primary" | "success" | "warning" | "danger" | "info";
type Size = "sm" | "md";

interface BadgeProps {
  variant?: Variant;
  size?: Size;
  dot?: boolean;
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const variantMap: Record<Variant, { bg: string; fg: string }> = {
  default: { bg: "var(--surface-card)", fg: "var(--text-muted)" },
  primary: { bg: "var(--accent-primary-soft)", fg: "var(--accent-primary)" },
  success: { bg: "var(--accent-success-soft)", fg: "var(--accent-success)" },
  warning: { bg: "var(--accent-warning-soft)", fg: "var(--accent-warning)" },
  danger: { bg: "var(--accent-danger-soft)", fg: "var(--accent-danger)" },
  info: { bg: "var(--accent-primary-soft)", fg: "var(--accent-primary)" },
};

const sizeMap: Record<Size, React.CSSProperties> = {
  sm: { padding: "2px 8px", fontSize: 11 },
  md: { padding: "3px 10px", fontSize: 12 },
};

export default function Badge({ variant = "default", size = "sm", dot, children, className, style }: BadgeProps) {
  const v = variantMap[variant];
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: sizeMap[size].padding,
        fontSize: sizeMap[size].fontSize,
        fontWeight: 600,
        borderRadius: "var(--radius-pill)",
        background: v.bg,
        color: v.fg,
        whiteSpace: "nowrap",
        lineHeight: 1.4,
        ...style,
      }}
    >
      {dot && (
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: v.fg,
          }}
        />
      )}
      {children}
    </span>
  );
}
