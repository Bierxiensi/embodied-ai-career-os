"use client";

interface ToggleProps {
  checked?: boolean;
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  size?: "sm" | "md";
  className?: string;
  style?: React.CSSProperties;
}

export default function Toggle({ checked = false, onChange, disabled, size = "md", className, style }: ToggleProps) {
  const dims = size === "sm" ? { w: 36, h: 20, knob: 16, offset: 2 } : { w: 44, h: 24, knob: 20, offset: 2 };

  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
      className={className}
      style={{
        position: "relative",
        width: dims.w,
        height: dims.h,
        borderRadius: dims.h,
        border: "none",
        background: checked ? "var(--accent-primary)" : "var(--border-default)",
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        transition: "200ms ease-out",
        flexShrink: 0,
        ...style,
      }}
    >
      <span
        style={{
          position: "absolute",
          top: dims.offset,
          left: checked ? dims.w - dims.knob - dims.offset : dims.offset,
          width: dims.knob,
          height: dims.knob,
          borderRadius: "50%",
          background: "var(--surface-card)",
          transition: "200ms ease-out",
          boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        }}
      />
    </button>
  );
}
