"use client";

import { forwardRef, type InputHTMLAttributes } from "react";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  indeterminate?: boolean;
  label?: string;
}

const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ indeterminate, label, style, disabled, ...rest }, ref) => {
    return (
      <label
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 8,
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.5 : 1,
          fontSize: 13,
          color: "var(--text-primary)",
          ...style,
        }}
      >
        <input
          ref={ref}
          type="checkbox"
          disabled={disabled}
          style={{ display: "none" }}
          {...rest}
        />
        <span
          style={{
            width: 18,
            height: 18,
            borderRadius: 4,
            border: `2px solid var(--border-default)`,
            background: "var(--surface-card)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "120ms ease-out",
            flexShrink: 0,
          }}
        >
          {/* 通过 CSS sibling selector 或 controlled state 显示勾选 */}
        </span>
        {label}
      </label>
    );
  }
);

Checkbox.displayName = "Checkbox";
export default Checkbox;
