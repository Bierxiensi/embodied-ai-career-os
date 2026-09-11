/** 30 天课程脊梁总览页面（Server Component）。
 *
 * 这是「施工」入口（见 docs/platform-direction-30day.md §六 IA）：
 * 从全局视角看 30 天课程进度 vs 日历进度，并对落后日期做滑期决策。
 *
 * 与 /today（当天施工单）的关系：
 *   /today 回答「今天干什么、做完没有」（过程·当日）
 *   /plan  回答「我整体进度如何、哪些天落后了」（过程·全局 + 滑期）
 *
 * 数据流：
 *   page.tsx (server) → getPlanOverview() → /api/plan/overview → FastAPI
 *   ↓
 *   PlanBoard（客户端）负责滑期三决策 → router.refresh()
 */

import PageHeader from "@/components/PageHeader";
import PlanBoard from "@/components/PlanBoard";
import { ApiError } from "@/lib/apiClient";
import { getPlanOverview } from "@/services/planService";

export const dynamic = "force-dynamic"; // 进度与滑期需实时

export default async function PlanPage() {
  try {
    const overview = await getPlanOverview();

    return (
      <main className="flex flex-1 flex-col" style={{ background: "var(--color-canvas)" }}>
        <div
          className="mx-auto flex w-full max-w-[1180px] flex-col"
          style={{ padding: "32px 32px 56px", gap: 24 }}
        >
          <PageHeader
            eyebrow="PLAN · 30 天课程脊梁"
            title="施工总览"
            subtitle="课程进度 Day N 与日历进度解耦：滑期只提示、不自动顺延，落后日期需手动决策。"
          />
          <PlanBoard overview={overview} />
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
            施工总览加载失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
            {message}
          </p>
          <p className="mt-4 text-xs" style={{ color: "var(--color-ink-48)", lineHeight: 1.7 }}>
            若提示课程日不存在，请先初始化课程脊梁：
            <br />
            cd backend &amp;&amp; python scripts/seed_plan_30d.py
          </p>
        </div>
      </main>
    );
  }
}
