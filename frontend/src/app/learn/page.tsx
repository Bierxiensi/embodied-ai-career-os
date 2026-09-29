/** /learn —— 三问之一「今天学什么」（Server Component）。
 *
 * 这是平台的**默认落地页**。它回答五个问题，也就是页面的"五区"：
 *
 *   ① 职业进度  CareerProgressCard + SkillRadarCard
 *   ② 当前工作  PositionCard
 *   ③ 学术与博士 AcademicProgressCard（硕士答辩倒计时 + 博士申请进度）
 *   ④ 今日 ROI  RoiTaskList（today.roiRankedTasks）
 *   ⑤ 风险雷达  RiskRadar（today.risk）
 *
 * 上方另有「今日施工单」（TodayBoard）：完成度三选一 + 今日任务 + 任务状态。
 * 它是"今天做什么"，五区是"我到哪里了" —— 一屏之内既给动作也给方位。
 *
 * 为什么收口到一页：
 *   转型期要同时盯四件事（赛道进度 / 在职窗口 / 答辩与博士 / 今日产出），
 *   散在 /jobs、/phd、/plan、/dashboard 四页会让人每天刷四遍；
 *   而这些页面各自只回答一个问题，没有一个回答"我现在整体如何"。
 *
 * 数据流（两处来源并行取，不做串行瀑布）：
 *   getTransitionDashboard() → /api/transition/dashboard  （①②③）
 *   getToday(day)            → /api/plan/today            （④⑤ + 施工单）
 *   getSkillDomains()        → /api/skills/domains        （①的 R2 雷达）
 *   getJobHuntBoard()        → /api/job-hunt              （①的 R1 雷达兜底）
 *   listUnits+getUnit        → /api/mastery/units         （完成度三选一的"测验过"派生，
 *                                                          依赖 today.day.seq，故串在 getToday 之后；
 *                                                          兜底 null，挂了只少一枚派生依据）
 *
 * 口径纪律：就绪度数字**不得**在前端重算 —— 与 /jobs 页同源，唯一权威在
 * 后端 `services/readiness`（llm 推进度 67% / 严格达标 23% 是回归锚点）。
 *
 * `?day=N` 可显式查看某一天的施工单（回看 / 预看），不传则按日历推导。
 *
 * 结构说明：取数在 try 内、JSX 构造在 try 外 —— react-hooks/error-boundaries
 * 禁止在 try/catch 内构造 JSX（try 内的渲染错误不会被 catch 捕获）。同
 * progress/page.tsx 的写法。
 */

import PageHeader from "@/components/PageHeader";
import TodayBoard from "@/components/TodayBoard";
import TodayUnit from "@/components/TodayUnit";
import CareerProgressCard from "@/components/CareerProgressCard";
import PositionCard from "@/components/PositionCard";
import AcademicProgressCard from "@/components/AcademicProgressCard";
import SkillRadarCard from "@/components/SkillRadarCard";
import RiskRadar from "@/components/RiskRadar";
import RoiTaskList from "@/components/RoiTaskList";
import { ApiError } from "@/lib/apiClient";
import { getJobHuntBoard } from "@/services/jobHuntService";
import { listLearningLogs } from "@/services/learningLogService";
import { getToday } from "@/services/planService";
import { getSkillDomains } from "@/services/skillService";
import { buildSkillRadar } from "@/services/skillRadarService";
import { getTransitionDashboard } from "@/services/transitionService";
import { getUnit, listUnits } from "@/services/masteryService";
import type { MasteryUnit } from "@/types";

export const dynamic = "force-dynamic"; // 完成度三选一与任务状态需实时

type PageProps = {
  searchParams: Promise<{ day?: string }>;
};

/** 五区共用的栅格：宽屏两列、窄屏一列（卡片自带 maxWidth，不会拉太宽）。 */
const ZONE_GRID = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
  gap: 24,
} as const;

type LearnData = {
  today: Awaited<ReturnType<typeof getToday>>;
  transition: Awaited<ReturnType<typeof getTransitionDashboard>> | null;
  radar: ReturnType<typeof buildSkillRadar>;
  learningLogs: Awaited<ReturnType<typeof listLearningLogs>>;
  /** 今日掌握单元（完成度三选一的"测验过"派生依据）。取不到 = null。 */
  unit: MasteryUnit | null;
};

