/** 岗位池页面（/jobs/pool）。

 * 数据流：page.tsx (server) → listPostings()/getPoolStats() → /api/job-postings
 *   ↓
 *   JDBoard 客户端组件渲染（统计 / 录入 / 匹配列表 / 详情抽屉）
 *
 * 原 /jd 页面迁移至此，/jd 保留为兼容重定向。
 */

import JDBoard from "@/components/JDBoard";
import { ApiError } from "@/lib/apiClient";
import { getPoolStats, listPostings } from "@/services/jdService";

export const dynamic = "force-dynamic";

export default async function JobPoolPage() {
  try {
    const [postings, stats] = await Promise.all([listPostings(), getPoolStats()]);

    return (
      <main className="min-h-full" style={{ background: "var(--surface-canvas)" }}>
        <JDBoard initialPostings={postings} initialStats={stats} />
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
          <h1
            className="text-lg font-semibold"
            style={{ color: "var(--accent-danger)" }}
          >
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
