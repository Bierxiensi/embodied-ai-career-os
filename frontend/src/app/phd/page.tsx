/** 归档线只读（2026-09-29 撤表单）：登记入口已收起，数据保留 */

/** 博士模块页面（Server Component）。
 *
 * 数据流：page.tsx (server) → getPhdAdvisors() + getPhdDirections() → /api/phd
 *   ↓
 *   PhDAdvisorBoard 客户端组件渲染（六维匹配 + 倒计时 + 缺口 + 主页/联系状态只读）
 *   录入面板 PhDEntryPanel 已随「撤表单」收起（组件文件一并移除），写口不在本页暴露。
 */

import PhDAdvisorBoard from "@/components/PhDAdvisorBoard";
import { ApiError } from "@/lib/apiClient";
import { getPhdAdvisors, getPhdDirections } from "@/services/phdService";
import type {
  PhDAdvisorDTO,
  ResearchDirectionDTO,
} from "@/services/phdService";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

export default async function PhdPage() {
  let advisors: PhDAdvisorDTO[] = [];
  let directions: ResearchDirectionDTO[] = [];
  let errorMessage: string | null = null;

  try {
    const [a, d] = await Promise.all([getPhdAdvisors(), getPhdDirections()]);
    advisors = a;
    directions = d;
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
          <p className="mt-4 text-xs" style={{ color: "var(--text-muted)" }}>
            请执行：cd backend &amp;&amp; uvicorn app.main:app --host 0.0.0.0 --port 8000
          </p>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-full" style={{ background: "var(--surface-canvas)", paddingTop: 20 }}>
      <PhDAdvisorBoard initialAdvisors={advisors} directions={directions} />
    </div>
  );
}
