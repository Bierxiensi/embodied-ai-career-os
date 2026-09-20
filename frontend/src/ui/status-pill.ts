import type { CSSProperties } from "react";

/** 任务状态标签配置。 */
export type TaskStatusKey = "todo" | "doing" | "done";

interface StatusStyle {
  label: string;
  bg: string;
  fg: string;
}

export const STATUS_MAP: Record<TaskStatusKey, StatusStyle> = {
  todo: { label: "待办", bg: "var(--color-zinc-100)", fg: "var(--color-ink-32)" },
  doing: { label: "进行中", bg: "var(--color-amber-soft)", fg: "var(--color-amber-deep)" },
  done: { label: "已完成", bg: "var(--color-emerald-soft)", fg: "var(--color-emerald-deep)" },
};

/** 状态标签基础样式。 */
export const pillBase: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 9px",
  borderRadius: "var(--radius-pill)",
  fontSize: 11,
  fontWeight: 600,
};

/** 根据状态 key 获取完整的标签样式。 */
export function pillStyle(status: TaskStatusKey): CSSProperties {
  const s = STATUS_MAP[status] ?? STATUS_MAP.todo;
  return { ...pillBase, background: s.bg, color: s.fg };
}
