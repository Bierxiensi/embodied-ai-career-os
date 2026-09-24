"use client";

import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";

type Size = "sm" | "md" | "lg";

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size" | "prefix"> {
  size?: Size;
  prefix?: ReactNode;
  suffix?: ReactNode;
  error?: string;
}

const sizeMap: Record<Size, { padding: string; fontSize: number }> = {
  sm: { padding: "6px 10px", fontSize: 12 },
  md: { padding: "8px 12px", fontSize: 13 },
  lg: { padding: "12px 16px", fontSize: 15 },
};

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ size = "md", prefix, suffix, error, style, disabled, ...rest }, ref) => {
    const s = sizeMap[size];

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: s.padding,
            fontSize: s.fontSize,
            borderRadius: "var(--radius-item)",
            border: `1px solid ${error ? "var(--border-error)" : "var(--border-default)"}`,
            background: disabled ? "var(--surface-card)" : "var(--surface-card)",
            color: "var(--text-primary)",
            opacity: disabled ? 0.5 : 1,
            transition: "120ms ease-out",
            cursor: disabled ? "not-allowed" : "text",
          }}
          onFocus={(e) => {
            if (!disabled) {
              e.currentTarget.style.borderColor = error ? "var(--border-error)" : "var(--border-focus)";
              e.currentTarget.style.boxShadow = `0 0 0 2px ${error ? "var(--accent-danger-soft)" : "var(--accent-primary-soft)"}`;
            }
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = error ? "var(--border-error)" : "var(--border-default)";
            e.currentTarget.style.boxShadow = "none";
          }}
        >
          {prefix && (
            <span style={{ display: "flex", alignItems: "center", color: "var(--text-muted)" }}>
              {prefix}
            </span>
          )}
          <input
            ref={ref}
            disabled={disabled}
            style={{
              flex: 1,
              border: "none",
              background: "transparent",
              color: "inherit",
              fontSize: "inherit",
              outline: "none",
              width: "100%",
              ...style,
            }}
            {...rest}
          />
          {suffix && (
            <span style={{ display: "flex", alignItems: "center", color: "var(--text-muted)" }}>
              {suffix}
            </span>
          )}
        </div>
        {error && (
          <span style={{ fontSize: 11, color: "var(--accent-danger)" }}>{error}</span>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;
