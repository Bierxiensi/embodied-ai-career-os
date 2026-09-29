/** 归档线只读（2026-09-29 撤表单）：登记入口已收起，数据保留 */

/** 简历线页面（Server Component）。

 * 数据流：page.tsx (server) → listVersions()/listFacts()/getSkillLines() → /api/resume
 *   ↓
 *   ResumeBoard 客户端组件渲染（版本 / 防虚构诊断 / 事实锚点库 / 技能行附证据，只读）
 *
 * 结构说明：取数在 try 内、JSX 构造在 try 外 —— react-hooks/error-boundaries
 * 禁止在 try/catch 内构造 JSX（与 /progress 同款纪律）。 */

import ResumeBoard from "@/components/ResumeBoard";
import { ApiError } from "@/lib/apiClient";
import { getSkillLines } from "@/services/packagingService";
import { listFacts, listVersions } from "@/services/resumeService";
import type { ResumeFact, ResumeVersion, SkillLineReport } from "@/types";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

export default async function ResumePage() {
  let versions: ResumeVersion[] = [];
  let facts: ResumeFact[] = [];
  let skillLines: SkillLineReport | null = null;
  let errorMessage: string | null = null;

  try {
    versions = await listVersions();
    facts = await listFacts();
    // 技能行依赖证据链推导（读多张表），失败不击穿整页
    skillLines = await getSkillLines().catch(() => null);
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
            请执行：cd backend &amp;&amp; uvicorn app.main:app --reload --port 8000
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-full" style={{ background: "var(--surface-canvas)" }}>
      <ResumeBoard
        initialVersions={versions}
        initialFacts={facts}
        initialSkillLines={skillLines}
      />
    </main>
  );
}
