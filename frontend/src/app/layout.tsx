import type { Metadata } from "next";
import { Inter } from "next/font/google";
import GlobalNav from "@/components/GlobalNav";
import CommandPaletteMount from "@/components/ui/CommandPaletteMount";
import { Sidebar } from "@/components/ui";
import { CareerModeProvider } from "@/lib/careerModeContext";
import { PALETTE_ITEMS, PRIMARY_NAV } from "@/lib/nav";
import { ThemeProvider } from "@/theme/ThemeProvider";
import "./globals.css";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Embodied AI Career OS",
  description: "AI 驱动的求职作战与能力成长操作系统（Multi-Agent）",
};

/** 全局侧边栏分区 — 常驻于所有页面左侧。 */
const SIDEBAR_SECTIONS = [
  {
    label: "求职",
    items: [
      { href: "/jobs", label: "作战看板" },
      { href: "/jobs/pool", label: "岗位池" },
      { href: "/jobs/applications", label: "投递管理" },
      { href: "/resume", label: "简历" },
      { href: "/interview", label: "面试准备" },
    ],
  },
  {
    label: "学习",
    items: [
      { href: "/plan", label: "施工计划" },
      { href: "/questions", label: "题库练习" },
      { href: "/knowledge", label: "知识库" },
      { href: "/projects", label: "项目" },
    ],
  },
  {
    label: "博士",
    items: [
      { href: "/phd", label: "申请追踪" },
    ],
  },
  {
    label: "系统",
    items: [
      { href: "/agents", label: "Agent 工作台" },
    ],
  },
];

/**
 * Root layout — GlobalNav + Sidebar live here, not in individual pages.
 *
 * ThemeProvider wraps CareerModeProvider so theme context is available
 * to all children including GlobalNav (which hosts ThemeSwitcher).
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className={`${inter.variable} h-full antialiased`}>
      <body
        className="flex min-h-full flex-col"
        style={{ background: "var(--surface-canvas)" }}
      >
        <ThemeProvider>
          <CareerModeProvider>
            <GlobalNav />
            <div style={{ display: "flex", flex: 1 }}>
              <Sidebar sections={SIDEBAR_SECTIONS} />
              <main style={{ flex: 1, minWidth: 0 }}>{children}</main>
            </div>
            {/* 命令面板：Ctrl/Cmd+K；低频入口收敛于此（nav.ts 单一真源） */}
            <CommandPaletteMount primary={PRIMARY_NAV} palette={PALETTE_ITEMS} />
          </CareerModeProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
