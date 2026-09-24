/** 骨架屏占位块。 */
export function SkeletonLine({ width = "100%", height = 14 }: { width?: string | number; height?: number }) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius: "var(--radius-sm)",
        background: "var(--border-subtle)",
        animation: "pulse 1.5s ease-in-out infinite",
      }}
    />
  );
}

/** 卡片骨架屏 — 替代完整卡片的 loading 状态。 */
export function SkeletonCard({ height = 120 }: { height?: number }) {
  return (
    <div
      style={{
        height,
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--spacing-lg)",
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      <SkeletonLine width="40%" />
      <SkeletonLine width="80%" />
      <SkeletonLine width="60%" />
    </div>
  );
}
