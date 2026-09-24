/** 投递管理页面（/jobs/applications）。

 * 展示全部投递记录，支持状态流转和新增。
 * 数据来源：GET /api/job-applications
 */

import ApplicationsBoard from "@/components/ApplicationsBoard";
import { ApiError } from "@/lib/apiClient";
import { listApplications } from "@/services/jobHuntService";

export const dynamic = "force-dynamic";

export default async function ApplicationsPage() {
  try {
    const applications = await listApplications();

    return (
      <main className="min-h-full" style={{ background: "var(--surface-canvas)" }}>
        <ApplicationsBoard initialApplications={applications} />
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
        </div>
      </main>
    );
  }
}
