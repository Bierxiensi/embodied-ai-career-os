"use client";

import type { ReactNode } from "react";

type Variant = "default" | "primary" | "success" | "warning" | "danger";

interface TagProps {
  variant?: Variant;
  closable?: boolean;
  onClose?: () => void;
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
};

export default function Tag({ variant = "default", closable, onClose, children, className, style }: TagProps) {
  const v = variantMap[variant];
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "4px 10px",
        fontSize: 12,
        fontWeight: 500,
        borderRadius: "var(--radius-item)",
        background: v.bg,
        color: v.fg,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
      {closable && (
        <button
          onClick={onClose}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 14,
            height: 14,
            borderRadius: "50%",
            border: "none",
            background: "transparent",
            color: v.fg,
            cursor: "pointer",
            fontSize: 10,
            lineHeight: 1,
            opacity: 0.7,
            transition: "120ms ease-out",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = "1"; }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = "0.7"; }}
          aria-label="关闭"
        >
          ✕
        </button>
      )}
    </span>
  );
}
