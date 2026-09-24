/**
 * Agent 视觉主题常量（单一事实来源）。
 *
 * 统一"Agent 应用"各处的：
 *  - 左侧色条颜色（与项目规范一致：sky=Planner / violet=Reviewer / amber=Career / rose=Research）
 *  - 中文显示名
 *  - 状态徽章样式
 *
 * 同时导出两套映射：
 *  - `*Token`：返回 CSS 变量名，供 token 体系组件（AgentActivityCard）使用
 *  - `*Class`：返回 Tailwind 类名，供仍用 `dark:` 体系的组件（ProjectCard 等）迁移使用
 *
 * 约定（见项目 MEMORY.md）：
 *  emerald=成功/当前 · sky=Planner · violet=Reviewer · amber=Career · rose=Research/失败
 */

export type AgentName = "planner" | "reviewer" | "career" | "research" | "supervisor";

/** 左侧色条颜色（CSS 变量 token）。 */
export const AGENT_COLOR_TOKEN: Record<AgentName, string> = {
  planner: "var(--color-sky)",
  reviewer: "var(--color-violet)",
  career: "var(--accent-warning)",
  research: "var(--accent-danger)",
  supervisor: "var(--text-muted)",
};

/** 左侧色条颜色（Tailwind 类名，便于迁移 dark: 体系）。 */
export const AGENT_COLOR_CLASS: Record<AgentName, string> = {
  planner: "bg-sky-500",
  reviewer: "bg-violet-500",
  career: "bg-amber-500",
  research: "bg-rose-500",
  supervisor: "bg-zinc-500",
};

/** 中文显示名 + 业务语义。 */
export const AGENT_LABEL: Record<AgentName, string> = {
  planner: "Planner",
  reviewer: "Reviewer",
  career: "Career",
  research: "Research",
  supervisor: "Supervisor",
};

/** 状态徽章：token 体系（背景 + 文字 CSS 变量）。 */
export const STATUS_TOKEN: Record<string, { bg: string; color: string }> = {
  success: { bg: "var(--accent-success-soft)", color: "var(--accent-success)" },
  failed: { bg: "var(--accent-danger-soft)", color: "var(--accent-danger)" },
};

/** 状态徽章：Tailwind 类名。 */
export const STATUS_CLASS: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
};

/** 取色条 token（带兜底）。 */
export function agentColorToken(name: string): string {
  return AGENT_COLOR_TOKEN[name as AgentName] ?? "var(--text-muted)";
}

/** 取中文显示名（带兜底）。 */
export function agentLabel(name: string): string {
  return AGENT_LABEL[name as AgentName] ?? name;
}
