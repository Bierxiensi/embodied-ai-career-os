"use client";

import { forwardRef, type InputHTMLAttributes } from "react";

interface RadioProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  label?: string;
}

const Radio = forwardRef<HTMLInputElement, RadioProps>(
  ({ label, style, disabled, ...rest }, ref) => {
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
          type="radio"
          disabled={disabled}
          style={{ display: "none" }}
          {...rest}
        />
        <span
          style={{
            width: 18,
            height: 18,
            borderRadius: "50%",
            border: `2px solid var(--border-default)`,
            background: "var(--surface-card)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "120ms ease-out",
            flexShrink: 0,
          }}
        />
        {label}
      </label>
    );
  }
);

Radio.displayName = "Radio";
export default Radio;
