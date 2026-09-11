/** 面试线页面（Server Component）。

 * 数据流：page.tsx (server) → listLogs()/getStats() → /api/interviews
 *   ↓
 *   InterviewBoard 客户端组件渲染（弱项排行 / 面经记录 / 回写任务）
 *
 * 2026-09-11（P3）：题库与抽题已独立到 /questions，本页只负责「面经 → 弱项 → 任务」。
 */

import InterviewBoard from "@/components/InterviewBoard";
import { ApiError } from "@/lib/apiClient";
import { getStats, listLogs } from "@/services/interviewService";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

export default async function InterviewPage() {
  try {
    // 题库 / 抽题已独立到 /questions（P3）—— 本页只负责「面经 → 弱项 → 任务」。
    const [logs, stats] = await Promise.all([listLogs(), getStats()]);

    return (
      <main className="flex flex-1 flex-col" style={{ background: "var(--color-canvas)" }}>
        <InterviewBoard initialLogs={logs} initialStats={stats} />
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
