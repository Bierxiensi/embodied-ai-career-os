import type { ReactNode } from "react";

type Props = {
  /** 页面顶部小标题（如 "EVIDENCE · 技能证据链"）。 */
  eyebrow?: string;
  /** 页面主标题。 */
  title: string;
  /** 页面副标题。 */
  subtitle?: string;
  /** 页面内容。 */
  children: ReactNode;
};

/** 统一的页面布局外壳。
 *
 * 所有页面共用，保证：
 *   - max-width 一致（1180px）
 *   - padding 一致
 *   - 标题层级一致
 *
 * Dashboard 不使用此组件（它有自己的布局），其他页面统一使用。
 */
export default function PageShell({ eyebrow, title, subtitle, children }: Props) {
  return (
    <main className="flex flex-1 flex-col" style={{ background: "var(--color-canvas)" }}>
      <div
        className="mx-auto flex w-full max-w-[1180px] flex-col"
        style={{ padding: "36px clamp(20px, 8vw, 120px) 56px", gap: "var(--spacing-lg)" }}
      >
        {eyebrow && (
          <span
            className="text-xs font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            {eyebrow}
          </span>
        )}
        <h1
          className="font-semibold"
          style={{
            fontSize: "var(--font-size-hero)",
            color: "var(--color-ink)",
            letterSpacing: "-0.02em",
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p className="text-sm" style={{ color: "var(--color-ink-48)" }}>
            {subtitle}
          </p>
        )}
        {children}
      </div>
    </main>
  );
}
