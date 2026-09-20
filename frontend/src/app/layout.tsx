import type { Metadata } from "next";
import { Inter } from "next/font/google";
import GlobalNav from "@/components/GlobalNav";
import SectionNav from "@/components/SectionNav";
import { CareerModeProvider } from "@/lib/careerModeContext";
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

/** 根布局 —— 顶栏在这里，不在各页面。
 *
 * 为什么放在布局层（2026-09-10 修复「项目界面风格不一致」）：
 *   原先 GlobalNav 由每个页面/看板各自渲染（7 处重复），结果 /projects 页
 *   漏了这一行，成了全站唯一没有顶栏、且自带一套 zinc-50/dark 旧配色的页面。
 *   把顶栏收敛到布局层后，"所有页面都有同一个顶栏"由架构保证，
 *   不再依赖每个新页面作者记得手动加一次。
 *
 * 页面容器约定：各页面/看板的最外层只需 `flex flex-1 flex-col`
 * （或纯内容），**不要再写 min-h-screen** —— 顶栏已占 44px，
 * 再叠一个 100vh 会让每页都多出一条滚动条。
 * 画布底色也在这里统一给，页面不需要自己再铺一层。
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
        style={{ background: "var(--color-canvas)" }}
      >
        <CareerModeProvider>
          <GlobalNav />
          <SectionNav />
        </CareerModeProvider>
        <div className="flex flex-1 flex-col">{children}</div>
      </body>
    </html>
  );
}
