/** 归档线只读（2026-09-29 撤表单）：登记入口已收起，数据保留 */

/** 岗位池页面（/jobs/pool）。

 * 数据流：page.tsx (server) → listPostings()/getPoolStats() → /api/job-postings
 *   ↓
 *   JDBoard 客户端组件渲染（统计 / 匹配列表 / 详情抽屉，只读）
 *
 * 原 /jd 页面迁移至此，/jd 保留为兼容重定向。
 *
 * 结构说明：取数在 try 内、JSX 构造在 try 外 —— react-hooks/error-boundaries
 * 禁止在 try/catch 内构造 JSX（与 /progress 同款纪律）。 */

import JDBoard from "@/components/JDBoard";
import { ApiError } from "@/lib/apiClient";
import { getPoolStats, listPostings } from "@/services/jdService";
import type { JobPoolStats, JobPosting } from "@/types";

export const dynamic = "force-dynamic";

export default async function JobPoolPage() {
  let postings: JobPosting[] = [];
  let stats: JobPoolStats | null = null;
  let errorMessage: string | null = null;

  try {
    [postings, stats] = await Promise.all([listPostings(), getPoolStats()]);
  } catch (err) {
    errorMessage =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";
  }

  if (errorMessage || !stats) {
    const message = errorMessage ?? "岗位池数据不可用，请稍后重试。";

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

  return (
    <main className="min-h-full" style={{ background: "var(--surface-canvas)" }}>
      <JDBoard initialPostings={postings} initialStats={stats} />
    </main>
  );
}
