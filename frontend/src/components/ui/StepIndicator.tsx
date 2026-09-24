"use client";

type StepStatus = "done" | "current" | "pending";
type Orientation = "horizontal" | "vertical";

interface Step {
  title: string;
  status: StepStatus;
}

interface StepIndicatorProps {
  steps: Step[];
  orientation?: Orientation;
  className?: string;
  style?: React.CSSProperties;
}

const statusColors: Record<StepStatus, { bg: string; fg: string; border: string }> = {
  done: { bg: "var(--accent-success-soft)", fg: "var(--accent-success)", border: "var(--accent-success)" },
  current: { bg: "var(--accent-primary-soft)", fg: "var(--accent-primary)", border: "var(--accent-primary)" },
  pending: { bg: "var(--surface-card)", fg: "var(--text-muted)", border: "var(--border-default)" },
};

export default function StepIndicator({ steps, orientation = "horizontal", className, style }: StepIndicatorProps) {
  const isH = orientation === "horizontal";

  return (
    <div
      className={className}
      style={{
        display: "flex",
        flexDirection: isH ? "row" : "column",
        gap: 0,
        ...style,
      }}
    >
      {steps.map((step, i) => {
        const c = statusColors[step.status];
        const isLast = i === steps.length - 1;

        return (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: isH ? "center" : "flex-start",
              flexDirection: isH ? "row" : "column",
              flex: isH ? 1 : undefined,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  border: `2px solid ${c.border}`,
                  background: c.bg,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 12,
                  fontWeight: 600,
                  color: c.fg,
                  flexShrink: 0,
                }}
              >
                {step.status === "done" ? "✓" : i + 1}
              </div>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: step.status === "current" ? 600 : 400,
                  color: step.status === "pending" ? "var(--text-muted)" : "var(--text-primary)",
                }}
              >
                {step.title}
              </span>
            </div>
            {!isLast && (
              <div
                style={{
                  flex: isH ? 1 : undefined,
                  height: isH ? 2 : 20,
                  width: isH ? undefined : 2,
                  background: step.status === "done" ? "var(--accent-success)" : "var(--border-subtle)",
                  margin: isH ? "0 12px" : "4px 0 4px 13px",
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
