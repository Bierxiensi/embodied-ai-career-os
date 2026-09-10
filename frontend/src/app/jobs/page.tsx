/** 求职看板页面（Server Component）。

 * 数据流：page.tsx (server) → getJobHuntBoard() → /api/job-hunt → FastAPI
 *   ↓
 *   JobsBoard 客户端组件渲染（作战看板：倒计时 / 岗位画像 / 技能缺口 /
 *   求职里程碑 / 周任务 / 投递漏斗 + 投递管理）
 *
 * 错误处理：后端不可用时展示降级提示，与 dashboard 页一致。
 */

import JobsBoard from "@/components/JobsBoard";
import { ApiError } from "@/lib/apiClient";
import { getJobHuntBoard } from "@/services/jobHuntService";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

export default async function JobsPage() {
  try {
    const board = await getJobHuntBoard();

    return (
      <main className="min-h-full" style={{ background: "var(--color-canvas)" }}>
        <JobsBoard board={board} />
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
