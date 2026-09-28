"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import ModeSwitcher from "@/components/ModeSwitcher";
import ThemeSwitcher from "@/theme/ThemeSwitcher";
import { useCareerMode } from "@/lib/careerModeContext";
import { PALETTE_ITEMS, PRIMARY_NAV } from "@/lib/nav";

/** 求职模式下的二级路由（用于 isActive 前缀匹配）。 */
const JOB_HUNT_ROUTES = ["/jobs", "/jd", "/resume", "/interview"];
/** 三问入口（学/习/证）——数据源为 nav.ts 单一真源，高亮按前缀匹配。 */
const LEARN_ROUTES = PRIMARY_NAV.map((n) => n.href);
/** 求职入口 —— 同样取自 PALETTE_ITEMS（nav.ts 单一真源），不再手写 label/hint。 */
const JOB_NAV_ITEM = PALETTE_ITEMS.find((p) => p.href === "/jobs");

/** 全局导航栏 — 三问三入口（学/习/证，nav.ts 单一真源），随 CareerMode 联动求职入口。
 *
 * 求职模式：学 | 习 | 证 | 求职
 * 长期模式：学 | 习 | 证（隐藏求职入口）
 * 低频入口收敛到 CommandPalette + /stages（见 lib/nav.ts）。
 */
export default function GlobalNav() {
  const pathname = usePathname();
  const { current } = useCareerMode();
  const modeKey = current?.key ?? "job_hunt";

  const isJobHunt = modeKey === "job_hunt";

  // 三问三入口来自 nav.ts；求职入口随模式显隐（模式联动保留）
  const links = [
    ...PRIMARY_NAV,
    ...(isJobHunt && JOB_NAV_ITEM ? [JOB_NAV_ITEM] : []),
  ];

  const isActive = (href: string) => {
    // / 与旧 /today 均落到 /learn
    if (href === "/learn" && (pathname === "/" || pathname === "/today")) return true;
    if (href === "/jobs") return JOB_HUNT_ROUTES.some((p) => pathname.startsWith(p));
    if (LEARN_ROUTES.includes(href)) return pathname.startsWith(href);
    return pathname === href;
  };

  return (
    <nav
      className="flex items-center justify-between"
      style={{
        height: 44,
        paddingInline: 24,
        background: "#000000",
        position: "relative",
        zIndex: 100,
      }}
    >
      {/* Left cluster: Logo + Wordmark + Links */}
      <div className="flex items-center" style={{ gap: 28 }}>
        <div className="relative" style={{ width: 20, height: 20 }}>
          <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="4" fill="var(--accent-primary)" />
            <circle cx="13" cy="13" r="4" fill="var(--accent-success)" />
            <path d="M7 7L13 13" stroke="var(--text-primary)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <span className="text-[13px] font-semibold" style={{ color: "var(--surface-canvas)" }}>
          Career OS
        </span>
        <div className="flex" style={{ gap: 28 }}>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              title={l.hint}
              className={`text-xs font-medium no-underline ${
                isActive(l.href) ? "text-white" : "text-[#787880]"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Right cluster: 当前阶段 + Search + Avatar */}
      <div className="flex items-center" style={{ gap: 18 }}>
        <ThemeSwitcher />
        <ModeSwitcher />
        <div style={{ width: 16, height: 16 }}>
          <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="5" stroke="var(--text-muted)" strokeWidth="1.5" />
            <path d="M11 11L15 15" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <div
          className="rounded-full"
          style={{ width: 26, height: 26, background: "var(--accent-primary)" }}
        />
      </div>
    </nav>
  );
}
