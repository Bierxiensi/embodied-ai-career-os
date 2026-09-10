/** Dashboard 页面（Server Component）。
 *
 * 数据流：
 *   page.tsx (server) → getDashboardData(role) → services → /api/* → FastAPI
 *   ↓
 *   Dashboard 组件渲染（匹配 Ardot 设计稿）
 *   ↓
 *   SubNav 点击生成任务 → POST /api/planner/generate → router.refresh() → 重新渲染
 *
 * 视角（role）解析优先级：
 *   1. URL `?role=`（可分享/收藏，最高优先级）
 *   2. cookie `view_role`（记住上次选择，从其他页返回时沿用）
 *   3. 默认 `jobhunt`
 * 三者都在服务端解析，因此首屏就是正确视角，无客户端闪烁 / hydration mismatch。
 *
 * 错误处理：后端不可用时展示降级提示，避免整页白屏。
 */

import { cookies } from "next/headers";
import Dashboard from "@/components/Dashboard";
import { ApiError } from "@/lib/apiClient";
import { VIEW_ROLE_COOKIE, normalizeViewRole } from "@/lib/viewRole";
import { getDashboardData } from "@/services/dashboardService";

export const dynamic = "force-dynamic"; // 每次请求都重新获取数据（任务列表实时更新）

type PageProps = {
  searchParams: Promise<{ role?: string }>;
};

export default async function DashboardPage({ searchParams }: PageProps) {
  const [sp, cookieStore] = await Promise.all([searchParams, cookies()]);
  const role = normalizeViewRole(sp.role ?? cookieStore.get(VIEW_ROLE_COOKIE)?.value);

  try {
    const data = await getDashboardData(role);

    return (
      <main className="min-h-full" style={{ background: "var(--color-canvas)" }}>
        <Dashboard
          career={data.career}
          skills={data.skills}
          viewRole={data.viewRole}
          roleOptions={data.roleOptions}
          activeTrack={data.activeTrack}
          radarAxes={data.radarAxes}
          tasks={data.tasks}
          tasksTotal={data.tasksTotal}
          agentRuns={data.agentRuns}
          projects={data.projects}
          daysLeft={data.daysLeft}
        />
      </main>
    );
  } catch (err) {
    // 后端服务不可用时的降级 UI
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
