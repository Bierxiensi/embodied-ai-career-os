"use client";

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

const sizeStyles: Record<Size, React.CSSProperties> = {
  sm: { padding: "6px 12px", fontSize: 12, borderRadius: "var(--radius-item)" },
  md: { padding: "8px 18px", fontSize: 13, borderRadius: "var(--radius-item)" },
  lg: { padding: "12px 24px", fontSize: 15, borderRadius: "var(--radius-item)" },
};

const variantStyles: Record<Variant, React.CSSProperties> = {
  primary: {
    background: "var(--accent-primary)",
    color: "var(--text-inverse)",
    border: "none",
  },
  secondary: {
    background: "transparent",
    color: "var(--text-primary)",
    border: "1px solid var(--border-default)",
  },
  ghost: {
    background: "transparent",
    color: "var(--text-secondary)",
    border: "none",
  },
  danger: {
    background: "var(--accent-danger)",
    color: "var(--text-inverse)",
    border: "none",
  },
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", loading, icon, children, style, disabled, ...rest }, ref) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 6,
          fontWeight: 600,
          cursor: isDisabled ? "not-allowed" : "pointer",
          opacity: isDisabled ? 0.5 : 1,
          transition: "120ms ease-out",
          whiteSpace: "nowrap",
          lineHeight: 1.4,
          ...sizeStyles[size],
          ...variantStyles[variant],
          ...style,
        }}
        onMouseEnter={(e) => {
          if (!isDisabled) {
            e.currentTarget.style.transform = "translateY(-1px)";
            if (variant === "primary") {
              e.currentTarget.style.background = "var(--accent-primary-hover)";
            }
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = "translateY(0)";
          if (variant === "primary") {
            e.currentTarget.style.background = "var(--accent-primary)";
          }
        }}
        onMouseDown={(e) => {
          if (!isDisabled) {
            e.currentTarget.style.transform = "scale(0.98)";
          }
        }}
        onMouseUp={(e) => {
          e.currentTarget.style.transform = "translateY(-1px)";
        }}
        {...rest}
      >
        {loading ? (
          <span style={{ animation: "pulse 1.5s ease-in-out infinite" }}>⏳</span>
        ) : icon ? (
          <span style={{ display: "flex", alignItems: "center" }}>{icon}</span>
        ) : null}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

export default Button;
