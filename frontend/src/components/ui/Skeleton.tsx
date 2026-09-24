"use client";

type Variant = "text" | "circular" | "rectangular";

interface SkeletonProps {
  variant?: Variant;
  width?: number | string;
  height?: number;
  lines?: number;
  className?: string;
  style?: React.CSSProperties;
}

export default function Skeleton({ variant = "text", width, height, lines, className, style }: SkeletonProps) {
  if (variant === "text" && lines && lines > 1) {
    return (
      <div className={className} style={{ display: "flex", flexDirection: "column", gap: 8, ...style }}>
        {Array.from({ length: lines }, (_, i) => (
          <div
            key={i}
            style={{
              width: i === lines - 1 ? "60%" : width ?? "100%",
              height: height ?? 14,
              borderRadius: "var(--radius-item)",
              background: "var(--border-subtle)",
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          />
        ))}
      </div>
    );
  }

  const shapeStyles: Record<Variant, React.CSSProperties> = {
    text: { width: width ?? "100%", height: height ?? 14, borderRadius: "var(--radius-item)" },
    circular: { width: width ?? 40, height: width ?? 40, borderRadius: "50%" },
    rectangular: { width: width ?? "100%", height: height ?? 120, borderRadius: "var(--radius-item)" },
  };

  return (
    <div
      className={className}
      style={{
        ...shapeStyles[variant],
        background: "var(--border-subtle)",
        animation: "pulse 1.5s ease-in-out infinite",
        ...style,
      }}
    />
  );
}
