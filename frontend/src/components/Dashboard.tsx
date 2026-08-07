import type { AgentRunRecord, Career, Skill, Task } from "@/types";
import AgentActivity from "./AgentActivity";
import CareerCard from "./CareerCard";
import GenerateTaskButton from "./GenerateTaskButton";
import SkillOverview from "./SkillOverview";
import SkillCard from "./SkillCard";
import TaskCard from "./TaskCard";

/** Dashboard 布局容器。组合 Career / SkillOverview / Skill / Task / AgentActivity 卡片。
 *
 * Day6：数据由 Server Component（app/dashboard/page.tsx）通过 services 获取后注入，
 * 组件本身保持纯展示。GenerateTaskButton 为 Client Component，触发 Planner Agent
 * 后通过 router.refresh() 让 Server Component 重新拉取任务列表。
 *
 * Day7：TaskCard 改为 Client Component（含"完成并复盘"交互），
 * 提交复盘后 router.refresh() 触发技能雷达图实时更新。
 *
 * Phase 2 Day6：新增 AgentActivity 面板，展示 Multi-Agent 执行可观测性。
 *
 * radarSkills 为雷达图专用核心能力子集（不含已达成优势）。
 */
type Props = {
  career: Career;
  skills: Skill[]; // 全部技能，SkillCard 明细 + GenerateTaskButton 输入
  radarSkills: Skill[]; // 核心能力子集，SkillOverview 雷达图
  tasks: Task[];
  agentRuns: AgentRunRecord[]; // Phase 2 Day6：Agent Activity 面板
};

export default function Dashboard({
  career,
  skills,
  radarSkills,
  tasks,
  agentRuns,
}: Props) {
  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <header className="mb-8">
        <p className="mb-2 text-xs font-medium tracking-widest text-zinc-400 uppercase dark:text-zinc-600">
          Phase 2 · Week 1 · Multi-Agent
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-black dark:text-zinc-50">
          Embodied AI Career OS
        </h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          AI 驱动的具身智能职业成长操作系统
        </p>
      </header>

      {/* 职业目标卡片 */}
      <CareerCard career={career} />

      {/* 技能总览：雷达图 + 缺口汇总（全局视角） */}
      <div className="mt-6">
        <SkillOverview skills={radarSkills} />
      </div>

      {/* 技能明细与任务两栏布局，窄屏自动堆叠 */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SkillCard skills={skills} />
        <div className="flex flex-col gap-3">
          {/* 触发 Planner Agent 生成任务，成功后刷新任务列表 */}
          <GenerateTaskButton skills={skills} />
          <TaskCard tasks={tasks} />
        </div>
      </div>

      {/* Phase 2 Day6：Agent Activity 面板（Multi-Agent 可观测性） */}
      <div className="mt-6">
        <AgentActivity runs={agentRuns} />
      </div>

      <footer className="mt-10 text-center text-xs text-zinc-400 dark:text-zinc-600">
        Keep simple · Build fast · Use AI agents
      </footer>
    </div>
  );
}
