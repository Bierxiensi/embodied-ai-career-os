import Link from "next/link";

/** 全局 404 页面。 */
export default function NotFound() {
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
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-lg)",
        }}
      >
        <h1
          className="font-semibold"
          style={{ fontSize: 48, color: "var(--text-primary)", letterSpacing: "-0.02em" }}
        >
          404
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
          页面不存在
        </p>
        <Link
          href="/today"
          className="mt-4 inline-block border-none text-sm font-medium no-underline"
          style={{
            padding: "8px 20px",
            borderRadius: "var(--radius-pill)",
            background: "var(--accent-primary-soft)",
            color: "var(--accent-primary)",
          }}
        >
          回到今日
        </Link>
      </div>
    </main>
  );
}
