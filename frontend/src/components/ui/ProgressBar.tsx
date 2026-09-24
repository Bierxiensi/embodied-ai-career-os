"use client";

type Variant = "default" | "success" | "warning" | "danger";
type Size = "sm" | "md";

interface ProgressBarProps {
  value: number;
  variant?: Variant;
  size?: Size;
  showLabel?: boolean;
  segments?: Array<{ value: number; variant: Variant }>;
  className?: string;
  style?: React.CSSProperties;
}

const variantColor: Record<Variant, string> = {
  default: "var(--accent-primary)",
  success: "var(--accent-success)",
  warning: "var(--accent-warning)",
  danger: "var(--accent-danger)",
};

export default function ProgressBar({
  value,
  variant = "default",
  size = "md",
  showLabel,
  segments,
  className,
  style,
}: ProgressBarProps) {
  const h = size === "sm" ? 4 : 8;
  const pct = Math.min(100, Math.max(0, value));

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", gap: 4, ...style }}>
      {showLabel && (
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)" }}>
          <span>进度</span>
          <span style={{ fontVariantNumeric: "tabular-nums" }}>{pct}%</span>
        </div>
      )}
      <div
        style={{
          height: h,
          width: "100%",
          borderRadius: "var(--radius-pill)",
          background: "var(--border-subtle)",
          overflow: "hidden",
        }}
      >
        {segments ? (
          segments.map((seg, i) => (
            <div
              key={i}
              style={{
                display: "inline-block",
                height: "100%",
                width: `${Math.min(100, Math.max(0, seg.value))}%`,
                background: variantColor[seg.variant],
                transition: "200ms ease-out",
              }}
            />
          ))
        ) : (
          <div
            style={{
              height: "100%",
              width: `${pct}%`,
              background: variantColor[variant],
              borderRadius: "var(--radius-pill)",
              transition: "200ms ease-out",
            }}
          />
        )}
      </div>
    </div>
  );
}
