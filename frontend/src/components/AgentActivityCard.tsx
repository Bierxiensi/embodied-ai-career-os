"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { AgentRunRecord } from "@/types";
import { agentColorToken, agentLabel } from "@/lib/agentTheme";
import { runAgent } from "@/services/agentService";
import { ApiError } from "@/lib/apiClient";

type Props = {
  runs: AgentRunRecord[];
  /** 是否允许展开 trace 详情与重试（Agent 页设为 true，Dashboard 默认 false）。 */
  interactive?: boolean;
  /** 最多展示的记录数。Dashboard 传 5 保持紧凑；Agent 页不传（默认不限制）。 */
  limit?: number;
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/** Agent 执行动态卡片 — 展示最近的 Agent 调用记录，支持展开 trace 与失败重试。 */
export default function AgentActivityCard({
  runs,
  interactive = false,
  limit = Infinity,
}: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [retryMsg, setRetryMsg] = useState<string | null>(null);
  const router = useRouter();

  if (runs.length === 0) return null;

  const successCount = runs.filter((r) => r.status === "success").length;
  const successRate = Math.round((successCount / runs.length) * 100);

  async function handleRetry(run: AgentRunRecord) {
    setRetryingId(run.id);
    setRetryMsg(null);
    try {
      // 用该次执行的原始输入上下文重新驱动对应 Agent
      const input = run.inputContext ?? {};
      await runAgent(`重试 ${agentLabel(run.agentName)} 上次任务`, {
        [run.agentName]: input,
      });
      setRetryMsg(`已重新触发 ${agentLabel(run.agentName)}`);
      // 重新拉取 Server Component 数据，新执行记录会出现在列表中
      router.refresh();
      setTimeout(() => setRetryMsg(null), 3000);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "重试失败";
      setRetryMsg(`重试失败：${msg}`);
      setTimeout(() => setRetryMsg(null), 4000);
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <div
      className="flex flex-col"
      style={{
        gap: 18,
        padding: "var(--spacing-lg)",
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[17px] font-semibold" style={{ color: "var(--text-primary)" }}>
          Agent 执行动态
        </span>
        <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
          {runs.length} 条记录 · 成功率 {successRate}%
        </span>
      </div>

      {retryMsg && (
        <p
          className="text-xs"
          style={{ color: retryMsg.startsWith("重试失败") ? "var(--accent-danger)" : "var(--accent-success)" }}
        >
          {retryMsg}
        </p>
      )}

      {runs.slice(0, limit).map((run) => {
        const barColor = agentColorToken(run.agentName);
        const isSuccess = run.status === "success";
        const isExpanded = expandedId === run.id;
        const hasDetail =
          interactive && (run.inputContext || run.outputResult);

        return (
          <div
            key={run.id}
            style={{
              padding: 14,
              background: "var(--color-item-bg)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div className="flex items-center" style={{ gap: 14 }}>
              {/* Color bar */}
              <div
                style={{
                  width: 4,
                  height: 44,
                  borderRadius: 2,
                  flexShrink: 0,
                  background: barColor,
                }}
              />
              <div className="flex flex-1 flex-col" style={{ gap: 6 }}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                    {agentLabel(run.agentName)}
                  </span>
                  <span
                    className="text-xs font-semibold"
                    style={{
                      color: isSuccess ? "var(--accent-success)" : "var(--accent-danger)",
                    }}
                  >
                    {isSuccess ? "success" : "failed"}
                  </span>
                </div>
                <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {run.outputSummary?.slice(0, 60) ?? "无摘要"} · {formatDuration(run.durationMs)}
                  {run.traceId ? ` · trace ${run.traceId.slice(0, 8)}` : ""}
                </span>
              </div>
            </div>

            {/* Trace 操作区（仅 interactive 模式） */}
            {interactive && (
              <div className="flex items-center" style={{ gap: 12, marginTop: 10, paddingLeft: 18 }}>
                {hasDetail && (
                  <button
                    type="button"
                    onClick={() => setExpandedId(isExpanded ? null : run.id)}
                    className="text-xs font-medium no-underline border-none bg-transparent"
                    style={{ color: "var(--accent-primary)", cursor: "pointer", padding: 0 }}
                  >
                    {isExpanded ? "收起 trace" : "查看 trace"}
                  </button>
                )}
                {!isSuccess && (
                  <button
                    type="button"
                    onClick={() => handleRetry(run)}
                    disabled={retryingId === run.id}
                    className="text-xs font-medium no-underline border-none rounded-full"
                    style={{
                      color: "var(--accent-danger)",
                      cursor: retryingId === run.id ? "not-allowed" : "pointer",
                      padding: "4px 10px",
                      background: "var(--accent-danger-soft)",
                      opacity: retryingId === run.id ? 0.6 : 1,
                    }}
                  >
                    {retryingId === run.id ? "重试中..." : "重试该 Agent"}
                  </button>
                )}
              </div>
            )}

            {/* 展开的 trace 详情 */}
            {isExpanded && hasDetail && (
              <div
                className="text-[11px]"
                style={{
                  marginTop: 10,
                  paddingLeft: 18,
                  paddingTop: 10,
                  borderTop: "1px dashed var(--border-default)",
                  color: "var(--text-muted)",
                  fontFamily: "var(--font-mono, monospace)",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {run.inputContext && (
                  <>
                    <div style={{ color: "var(--text-secondary)", fontWeight: 600, marginBottom: 4 }}>
                      INPUT
                    </div>
                    <div>{JSON.stringify(run.inputContext, null, 2)}</div>
                  </>
                )}
                {run.outputResult && (
                  <>
                    <div style={{ color: "var(--text-secondary)", fontWeight: 600, margin: "10px 0 4px" }}>
                      OUTPUT
                    </div>
                    <div>{JSON.stringify(run.outputResult, null, 2)}</div>
                  </>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
