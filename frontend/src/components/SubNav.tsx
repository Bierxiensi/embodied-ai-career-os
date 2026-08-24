"use client";

import GenerateTaskButton from "./GenerateTaskButton";
import type { Skill } from "@/types";

type Props = {
  skills: Skill[];
  /** 次级栏标题，默认 "概览"（Dashboard）。Agents 页传 "Agent 应用"。 */
  title?: string;
};

/** 子导航栏 — 标题 + 日期 + "生成今日任务"按钮。 */
export default function SubNav({ skills, title = "概览" }: Props) {
  const today = new Date();
  const dateStr = `${today.getMonth() + 1} 月 ${today.getDate()} 日 ${["日", "一", "二", "三", "四", "五", "六"][today.getDay()]}`;

  return (
    <div
      className="flex items-center justify-between"
      style={{
        height: 52,
        paddingInline: 24,
        background: "var(--color-canvas)",
        borderBottom: "1px solid var(--color-hairline)",
      }}
    >
      <span className="text-xl font-semibold" style={{ color: "var(--color-ink)" }}>
        {title}
      </span>
      <div className="flex items-center" style={{ gap: 16 }}>
        <span className="text-sm" style={{ color: "var(--color-ink-48)" }}>
          {dateStr}
        </span>
        <GenerateTaskButton skills={skills} variant="pill" />
      </div>
    </div>
  );
}
