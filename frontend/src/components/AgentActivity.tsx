import type { AgentRunRecord } from "@/types";

/** Agent Activity 面板。
 *
 * Phase 2 Week 1 Day 6：展示最近 Agent 执行记录，体现 Multi-Agent 系统可观测性。
 *
 * 数据流：
 *   Server Component（dashboardService）→ getAgentRuns() → GET /api/agent/runs
 *   → AgentActivity 组件纯展示
 *
 * 展示内容：
 * - 每个 Agent 最近一次执行（success/failed + 耗时 + 摘要）
 * - 完整执行时间线（按时间倒序，最近 N 条）
 */

type Props = {
  runs: AgentRunRecord[]; // 已按时间倒序
};

// Agent 显示名映射（中文化 + 业务语义）
const AGENT_LABELS: Record<string, string> = {
  planner: "Planner",
  reviewer: "Reviewer",
  career: "Career",
  research: "Research",
  supervisor: "Supervisor",
};

// 状态徽章样式
const STATUS_STYLES: Record<string, string> = {
  success:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
};

// Agent 图标颜色（左侧色条）
const AGENT_COLORS: Record<string, string> = {
  planner: "bg-sky-500",
  reviewer: "bg-violet-500",
  career: "bg-amber-500",
  research: "bg-rose-500",
  supervisor: "bg-zinc-500",
};

/** 格式化时间为相对时间（如"3 分钟前"）。 */
function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin} 分钟前`;
  if (diffHour < 24) return `${diffHour} 小时前`;
  if (diffDay < 7) return `${diffDay} 天前`;
  return date.toLocaleDateString("zh-CN");
}

export default function AgentActivity({ runs }: Props) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-black dark:text-zinc-50">
          🤖 Agent Activity
        </h2>
        <span className="text-xs text-zinc-400 dark:text-zinc-600">
          {runs.length} 条最近执行
        </span>
      </div>

      {runs.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-400 dark:text-zinc-600">
          暂无 Agent 执行记录
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {runs.map((run) => {
            const label = AGENT_LABELS[run.agentName] ?? run.agentName;
            const color = AGENT_COLORS[run.agentName] ?? "bg-zinc-400";
            const statusStyle = STATUS_STYLES[run.status] ?? STATUS_STYLES.failed;

            return (
              <li
                key={run.id}
                className="flex items-start gap-3 rounded-lg border border-zinc-100 p-3 dark:border-zinc-900"
              >
                {/* 左侧色条：区分 Agent 类型 */}
                <span className={`mt-1 h-8 w-1 shrink-0 rounded-full ${color}`} />

                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-black dark:text-zinc-50">
                        {label}
                      </span>
                      <span
                        className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${statusStyle}`}
                      >
                        {run.status}
                      </span>
                    </div>
                    <span className="shrink-0 text-xs text-zinc-400 dark:text-zinc-600">
                      {formatRelativeTime(run.createdAt)}
                    </span>
                  </div>

                  {/* 输出摘要 */}
                  {run.outputSummary && (
                    <p className="mt-1 truncate text-xs text-zinc-600 dark:text-zinc-400">
                      {run.outputSummary}
                    </p>
                  )}

                  {/* 耗时 + trace_id 简写 */}
                  <p className="mt-0.5 text-xs text-zinc-400 dark:text-zinc-600">
                    {run.durationMs}ms
                    {run.traceId && (
                      <span className="ml-2 font-mono">
                        trace: {run.traceId.slice(0, 8)}
                      </span>
                    )}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
