import type { Metadata } from "next";
import { Inter } from "next/font/google";
import GlobalNav from "@/components/GlobalNav";
import SectionNav from "@/components/SectionNav";
import { CareerModeProvider } from "@/lib/careerModeContext";
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

/**
 * Root layout — GlobalNav lives here, not in individual pages.
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
            <SectionNav />
          </CareerModeProvider>
          <div className="flex flex-1 flex-col">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  );
}
