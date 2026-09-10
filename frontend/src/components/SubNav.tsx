"use client";

import GenerateTaskButton from "./GenerateTaskButton";
import type { Skill } from "@/types";

type Props = {
  skills: Skill[];
  /** 次级栏标题，默认 "概览"（Dashboard）。Agents 页传 "Agent 应用"。 */
  title?: string;
  /** 当前视角赛道 key —— 决定 Planner 在哪些技能里挑（生成任务会跟随视角）。 */
  trackKey?: string | null;
  /** 当前视角赛道名，用于把按钮的语义说清楚。 */
  trackName?: string | null;
};

/** 子导航栏 — 标题 + 日期 + "生成今日任务"按钮。
 *
 * 顶栏 GlobalNav 已由 app/layout.tsx 统一渲染，本组件只负责次级栏。
 * 2026-09-10：新增 trackKey/trackName —— 生成任务随视角走（冲刺视角出 LLM 任务，
 * 具身视角出具身任务），按钮副标注明"按 X 视角规划"，避免生成结果与预期不符。
 */
export default function SubNav({
  skills,
  title = "概览",
  trackKey,
  trackName,
}: Props) {
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
        {trackName && (
          <span
            className="inline-flex items-center"
            style={{
              padding: "3px 10px",
              borderRadius: "var(--radius-pill)",
              fontSize: 11,
              fontWeight: 600,
              background: "var(--color-primary-soft)",
              color: "var(--color-primary)",
            }}
          >
            生成范围 · {trackName}
          </span>
        )}
        <span className="text-sm" style={{ color: "var(--color-ink-48)" }}>
          {dateStr}
        </span>
        <GenerateTaskButton skills={skills} variant="pill" trackKey={trackKey} />
      </div>
    </div>
  );
}
