/** /progress —— 三问之三「能力真提升吗」：雷达 + 职业进度 + 风险。
 * 证据门 L 级与作品集组装由计划 3 接入到本页。
 *
 * 结构说明：取数在 try 内、JSX 构造在 try 外 —— react-hooks/error-boundaries
 * 禁止在 try/catch 内构造 JSX（try 内的渲染错误不会被 catch 捕获）。行为与
 * 「try 内 return、catch 返回错误页」的写法一致。 */

import PageHeader from "@/components/PageHeader";
import CareerProgressCard from "@/components/CareerProgressCard";
import SkillRadarCard from "@/components/SkillRadarCard";
import RiskRadar from "@/components/RiskRadar";
import RoiTaskList from "@/components/RoiTaskList";
import { ApiError } from "@/lib/apiClient";
import { getJobHuntBoard } from "@/services/jobHuntService";
import { getToday } from "@/services/planService";
import { getSkillDomains } from "@/services/skillService";
import { buildSkillRadar } from "@/services/skillRadarService";
import { getTransitionDashboard } from "@/services/transitionService";

export const dynamic = "force-dynamic";

type ProgressData = {
  today: Awaited<ReturnType<typeof getToday>>;
  transition: Awaited<ReturnType<typeof getTransitionDashboard>> | null;
  radar: ReturnType<typeof buildSkillRadar>;
};

export default async function ProgressPage() {
  let data: ProgressData | null = null;
  let loadError: string | null = null;
  try {
    const [today, transition, domains, board] = await Promise.all([
      getToday(),
      getTransitionDashboard().catch(() => null),
      getSkillDomains().catch(() => null),
      getJobHuntBoard().catch(() => null),
    ]);
    data = {
      today,
      transition,
      radar: buildSkillRadar({
        modeKey: transition?.mode.key ?? null,
        targetRoles: board?.targetRoles ?? null,
        domains,
      }),
    };
  } catch (err) {
    loadError =
      err instanceof ApiError ? err.message : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";
  }

  if (loadError !== null || !data) {
    return (
      <main className="flex flex-1 items-center justify-center" style={{ background: "var(--surface-canvas)" }}>
        <div className="max-w-md text-center" style={{ padding: 32, background: "var(--surface-card)", border: "1px solid var(--accent-danger)", borderRadius: "var(--radius-lg)" }}>
          <h1 className="text-lg font-semibold" style={{ color: "var(--accent-danger)" }}>
            进度页加载失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
            {loadError}
          </p>
        </div>
      </main>
    );
  }

  const { today, transition, radar } = data;

  return (
    <main className="flex flex-1 flex-col" style={{ background: "var(--surface-canvas)" }}>
      <div
        className="mx-auto flex w-full max-w-[1180px] flex-col"
        style={{ padding: "32px 32px 56px", gap: 24 }}
      >
        <PageHeader
          eyebrow="PROGRESS · 能力真提升吗"
          title="差距与证据"
          subtitle="雷达看差距，ROI 看下一步，风险看阻塞——每条主张将来都可点开证据（计划 3）。"
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
            gap: 24,
          }}
        >
          <SkillRadarCard data={radar} />
          {transition ? (
            <CareerProgressCard
              progress={transition.careerProgress}
              mode={transition.mode}
              asOf={transition.asOf}
            />
          ) : null}
          {today.roiRankedTasks ? <RoiTaskList tasks={today.roiRankedTasks} /> : null}
          {today.risk ? <RiskRadar risk={today.risk} /> : null}
        </div>
        {transition ? null : (
          <div
            className="text-xs"
            style={{
              padding: 12,
              color: "var(--accent-danger)",
              background: "var(--accent-danger-soft)",
              border: "1px solid var(--accent-danger)",
              borderRadius: "var(--radius-md)",
            }}
          >
            职业进度区未加载：/api/transition/dashboard 不可用。其余区块正常显示。
          </div>
        )}
      </div>
    </main>
  );
}
