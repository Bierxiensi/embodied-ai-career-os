"use client";

/** 生成今日任务按钮（Client Component）。
 *
 * 职责：
 * - 触发 Planner Agent 生成学习任务
 * - 成功后调用 router.refresh() 让 Server Component 重新拉取任务列表
 * - 展示 loading / error / success 状态
 *
 * 设计原则：
 * - Server Component 负责数据获取（dashboard/page.tsx）
 * - Client Component 只负责交互（此组件）
 * - 数据流单向：点击 → POST /api/planner/generate → router.refresh() → 重新渲染
 */

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/apiClient";
import { generateTask } from "@/services/plannerService";
import type { Skill } from "@/types";

type Props = {
  /** 全部技能，用于计算缺口并传入 Planner Agent。 */
  skills: Skill[];
  /** 可用学习时长（分钟），默认 45。 */
  availableMinutes?: number;
};

/** 状态机：idle → loading → success/error → idle。 */
type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export default function GenerateTaskButton({
  skills,
  availableMinutes = 45,
}: Props) {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "idle" });

  async function handleClick() {
    setState({ kind: "loading" });
    try {
      // 构造 Planner 输入：技能名 + 当前等级 + 目标等级
      const skillInputs = skills.map((s) => ({
        name: s.name,
        level: s.level,
        target: s.targetLevel,
      }));

      const result = await generateTask({
        availableMinutes,
        targetRole: "Robot AI Engineer",
        skills: skillInputs,
        energyLevel: "normal",
        persist: true, // 后端写入 tasks 表 + agent_runs
      });

      setState({
        kind: "success",
        message: result.taskId
          ? `已生成任务：${result.title}（已入库 #${result.taskId}）`
          : `已生成任务：${result.title}`,
      });

      // 触发 Server Component 重新获取数据，新任务会出现在列表中
      router.refresh();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "生成任务失败，请检查后端服务";
      setState({ kind: "error", message });
    }
  }

  // 按钮文案与禁用态
  const isLoading = state.kind === "loading";
  const label =
    state.kind === "loading"
      ? "生成中..."
      : state.kind === "success"
        ? "再生成一个"
        : state.kind === "error"
          ? "重试"
          : "生成今日任务";

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoading}
        className="self-start rounded-lg bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-zinc-200"
      >
        {label}
      </button>

      {/* 状态提示：成功/错误信息 */}
      {state.kind === "success" && (
        <p className="text-xs text-emerald-600 dark:text-emerald-400">
          ✓ {state.message}
        </p>
      )}
      {state.kind === "error" && (
        <p className="text-xs text-red-600 dark:text-red-400">
          ✗ {state.message}
        </p>
      )}
    </div>
  );
}
