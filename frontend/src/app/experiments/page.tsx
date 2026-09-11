/** 实验记录页面（Server Component · P2 证据闭环）。

 * 对应 docs/platform-direction-30day.md 决策 4「实验记录是一等公民」与 P2 验收：
 * 「填一次 LoRA vs QLoRA 实验，页面直接渲染出对比表」。
 *
 * 数据流：
 *   page.tsx (server) → getExperiments() → /api/experiments → FastAPI
 *   ↓
 *   ExperimentBoard（客户端）渲染对比表 + 新增表单 → router.refresh()
 */

import PageHeader from "@/components/PageHeader";
import ExperimentBoard from "@/components/ExperimentBoard";
import { ApiError } from "@/lib/apiClient";
import { getExperiments } from "@/services/experimentService";

export const dynamic = "force-dynamic";

export default async function ExperimentsPage() {
  try {
    const experiments = await getExperiments();

    return (
      <main className="flex flex-1 flex-col" style={{ background: "var(--color-canvas)" }}>
        <div
          className="mx-auto flex w-full max-w-[1180px] flex-col"
          style={{ padding: "32px 32px 56px", gap: 24 }}
        >
          <PageHeader
            eyebrow="EXPERIMENTS · 实验记录"
            title="实验对比"
            subtitle="把训练 / 推理实验落表（决策 4）：面试时直接打开对比表，而不是空口说「我跑了 Qwen」。"
          />
          <ExperimentBoard experiments={experiments} />
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
            实验页加载失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
            {message}
          </p>
        </div>
      </main>
    );
  }
}
