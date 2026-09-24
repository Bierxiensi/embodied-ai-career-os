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
      style={{ background: "var(--surface-canvas)" }}
    >
      <div
        className="max-w-md text-center"
        style={{
          padding: 32,
          background: "var(--surface-card)",
          border: "1px solid var(--accent-danger)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <h1
          className="text-lg font-semibold"
          style={{ color: "var(--accent-danger)" }}
        >
          页面出错了
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
          {error.message || "发生了未知错误"}
        </p>
        <button
          onClick={reset}
          className="mt-4 border-none text-sm font-medium"
          style={{
            padding: "8px 20px",
            borderRadius: "var(--radius-pill)",
            background: "var(--accent-primary-soft)",
            color: "var(--accent-primary)",
            cursor: "pointer",
          }}
        >
          重试
        </button>
      </div>
    </main>
  );
}
