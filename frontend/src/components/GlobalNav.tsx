"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/** 全局导航栏 — 黑色顶栏，含 Logo、导航链接、搜索、头像。 */
export default function GlobalNav() {
  const pathname = usePathname();

  // P4：`/jobs`（求职漏斗）提为主位 —— 位于「今日」之后。
  // 依据 docs/platform-direction-30day.md 路线图第 14 项「10 月起提为主位」：
  // 求职是当前最高优先级，投递漏斗不该排在「施工 / 实验 / 证据」这些学习页之后。
  const links = [
    { href: "/today", label: "今日" },
    { href: "/jobs", label: "求职" },
    { href: "/plan", label: "施工" },
    { href: "/projects", label: "项目" },
    { href: "/questions", label: "题库" },
    { href: "/experiments", label: "实验" },
    { href: "/evidence", label: "证据" },
    { href: "/dashboard", label: "概览" },
    { href: "/jd", label: "岗位" },
    { href: "/resume", label: "简历" },
    { href: "/interview", label: "面试" },
    { href: "/reports", label: "报告" },
    { href: "/agents", label: "Agent" },
  ];

  // 「今日」与「概览」是精确匹配（/today、/dashboard），
  // 其余按前缀匹配（如 /projects/1 也应高亮「项目」）。
  const isActive = (href: string) =>
    href === "/dashboard" || href === "/today"
      ? pathname === href
      : pathname.startsWith(href);

  return (
    <nav
      className="flex items-center justify-between"
      style={{
        height: 44,
        paddingInline: 24,
        background: "#000000",
      }}
    >
      {/* Left cluster: Logo + Wordmark + Links */}
      <div className="flex items-center" style={{ gap: 28 }}>
        {/* Logo mark */}
        <div className="relative" style={{ width: 20, height: 20 }}>
          <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="4" fill="#0066CC" />
            <circle cx="13" cy="13" r="4" fill="#10B981" />
            <path d="M7 7L13 13" stroke="#F5F5F7" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <span className="text-[13px] font-semibold" style={{ color: "#F5F5F7" }}>
          Career OS
        </span>
        <div className="flex" style={{ gap: 20 }}>
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`text-xs font-medium no-underline ${
                isActive(l.href) ? "text-white" : "text-[#86868B]"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Right cluster: Search + Avatar */}
      <div className="flex items-center" style={{ gap: 18 }}>
        <div style={{ width: 16, height: 16 }}>
          <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="7" cy="7" r="5" stroke="#86868B" strokeWidth="1.5" />
            <path d="M11 11L15 15" stroke="#86868B" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <div
          className="rounded-full"
          style={{ width: 26, height: 26, background: "#0066CC" }}
        />
      </div>
    </nav>
  );
}
