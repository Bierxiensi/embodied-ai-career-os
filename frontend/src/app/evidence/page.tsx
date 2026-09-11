/** 技能证据链页面（Server Component · P2 证据闭环）。

 * 对应 docs/platform-direction-30day.md 决策 3「技能晋级改成 evidence-gated」
 * 与 P2 验收：「技能升级弹窗显示因为这份代码 / 实验 + 可信等级」。
 *
 * 数据流：
 *   page.tsx (server) → getSkillEvidenceList() → /api/skills/evidence → FastAPI
 *   ↓
 *   EvidenceBoard（客户端）渲染每条技能的证据链 + 可信等级徽章
 */

import PageHeader from "@/components/PageHeader";
import EvidenceBoard from "@/components/EvidenceBoard";
import { ApiError } from "@/lib/apiClient";
import { getSkillEvidenceList } from "@/services/experimentService";

export const dynamic = "force-dynamic";

export default async function EvidencePage() {
  try {
    const skills = await getSkillEvidenceList();

    return (
      <main className="flex flex-1 flex-col" style={{ background: "var(--color-canvas)" }}>
        <div
          className="mx-auto flex w-full max-w-[1180px] flex-col"
          style={{ padding: "32px 32px 56px", gap: 24 }}
        >
          <PageHeader
            eyebrow="EVIDENCE · 技能证据链"
            title="证据可信度"
            subtitle="技能等级不再靠自评（决策 3）：每条晋级都附带「因为这份代码 / 笔记 / 实验」的可信证据，面试时直接打开对照。"
          />
          <EvidenceBoard skills={skills} />
        </div>
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
            证据页加载失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
            {message}
          </p>
        </div>
      </main>
    );
  }
}
