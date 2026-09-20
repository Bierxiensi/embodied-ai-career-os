"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import ModeSwitcher from "@/components/ModeSwitcher";
import { useCareerMode } from "@/lib/careerModeContext";

/** 求职模式下的二级路由（用于 isActive 前缀匹配）。 */
const JOB_HUNT_ROUTES = ["/jobs", "/jd", "/resume", "/interview", "/reports"];
/** 学习模式下的二级路由。 */
const LEARN_ROUTES = ["/plan", "/projects", "/questions", "/experiments", "/evidence", "/agents"];

/** 全局导航栏 — 顶栏 4 个一级入口，随 CareerMode 动态调整。
 *
 * 求职模式：今日 | 求职 | 学习 | 概览
 * 长期模式：今日 | 学习 | 概览（隐藏求职入口）
 */
export default function GlobalNav() {
  const pathname = usePathname();
  const { current } = useCareerMode();
  const modeKey = current?.key ?? "job_hunt";

  const isJobHunt = modeKey === "job_hunt";

  // 按模式决定显示哪些链接
  const links = [
    { href: "/today", label: "今日" },
    ...(isJobHunt ? [{ href: "/jobs", label: "求职" }] : []),
    { href: "/plan", label: "学习" },
    { href: "/dashboard", label: "概览" },
  ];

  const isActive = (href: string) => {
    if (href === "/today") return pathname === href || pathname === "/";
    if (href === "/jobs") return JOB_HUNT_ROUTES.some((p) => pathname.startsWith(p));
    if (href === "/plan") return LEARN_ROUTES.some((p) => pathname.startsWith(p));
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
            <circle cx="7" cy="7" r="4" fill="var(--color-primary)" />
            <circle cx="13" cy="13" r="4" fill="var(--color-emerald)" />
            <path d="M7 7L13 13" stroke="var(--color-ink)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <span className="text-[13px] font-semibold" style={{ color: "#F5F5F7" }}>
          Career OS
        </span>
        <div className="flex" style={{ gap: 28 }}>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
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
        <ModeSwitcher />
        <div style={{ width: 16, height: 16 }}>
          <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="5" stroke="var(--color-ink-48)" strokeWidth="1.5" />
            <path d="M11 11L15 15" stroke="var(--color-ink-48)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <div
          className="rounded-full"
          style={{ width: 26, height: 26, background: "var(--color-primary)" }}
        />
      </div>
    </nav>
  );
}
