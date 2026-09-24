import type { CountdownStatus } from "@/types";

/** 倒计时分档 → 语义色（禁止硬编码 hex）。
 *
 * 唯一映射表：职业进度卡与学术卡都用它 —— 两处各写一份会出现
 * "答辩红色、导师窗口橙色" 这种同一分档不同色的问题。
 */
export const COUNTDOWN_COLOR: Record<CountdownStatus, string> = {
  overdue: "var(--accent-danger)",
  urgent: "var(--accent-danger)",
  soon: "var(--accent-warning)",
  ok: "var(--accent-success)",
};

/** 倒计时分档 → 文案。 */
export const COUNTDOWN_LABEL: Record<CountdownStatus, string> = {
  overdue: "已过期",
  urgent: "紧急",
  soon: "临近",
  ok: "充裕",
};

/** 剩余天数 → 人话。负数如实显示（已过期的节点不该被藏起来）。 */
export function daysText(daysLeft: number): string {
  if (daysLeft < 0) return `已过期 ${Math.abs(daysLeft)} 天`;
  if (daysLeft === 0) return "今天到期";
  return `还剩 ${daysLeft} 天`;
}
