import type { Metadata } from "next";
import { Inter } from "next/font/google";
import GlobalNav from "@/components/GlobalNav";
import CommandPaletteMount from "@/components/ui/CommandPaletteMount";
import { Sidebar } from "@/components/ui";
import { CareerModeProvider } from "@/lib/careerModeContext";
import { PALETTE_ITEMS, PRIMARY_NAV, SIDEBAR_GROUP_ORDER } from "@/lib/nav";
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

/** 全局侧边栏分区 — 低频入口的分组渲染，**同源于 nav.ts 的 PALETTE_ITEMS**
 * （不另存第二份入口表：新增入口只改 PALETTE_ITEMS.group）。
 * 顶栏仍是 PRIMARY_NAV 三问（GlobalNav），/knowledge 不作为主入口出现。 */
const SIDEBAR_SECTIONS = SIDEBAR_GROUP_ORDER.map((group) => ({
  label: group,
  items: PALETTE_ITEMS.filter((item) => item.group === group),
})).filter((section) => section.items.length > 0);

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
