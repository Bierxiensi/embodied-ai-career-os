import Link from "next/link";

/** 全局 404 页面。 */
export default function NotFound() {
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
          border: "1px solid var(--color-hairline)",
          borderRadius: "var(--radius-card-lg)",
        }}
      >
        <h1
          className="font-semibold"
          style={{ fontSize: 48, color: "var(--color-ink)", letterSpacing: "-0.02em" }}
        >
          404
        </h1>
        <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
          页面不存在
        </p>
        <Link
          href="/today"
          className="mt-4 inline-block border-none text-sm font-medium no-underline"
          style={{
            padding: "8px 20px",
            borderRadius: "var(--radius-pill)",
            background: "var(--color-primary-soft)",
            color: "var(--color-primary)",
          }}
        >
          回到今日
        </Link>
      </div>
    </main>
  );
}
