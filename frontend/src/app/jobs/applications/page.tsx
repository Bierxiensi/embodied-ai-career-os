/** 归档线只读（2026-09-29 撤表单）：登记入口已收起，数据保留 */

/** 投递管理页面（/jobs/applications）。

 * 展示全部投递记录（只读：新增 / 状态流转 / 删除入口已随撤表单收起）。
 * 数据来源：GET /api/job-applications
 *
 * 结构说明：取数在 try 内、JSX 构造在 try 外 —— react-hooks/error-boundaries
 * 禁止在 try/catch 内构造 JSX（与 /progress 同款纪律）。 */

import ApplicationsBoard from "@/components/ApplicationsBoard";
import { ApiError } from "@/lib/apiClient";
import { listApplications } from "@/services/jobHuntService";
import type { JobApplication } from "@/types";

export const dynamic = "force-dynamic";

export default async function ApplicationsPage() {
  let applications: JobApplication[] = [];
  let errorMessage: string | null = null;

  try {
    applications = await listApplications();
  } catch (err) {
    errorMessage =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";
  }

  if (errorMessage) {
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
            {errorMessage}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-full" style={{ background: "var(--surface-canvas)" }}>
      <ApplicationsBoard initialApplications={applications} />
    </main>
  );
}
