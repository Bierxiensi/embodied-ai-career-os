/** 博士模块页面（Server Component）。
 *
 * 数据流：page.tsx (server) → getPhdAdvisors() + getPhdDirections() + getPhdTargets() → /api/phd
 *   ↓
 *   PhDEntryPanel 录入面板（院校机会 + 导师，提交后 router.refresh() 刷新本页数据）
 *   PhDAdvisorBoard 客户端组件渲染（六维匹配 + 倒计时 + 缺口 + 联系标记/删除）
 */

import PhDAdvisorBoard from "@/components/PhDAdvisorBoard";
import PhDEntryPanel from "@/components/PhDEntryPanel";
import { ApiError } from "@/lib/apiClient";
import { getPhdAdvisors, getPhdDirections, getPhdTargets } from "@/services/phdService";
import type {
  PhDAdvisorDTO,
  PhDTargetDTO,
  ResearchDirectionDTO,
} from "@/services/phdService";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

export default async function PhdPage() {
  let advisors: PhDAdvisorDTO[] = [];
  let directions: ResearchDirectionDTO[] = [];
  let targets: PhDTargetDTO[] = [];
  let errorMessage: string | null = null;

  try {
    const [a, d, t] = await Promise.all([
      getPhdAdvisors(),
      getPhdDirections(),
      getPhdTargets(),
    ]);
    advisors = a;
    directions = d;
    targets = t;
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
            {errorMessage}
          </p>
          <p className="mt-4 text-xs" style={{ color: "var(--color-ink-48)" }}>
            请执行：cd backend &amp;&amp; uvicorn app.main:app --host 0.0.0.0 --port 8000
          </p>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-full" style={{ background: "var(--color-canvas)", paddingTop: 20 }}>
      <PhDEntryPanel directions={directions} targets={targets} />
      <PhDAdvisorBoard initialAdvisors={advisors} directions={directions} />
    </div>
  );
}
