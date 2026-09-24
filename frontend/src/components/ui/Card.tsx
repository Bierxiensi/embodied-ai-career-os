"use client";

import { forwardRef, type HTMLAttributes, type ReactNode } from "react";

type Variant = "default" | "elevated" | "outlined" | "ghost";
type Padding = "sm" | "md" | "lg" | "none";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
  padding?: Padding;
  hoverable?: boolean;
  header?: ReactNode;
  footer?: ReactNode;
}

const paddingMap: Record<Padding, string> = {
  none: "0",
  sm: "12px",
  md: "20px",
  lg: "28px",
};

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ variant = "default", padding = "md", hoverable, header, footer, children, style, ...rest }, ref) => {
    const baseStyle: React.CSSProperties = {
      borderRadius: "var(--radius-card)",
      transition: "200ms ease-out",
      overflow: "hidden",
    };

    const variantStyles: Record<Variant, React.CSSProperties> = {
      default: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        boxShadow: "var(--shadow-card)",
      },
      elevated: {
        background: "var(--surface-elevated)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-elevated)",
      },
      outlined: {
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        boxShadow: "none",
      },
      ghost: {
        background: "transparent",
        border: "none",
        boxShadow: "none",
      },
    };

    return (
      <div
        ref={ref}
        style={{ ...baseStyle, ...variantStyles[variant], ...style }}
        onMouseEnter={(e) => {
          if (hoverable) {
            e.currentTarget.style.transform = "translateY(-2px)";
            e.currentTarget.style.boxShadow = "var(--shadow-elevated)";
          }
        }}
        onMouseLeave={(e) => {
          if (hoverable) {
            e.currentTarget.style.transform = "translateY(0)";
            e.currentTarget.style.boxShadow = variantStyles[variant].boxShadow || "none";
          }
        }}
        {...rest}
      >
        {header && (
          <div style={{ padding: paddingMap[padding], borderBottom: "1px solid var(--border-subtle)" }}>
            {header}
          </div>
        )}
        <div style={{ padding: paddingMap[padding] }}>{children}</div>
        {footer && (
          <div style={{ padding: paddingMap[padding], borderTop: "1px solid var(--border-subtle)" }}>
            {footer}
          </div>
        )}
      </div>
    );
  }
);

Card.displayName = "Card";

export default Card;
