"use client";

/** 全局错误边界 — 页面渲染阶段抛出的异常在此兜底。 */

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main
      className="flex flex-1 items-center justify-center"
      style={{ background: "var(--color-canvas)" }}
    >
      <div
        className="max-w-md text-center"
        style={{
          padding: 32,
          background: "var(--color-card)",
          border: "1px solid var(--color-rose)",
          borderRadius: "var(--radius-card-lg)",
        }}
      >
        <h1
          className="text-lg font-semibold"
          style={{ color: "var(--color-rose-deep)" }}
        >
          页面出错了
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
          {error.message || "发生了未知错误"}
        </p>
        <button
          onClick={reset}
          className="mt-4 border-none text-sm font-medium"
          style={{
            padding: "8px 20px",
            borderRadius: "var(--radius-pill)",
            background: "var(--color-primary-soft)",
            color: "var(--color-primary)",
            cursor: "pointer",
          }}
        >
          重试
        </button>
      </div>
    </main>
  );
}