export default async function LearnPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const parsed = sp.day ? Number.parseInt(sp.day, 10) : undefined;
  const day = Number.isFinite(parsed) ? parsed : undefined;

  let data: LearnData | null = null;
  let loadError: string | null = null;

  try {
    // getToday 不兜底：它失败意味着后端整体不可用，直接走错误页。
    // 其余三处各自兜底 —— 任一辅助端点抽风时页面仍应给出能给的区。
    const [today, transition, domains, board, learningLogs] = await Promise.all([
      getToday(day),
      getTransitionDashboard().catch(() => null),
      getSkillDomains().catch(() => null),
      getJobHuntBoard().catch(() => null),
      // 学习日志：与其它辅助端点同样兜底为空数组 —— 它挂了不该让整页进错误页
      listLearningLogs().catch(() => []),
    ]);

    // 今日掌握单元：依赖 today.day.seq，只能串在 getToday 之后（计划 2）。
    // 与辅助端点同规矩兜底 null —— 挂了只少一枚派生依据，整页照常。
    // getUnit 是必需的：list_units 返回的 items 恒空，内容（含懒生成）在详情接口。
    const unit = await listUnits(today.day.seq)
      .then((list) => (list.length > 0 ? getUnit(list[0].id) : null))
      .catch(() => null);

    // 雷达形态由**当前模式**决定（long_term_transition → 六域；job_hunt → 岗位对齐）。
    // 模式取不到时按非求职期处理（走域视图），因为长期模式是当前默认。
    data = {
      today,
      transition,
      radar: buildSkillRadar({
        modeKey: transition?.mode.key ?? null,
        targetRoles: board?.targetRoles ?? null,
        domains,
      }),
      learningLogs,
      unit,
    };
  } catch (err) {
    loadError =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";
  }

  if (loadError !== null || !data) {
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
          <h1 className="text-lg font-semibold" style={{ color: "var(--accent-danger)" }}>
            今日学习单加载失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--text-muted)" }}>
            {loadError}
          </p>
          <p className="mt-4 text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
            若提示课程日不存在，请先初始化课程脊梁：
            <br />
            cd backend &amp;&amp; python scripts/seed_plan_30d.py
          </p>
        </div>
      </main>
    );
  }

  const { today, transition, radar, learningLogs, unit } = data;

  return (
    <main className="flex flex-1 flex-col" style={{ background: "var(--surface-canvas)" }}>
      <div
        className="mx-auto flex w-full max-w-[1180px] flex-col"
        style={{ padding: "32px 32px 56px", gap: 24 }}
      >
        <PageHeader
          eyebrow="LEARN · 今天学什么"
          title="今日学习单"
          subtitle="关键单元与施工单在上，进度五区在下——学完记得留下实质记录。"
        />

        {/* 今日关键单元：学→测→Teach-Back（计划 2） */}
        <TodayUnit daySeq={today.day.seq} />

        {/* 今日施工单：完成度三选一 + 今天学到什么 + 今日任务（今天干什么、做完没有） */}
        <TodayBoard today={today} learningLogs={learningLogs} unit={unit} />

        {/* ═══ 五区 ═══ */}
        <div style={ZONE_GRID}>
          {/* ① 职业进度（赛道双轨就绪度 + 关键节点倒计时） */}
          {transition ? (
            <CareerProgressCard
              progress={transition.careerProgress}
              mode={transition.mode}
              asOf={transition.asOf}
            />
          ) : null}

          {/* ① 附：技能雷达（R2 六域 / R1 岗位对齐，由模式决定） */}
          <SkillRadarCard data={radar} />

          {/* ② 当前工作（在职事实 + 在职转型窗口） */}
          {transition ? <PositionCard position={transition.position} /> : null}

          {/* ③ 学术与博士（答辩倒计时 + 博士申请进度） */}
          {transition ? <AcademicProgressCard academic={transition.academic} /> : null}

          {/* ④ 今日 ROI 排名（RoiTaskList 自带空态；字段缺失=老响应才整块跳过） */}
          {today.roiRankedTasks ? <RoiTaskList tasks={today.roiRankedTasks} /> : null}

          {/* ⑤ 七维风险雷达（老响应无 risk 时跳过，向后兼容） */}
          {today.risk ? <RiskRadar risk={today.risk} /> : null}
        </div>

        {/* ①–③ 依赖 /api/transition/dashboard；它不可用时如实说明，不静默少三区 */}
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
            职业进度 / 当前工作 / 学术与博士三区未加载：/api/transition/dashboard 不可用。
            其余区块正常显示。
          </div>
        )}
      </div>
    </main>
  );
}
