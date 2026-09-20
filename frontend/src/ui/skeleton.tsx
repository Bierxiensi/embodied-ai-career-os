/** 骨架屏占位块。 */
export function SkeletonLine({ width = "100%", height = 14 }: { width?: string | number; height?: number }) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius: "var(--radius-item-sm)",
        background: "var(--color-hairline-soft)",
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
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
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
