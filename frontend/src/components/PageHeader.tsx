import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  /** 小写字距标签，如 "PROJECTS · 实践项目" */
  eyebrow: string;
  /** H1 标题 */
  title: string;
  /** 一句话副标题 */
  subtitle?: string;
  /** 标题下方的补充内容（如切换器、状态徽章行） */
  children?: ReactNode;
  /** 右上角操作区 */
  actions?: ReactNode;
  /** 返回链接（详情页用） */
  backHref?: string;
  backLabel?: string;
};

/** 页面头部 —— 全站统一的 eyebrow + H1 + subtitle 结构。
 *
 * 为什么抽出来（2026-09-10 修复「项目界面和其他风格不一致」）：
 *   各看板此前把这段结构各写一份，`/projects` 漏写且自己发明了一套
 *   zinc-50/dark 配色，成了全站唯一的异类。抽成组件后，
 *   标题层级（40px/ink/-0.02em）、字距、间距都有单一定义。
 *
 * 尺寸口径与 `JobsBoard` / `Dashboard` 的页头一致，改动这里即全站生效。
 */
export default function PageHeader({
  eyebrow,
  title,
  subtitle,
  children,
  actions,
  backHref,
  backLabel,
}: Props) {
  return (
    <div className="flex flex-col" style={{ gap: 10 }}>
      {backHref && (
        <Link
          href={backHref}
          className="self-start text-xs font-medium no-underline"
          style={{ color: "var(--color-primary)" }}
        >
          ← {backLabel ?? "返回"}
        </Link>
      )}

      <div className="flex items-start justify-between" style={{ gap: 24 }}>
        <div className="flex flex-col" style={{ gap: 10, minWidth: 0 }}>
          <span
            className="text-xs font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            {eyebrow}
          </span>
          <h1
            className="font-semibold"
            style={{
              fontSize: 40,
              lineHeight: 1.15,
              color: "var(--color-ink)",
              letterSpacing: "-0.02em",
            }}
          >
            {title}
          </h1>
          {subtitle && (
            <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
              {subtitle}
            </p>
          )}
          {children}
        </div>
        {actions && <div className="flex shrink-0 items-center">{actions}</div>}
      </div>
    </div>
  );
}
