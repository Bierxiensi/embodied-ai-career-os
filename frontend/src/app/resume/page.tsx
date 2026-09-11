/** 简历线页面（Server Component）。

 * 数据流：page.tsx (server) → listVersions()/listFacts()/getSkillLines() → /api/resume
 *   ↓
 *   ResumeBoard 客户端组件渲染（版本 / 防虚构诊断 / 事实锚点库 / 技能行附证据）
 */

import ResumeBoard from "@/components/ResumeBoard";
import { ApiError } from "@/lib/apiClient";
import { getSkillLines } from "@/services/packagingService";
import { listFacts, listVersions } from "@/services/resumeService";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

export default async function ResumePage() {
  try {
    const [versions, facts, skillLines] = await Promise.all([
      listVersions(),
      listFacts(),
      // 技能行依赖证据链推导（读多张表），失败不击穿整页
      getSkillLines().catch(() => null),
    ]);

    return (
      <main className="min-h-full" style={{ background: "var(--color-canvas)" }}>
        <ResumeBoard
          initialVersions={versions}
          initialFacts={facts}
          initialSkillLines={skillLines}
        />
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
