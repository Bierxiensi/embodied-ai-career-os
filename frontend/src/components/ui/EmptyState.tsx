"use client";

import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  className?: string;
  style?: React.CSSProperties;
}

export default function EmptyState({ icon, title, description, action, className, style }: EmptyStateProps) {
  return (
    <div
      className={className}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        ...style,
      }}
    >
      {icon && (
        <div style={{ fontSize: 40, marginBottom: 16, opacity: 0.5 }}>{icon}</div>
      )}
      <h3 style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
        {title}
      </h3>
      {description && (
        <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 8, maxWidth: 320 }}>
          {description}
        </p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          style={{
            marginTop: 20,
            padding: "8px 20px",
            fontSize: 13,
            fontWeight: 600,
            borderRadius: "var(--radius-item)",
            border: "none",
            background: "var(--accent-primary)",
            color: "var(--text-inverse)",
            cursor: "pointer",
            transition: "120ms ease-out",
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
