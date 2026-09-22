/** 今日施工单页面（Server Component）。
 *
 * 这是平台的**默认落地页**（见 docs/platform-direction-30day.md §六）。
 * 它回答三个问题：今天第几天、今天干什么、今天做完没有。
 *
 * 数据流：
 *   page.tsx (server) → getToday(day?) → /api/plan/today → FastAPI
 *   ↓
 *   TodayBoard（客户端）负责勾选四件套 / 标记任务完成 → router.refresh()
 *
 * 为什么替代 /dashboard 成为首页：
 *   /dashboard 是「我现在什么水平」的能力盘点（镜子），
 *   /today 是「我今天该做什么」的施工单（施工图）。
 *   学习平台的第一个入口必须是后者 —— /dashboard 降为二级页保留，不删。
 *
 * `?day=N` 可显式查看某一天（回看 / 预看），不传则按日历推导。
 */

import PageHeader from "@/components/PageHeader";
import TodayBoard from "@/components/TodayBoard";
import RiskRadar from "@/components/RiskRadar";
import RoiTaskList from "@/components/RoiTaskList";
import { ApiError } from "@/lib/apiClient";
import { getToday } from "@/services/planService";

export const dynamic = "force-dynamic"; // 四件套与任务状态需实时

type PageProps = {
  searchParams: Promise<{ day?: string }>;
};

export default async function TodayPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const parsed = sp.day ? Number.parseInt(sp.day, 10) : undefined;
  const day = Number.isFinite(parsed) ? parsed : undefined;

  try {
    const today = await getToday(day);

    return (
      <main
        className="flex flex-1 flex-col"
        style={{ background: "var(--color-canvas)" }}
      >
        <div
          className="mx-auto flex w-full max-w-[1180px] flex-col"
          style={{ padding: "32px 32px 56px", gap: 24 }}
        >
          <PageHeader
            eyebrow="TODAY · 今日施工单"
            title="今天干什么"
            subtitle="每天必须留下四样东西：一段代码、一页笔记、至少 5 道面试题、一次 commit。"
          />
          {/* Phase 2：七维风险雷达（老响应无 risk 时跳过，向后兼容） */}
          {today.risk ? <RiskRadar risk={today.risk} /> : null}
          <TodayBoard today={today} />
          {/* Phase 2：今日 ROI 排名 Top5（老响应无 roiRankedTasks 时跳过） */}
          {today.roiRankedTasks && today.roiRankedTasks.length > 0 ? (
            <RoiTaskList tasks={today.roiRankedTasks} />
          ) : null}
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
            今日施工单加载失败
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
