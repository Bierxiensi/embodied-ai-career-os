/** Dashboard 页面（Server Component）。
 *
 * 数据流：
 *   page.tsx (server) → getDashboardData() → services → /api/* → FastAPI → PostgreSQL
 *   ↓
 *   Dashboard 组件渲染（匹配 Ardot 设计稿）
 *   ↓
 *   SubNav 点击生成任务 → POST /api/planner/generate → router.refresh() → 重新渲染
 *
 * 错误处理：后端不可用时展示降级提示，避免整页白屏。
 */

import Dashboard from "@/components/Dashboard";
import { ApiError } from "@/lib/apiClient";
import { getDashboardData } from "@/services/dashboardService";

export const dynamic = "force-dynamic"; // 每次请求都重新获取数据（任务列表实时更新）

export default async function DashboardPage() {
  try {
    const data = await getDashboardData();

    return (
      <main className="min-h-full" style={{ background: "var(--color-canvas)" }}>
        <Dashboard
          career={data.career}
          skills={data.skills}
          radarSkills={data.radarSkills}
          tasks={data.tasks}
          agentRuns={data.agentRuns}
          projects={data.projects}
        />
      </main>
    );
  } catch (err) {
    // 后端服务不可用时的降级 UI
    const message =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（localhost:8000）";

    return (
      <main
        className="flex min-h-screen items-center justify-center"
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
