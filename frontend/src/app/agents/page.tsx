/** Agents 一级页面（Server Component）。
 *
 * 把"Agent 应用"作为正经营收入口：
 *   - 展示各 Agent 的总览统计 + 成功率
 *   - 支持按 Agent 过滤执行动态
 *   - 执行动态卡片为 interactive 模式：可展开 trace（input/output）、失败项可一键重试
 *
 * 数据流：page.tsx (server) → getAgentRuns() → GET /api/agent/runs → FastAPI → PostgreSQL
 * 复用 dashboard 的降级 UI 模式。
 */

import SubNav from "@/components/SubNav";
import AgentOverview from "@/components/AgentOverview";
import { ApiError } from "@/lib/apiClient";
import { getAgentRuns } from "@/services/agentService";
import { getSkills } from "@/services/skillService";
import type { Skill } from "@/types";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  try {
    const { runs } = await getAgentRuns(undefined, 50);
    // 次级栏"生成今日任务"需要技能数据；技能接口单独隔离，失败不击穿整个页面。
    const skills = await getSkills().catch(() => [] as Skill[]);

    return (
      <main className="flex flex-1 flex-col">
        <SubNav title="Agent 应用" skills={skills} />
        <div
          className="flex flex-col"
          style={{ gap: "var(--spacing-lg)", padding: "36px clamp(20px, 8vw, 120px) 48px" }}
        >
          <div className="flex flex-col" style={{ gap: 8 }}>
            <span
              className="text-xs font-semibold uppercase"
              style={{ color: "var(--text-muted)", letterSpacing: "0.04em" }}
            >
              MULTI-AGENT SYSTEM
            </span>
            <h1
              className="font-semibold"
              style={{ fontSize: 40, color: "var(--text-primary)", letterSpacing: "-0.02em" }}
            >
              Agent 工作台
            </h1>
            <p className="text-[17px]" style={{ color: "var(--text-muted)" }}>
              多智能体执行总览与可观测性 · Planner / Reviewer / Career / Research / Supervisor
            </p>
          </div>

          <AgentOverview runs={runs} />
        </div>
      </main>
    );
  } catch (err) {
    const message =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（localhost:8000）";

    return (
      <main
        className="flex flex-1 items-center justify-center"
        style={{ background: "var(--surface-canvas)" }}
      >
        <div
          className="max-w-md text-center"
          style={{
            padding: 32,
            background: "var(--surface-card)",
            border: "1px solid var(--accent-danger)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          <h1 className="text-lg font-semibold" style={{ color: "var(--accent-danger)" }}>
            后端连接失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
            {message}
          </p>
          <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>
            请执行：cd backend &amp;&amp; uvicorn app.main:app --reload --port 8000
          </p>
        </div>
      </main>
    );
  }
}
