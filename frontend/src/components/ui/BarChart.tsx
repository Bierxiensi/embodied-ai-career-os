"use client";

type Orientation = "horizontal" | "vertical";

interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  data: BarItem[];
  orientation?: Orientation;
  showValues?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

export default function BarChart({
  data,
  orientation = "vertical",
  showValues = true,
  className,
  style,
}: BarChartProps) {
  const maxValue = Math.max(...data.map((d) => d.value), 1);

  if (orientation === "horizontal") {
    return (
      <div className={className} style={{ display: "flex", flexDirection: "column", gap: 8, ...style }}>
        {data.map((item, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, color: "var(--text-secondary)", minWidth: 60, flexShrink: 0 }}>
              {item.label}
            </span>
            <div style={{ flex: 1, height: 20, background: "var(--border-subtle)", borderRadius: "var(--radius-pill)", overflow: "hidden" }}>
              <div
                style={{
                  height: "100%",
                  width: `${(item.value / maxValue) * 100}%`,
                  background: item.color ?? "var(--accent-primary)",
                  borderRadius: "var(--radius-pill)",
                  transition: "200ms ease-out",
                }}
              />
            </div>
            {showValues && (
              <span style={{ fontSize: 12, color: "var(--text-muted)", minWidth: 32, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                {item.value}
              </span>
            )}
          </div>
        ))}
      </div>
    );
  }

  // vertical
  return (
    <div className={className} style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 160, ...style }}>
      {data.map((item, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1, gap: 4, height: "100%", justifyContent: "flex-end" }}>
          {showValues && (
            <span style={{ fontSize: 11, color: "var(--text-muted)", fontVariantNumeric: "tabular-nums" }}>
              {item.value}
            </span>
          )}
          <div
            style={{
              width: "100%",
              maxWidth: 48,
              height: `${(item.value / maxValue) * 100}%`,
              background: item.color ?? "var(--accent-primary)",
              borderRadius: "var(--radius-sm) var(--radius-sm) 0 0",
              transition: "200ms ease-out",
              minHeight: 2,
            }}
          />
          <span style={{ fontSize: 11, color: "var(--text-secondary)", textAlign: "center", lineHeight: 1.3 }}>
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
