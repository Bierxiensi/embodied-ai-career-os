/** 日报 / 周报页面（Server Component）。
 *
 * 数据流：page.tsx (server) → getReport/getSchedule/getFollowups/getHistory → /api/reports
 *   ↓
 *   ReportsBoard 客户端组件渲染（调度配置 / 待跟进 / 日报周报正文 / 归档历史）
 */

import ReportsBoard from "@/components/ReportsBoard";
import { ApiError } from "@/lib/apiClient";
import { getFollowups, getHistory, getReport, getSchedule } from "@/services/reportService";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新构建报告

export default async function ReportsPage() {
  try {
    const [daily, weekly, schedule, followups, history] = await Promise.all([
      getReport("daily"),
      getReport("weekly"),
      getSchedule(),
      getFollowups(),
      getHistory(undefined, 20),
    ]);

    return (
      <main className="min-h-full" style={{ background: "var(--color-canvas)" }}>
        <ReportsBoard
          initialDaily={daily}
          initialWeekly={weekly}
          initialSchedule={schedule}
          initialFollowups={followups}
          initialHistory={history}
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
          <h1 className="text-lg font-semibold" style={{ color: "var(--color-rose-deep)" }}>
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
