/** 知识库页面（Server Component）。
 *
 * 数据流：page.tsx (server) → getKnowledgeStats() → /api/paper/stats
 *   ↓
 *   KnowledgeBoard 客户端组件（检索 / 提问 / 引用展示）
 *
 * 说明：检索与问答是**用户触发**的交互，由客户端组件直接调 service，
 * 不走本页的服务端取数（避免每次页面加载都跑一次 RAG）。
 */

import KnowledgeBoard from "@/components/KnowledgeBoard";
import { ApiError } from "@/lib/apiClient";
import { getKnowledgeStats } from "@/services/knowledgeService";
import type { KnowledgeStats } from "@/types";

export const dynamic = "force-dynamic"; // 实时数据，每次请求重新获取

const EMPTY_STATS: KnowledgeStats = {
  paperCount: 0,
  chunkCount: 0,
  indexedChunkCount: 0,
  modelName: "",
  coverage: 0,
};

export default async function KnowledgePage() {
  let stats: KnowledgeStats = EMPTY_STATS;
  let errorMessage: string | null = null;

  try {
    stats = await getKnowledgeStats();
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
    <div
      className="min-h-full"
      style={{ background: "var(--surface-canvas)", paddingTop: 20 }}
    >
      <KnowledgeBoard stats={stats} />
    </div>
  );
}
