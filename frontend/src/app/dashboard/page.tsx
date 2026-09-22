/** Dashboard 页面（Server Component）。
 *
 * 数据流：page.tsx → getDashboardData() → services → /api/* → FastAPI
 * 每次请求重新获取数据（任务列表实时更新）。
 */

import Dashboard from "@/components/Dashboard";
import { ApiError } from "@/lib/apiClient";
import { getDashboardData } from "@/services/dashboardService";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  try {
    const data = await getDashboardData();

    return (
      <main className="min-h-full" style={{ background: "var(--color-canvas)" }}>
        <Dashboard
          skills={data.skills}
          activeTrack={data.activeTrack}
          skillRadar={data.skillRadar}
          defaultScopeTasks={data.defaultScopeTasks}
          frozenExcludedTasks={data.frozenExcludedTasks}
          unclassifiedTasks={data.unclassifiedTasks}
          taskScopeReason={data.taskScopeReason}
          agentRuns={data.agentRuns}
          projects={data.projects}
          daysLeft={data.daysLeft}
          applicationCounts={data.applicationCounts}
        />
      </main>
    );
  } catch (err) {
    const message =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";

    return (
      <main
        className="flex flex-1 items-center justify-center"
        style={{ background: "var(--color-canvas)" }}
      >
        <div
          className="max-w-md text-center"
          style={{
            padding: 32,
            background: "var(--color-card)",
            border: "1px solid var(--color-rose)",
            borderRadius: "var(--radius-card-lg)",
          }}
        >
          <h1
            className="text-lg font-semibold"
            style={{ color: "var(--color-rose-deep)" }}
          >
            后端连接失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
            {message}
          </p>
          <p className="mt-4 text-xs" style={{ color: "var(--color-ink-48)" }}>
            请执行：cd backend &amp;&amp; uvicorn app.main:app --reload --port 8000
          </p>
        </div>
      </main>
    );
  }
}
