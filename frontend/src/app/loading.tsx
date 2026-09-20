import { SkeletonCard } from "@/ui/skeleton";

/** 全局 loading 骨架屏 — 所有 force-dynamic 页面加载时展示。 */
export default function Loading() {
  return (
    <main
      className="flex flex-1 flex-col"
      style={{ background: "var(--color-canvas)", padding: "36px clamp(20px, 8vw, 120px) 48px", gap: 16 }}
    >
      <SkeletonCard height={80} />
      <div className="flex" style={{ gap: 16 }}>
        <SkeletonCard height={140} />
        <SkeletonCard height={140} />
        <SkeletonCard height={140} />
      </div>
      <SkeletonCard height={200} />
    </main>
  );
}
