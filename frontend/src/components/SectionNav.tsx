"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCareerMode } from "@/lib/careerModeContext";

type Section = {
  match: string;
  label: string;
  links: { href: string; label: string }[];
  /** 该区域在哪些模式下显示。缺省 = 所有模式。 */
  modes?: string[];
};

/** 区域定义 — 按模式过滤。 */
const SECTIONS: Section[] = [
  {
    match: "/jobs",
    label: "求职",
    modes: ["job_hunt"], // 仅求职模式显示
    links: [
      { href: "/jobs", label: "作战看板" },
      { href: "/jobs/pool", label: "岗位池" },
      { href: "/jobs/applications", label: "投递管理" },
      { href: "/resume", label: "简历" },
      { href: "/interview", label: "面试" },
    ],
  },
  {
    match: "/plan",
    label: "学习",
    links: [
      { href: "/plan", label: "施工计划" },
      { href: "/knowledge", label: "知识库" },
      { href: "/projects", label: "项目" },
      { href: "/questions", label: "题库" },
      { href: "/experiments", label: "实验" },
      { href: "/evidence", label: "证据" },
      { href: "/agents", label: "Agent" },
    ],
  },
];

/** 二级导航栏 — 出现在区域页面顶部，随 CareerMode 动态调整。
 *
 * 求职模式：求职区域 + 学习区域
 * 长期模式：只有学习区域（求职相关页面的二级导航隐藏）
 */
export default function SectionNav() {
  const pathname = usePathname();
  const { current } = useCareerMode();
  const modeKey = current?.key ?? "job_hunt";

  // 按当前模式过滤可用区域
  const availableSections = SECTIONS.filter(
    (s) => !s.modes || s.modes.includes(modeKey)
  );

  // 找到当前匹配的区域
  const section = availableSections.find((s) => {
    if (s.match === "/plan") {
      return s.links.some((l) => pathname.startsWith(l.href));
    }
    return pathname.startsWith(s.match);
  });

  if (!section) return null;

  return (
    <div
      className="flex items-center"
      style={{
        height: 40,
        paddingInline: "clamp(20px, 8vw, 120px)",
        background: "var(--color-card)",
        borderBottom: "1px solid var(--color-hairline)",
        gap: 4,
      }}
    >
      <span
        className="text-xs font-semibold"
        style={{ color: "var(--color-ink-48)", marginRight: 12 }}
      >
        {section.label}
      </span>
      {section.links.map((l) => {
        const isActive =
          l.href === "/jobs" || l.href === "/plan"
            ? pathname === l.href
            : pathname.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            className="text-xs font-medium no-underline"
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-pill)",
              background: isActive ? "var(--color-primary-soft)" : "transparent",
              color: isActive ? "var(--color-primary)" : "var(--color-ink-48)",
              transition: "background 0.15s ease, color 0.15s ease",
            }}
          >
            {l.label}
          </Link>
        );
      })}
    </div>
  );
}
