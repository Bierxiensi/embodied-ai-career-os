/** /stages —— 阶段制收纳页（spec §2.4）：归档线保留数据、入口收在此处。
 * 同一时刻只有一个 active stage（当前 post_training_growth）；切换需确认且不删历史。 */

import PageHeader from "@/components/PageHeader";
import Link from "next/link";

const ARCHIVED = [
  { href: "/phd", label: "博士申请线", note: "26 秋申请季启用（archived）" },
  { href: "/jobs", label: "求职冲刺线", note: "未来窗口启用（archived）" },
  { href: "/jd", label: "JD 分析", note: "求职线附属" },
  { href: "/resume", label: "简历版本", note: "求职线附属" },
  { href: "/interview", label: "面试日志", note: "复盘仍建议用 /review" },
];

export default function StagesPage() {
  return (
    <main className="flex flex-1 flex-col" style={{ background: "var(--surface-canvas)" }}>
      <div className="mx-auto flex w-full max-w-[1180px] flex-col" style={{ padding: "32px 32px 56px", gap: 24 }}>
        <PageHeader
          eyebrow="STAGES · 阶段制"
          title="归档线与阶段切换"
          subtitle="每期只开一线（当前：Post-Training 成长线）。归档线数据保留，入口收在此处。"
        />
        <ul className="flex flex-col" style={{ gap: 12, listStyle: "none", padding: 0 }}>
          {ARCHIVED.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="flex items-center justify-between no-underline"
                style={{
                  padding: 16,
                  background: "var(--surface-card)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-default)",
                }}
              >
                <span className="text-sm font-semibold">{item.label}</span>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {item.note}
                </span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          SO101 是「证据工厂」不是阶段：MISTAKES / baseline 改造记录随时可回流证据库，永不占今日单。
        </p>
      </div>
    </main>
  );
}
