"use client";

import GenerateTaskButton from "./GenerateTaskButton";
import type { Skill } from "@/types";

type Props = {
  skills: Skill[];
  /** 次级栏标题，默认 "概览"（Dashboard）。Agents 页传 "Agent 应用"。 */
  title?: string;
};

/** 子导航栏 — 标题 + 日期 + "生成今日任务"按钮。
 *
 * 顶栏 GlobalNav 已由 app/layout.tsx 统一渲染，本组件只负责次级栏。
 * 2026-09-22：删除 trackKey/trackName 死 props —— 它们来自已删除的 ViewRole
 * 展示视角概念（曾让 Planner 生成任务跟随视角赛道，属写操作混入视角逻辑）。
 * 现在生成任务一律走 Planner 默认口径（主攻赛道），与 CareerMode 对齐。
 */
export default function SubNav({ skills, title = "概览" }: Props) {
  const today = new Date();
  const dateStr = `${today.getMonth() + 1} 月 ${today.getDate()} 日 ${["日", "一", "二", "三", "四", "五", "六"][today.getDay()]}`;

  return (
    <div
      className="flex items-center justify-between"
      style={{
        height: 52,
        paddingInline: 24,
        background: "var(--surface-canvas)",
        borderBottom: "1px solid var(--border-default)",
      }}
    >
      <span className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
        {title}
      </span>
      <div className="flex items-center" style={{ gap: 16 }}>
        <span className="text-sm" style={{ color: "var(--text-muted)" }}>
          {dateStr}
        </span>
        <GenerateTaskButton skills={skills} variant="pill" />
      </div>
    </div>
  );
}
