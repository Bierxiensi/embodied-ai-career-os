/** 面试线页面（Server Component）。

 * 数据流：page.tsx (server) → listLogs()/listQuestions()/getStats() → /api/interviews
 *   ↓
 *   InterviewBoard 客户端组件渲染（弱项排行 / 模拟抽题 / 面经记录 / 题库）
 */

import InterviewBoard from "@/components/InterviewBoard";
import { ApiError } from "@/lib/apiClient";
import { getStats, listLogs, listQuestions } from "@/services/interviewService";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

export default async function InterviewPage() {
  try {
    const [logs, questions, stats] = await Promise.all([
      listLogs(),
      listQuestions(),
      getStats(),
    ]);

    return (
      <main className="min-h-full" style={{ background: "var(--color-canvas)" }}>
        <InterviewBoard initialLogs={logs} initialQuestions={questions} initialStats={stats} />
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
