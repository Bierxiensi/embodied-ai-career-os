"use client";

/**
 * 生成今日任务按钮（Client Component，唯一真实现入口）。
 *
 * 之前存在两份实现：SubNav 内联了一份、另有已废弃的 GenerateTaskButton.tsx
 * 死代码。本组件统一两处，通过 variant 适配两种视觉形态：
 *  - "pill"：SubNav 顶部胶囊按钮
 *  - "tile"：QuickActions 内的主操作磁贴（蓝底大卡）
 *
 * 数据流：点击 → generateTask() → router.refresh() → Server Component 重渲染。
 *
 * 2026-09-10（用户反馈「Agent 生成今日任务不是很明确，没看明白」）：
 *   1. 请求带上 `trackKey` —— Planner 只在**当前视角赛道**的硬性技能里挑，
 *      冲刺视角不会再产出具身任务（反之亦然）。
 *   2. 成功不再只渲染一句"✓ 已生成"，而是弹 `PlannerResultCard`，
 *      把选中技能、缺口、新建/复用、验收标准全部摊开。
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/apiClient";
import { generateTask } from "@/services/plannerService";
import type { PlannerResult, Skill } from "@/types";
import PlannerResultCard from "./PlannerResultCard";

type Props = {
  /** 全部技能。后端会按赛道 required_skills 收敛，前端传全量即可。 */
  skills: Skill[];
  variant?: "pill" | "tile";
  /** 可用学习时长（分钟），默认 45。 */
  availableMinutes?: number;
  /** 目标岗位。不传则由后端按 target_roles 配置取「主攻」赛道
   *  （不要再写死岗位名 —— 曾经硬编码 "Robot AI Engineer" 导致 Planner 一直产出具身方向任务）。 */
  targetRole?: string;
  /** 当前视角赛道 key（llm / vlm / ai-algo / embodied）。
   * 不传则后端回退「主攻」赛道。 */
  trackKey?: string | null;
};

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "done"; result: PlannerResult }
  | { kind: "error"; message: string };

export default function GenerateTaskButton({
  skills,
  variant = "pill",
  availableMinutes = 45,
  targetRole,
  trackKey,
}: Props) {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "idle" });
  const [showCard, setShowCard] = useState(false);

  async function handleClick() {
    setState({ kind: "loading" });
    setShowCard(false);
    try {
      const skillInputs = skills.map((s) => ({
        name: s.name,
        level: s.level,
        target: s.targetLevel,
      }));

      const result = await generateTask({
        availableMinutes,
        // 不传 targetRole 时后端按 target_roles 配置取「主攻」赛道
        targetRole,
        // 视角赛道：决定 Planner 的候选技能范围
        trackKey: trackKey ?? null,
        skills: skillInputs,
        energyLevel: "normal",
        persist: true,
      });

      setState({ kind: "done", result });
      setShowCard(true);
      router.refresh();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "生成任务失败，请检查后端服务";
      setState({ kind: "error", message });
    }
  }

  const isLoading = state.kind === "loading";
  const label =
    state.kind === "loading"
      ? "生成中..."
      : state.kind === "done"
        ? "再生成一个"
        : state.kind === "error"
          ? "重试"
          : "生成今日任务";

  const card =
    showCard && state.kind === "done" ? (
      <PlannerResultCard
        result={state.result}
        onClose={() => setShowCard(false)}
      />
    ) : null;

  if (variant === "tile") {
    return (
      <div className="flex flex-col" style={{ gap: 6, width: "calc(50% - 6px)" }}>
        <button
          type="button"
          onClick={handleClick}
          disabled={isLoading}
          className="flex flex-col no-underline text-left"
          style={{
            gap: 8,
            padding: "var(--spacing-md)",
            borderRadius: "var(--radius-item-md)",
            background: "var(--color-primary)",
            height: 110,
            cursor: isLoading ? "not-allowed" : "pointer",
            opacity: isLoading ? 0.7 : 1,
            border: "none",
          }}
        >
          <div
            className="flex items-center justify-center"
            style={{
              width: 30,
              height: 30,
              borderRadius: "var(--radius-item-sm)",
              background: "rgba(255,255,255,0.18)",
            }}
          >
            <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M15 4L18 12L26 13L20 18L22 26L15 22L8 26L10 18L4 13L12 12L15 4Z" fill="var(--color-on-primary)" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-white">{label}</span>
          <span className="text-xs" style={{ color: "#B8D4F0" }}>
            Planner Agent · 按当前视角规划
          </span>
        </button>
        {state.kind === "error" && (
          <p className="text-xs" style={{ color: "var(--color-rose-deep)" }}>
            ✗ {state.message}
          </p>
        )}
        {state.kind === "done" && !showCard && (
          <button
            type="button"
            onClick={() => setShowCard(true)}
            className="self-start border-none text-xs font-medium"
            style={{
              color: "var(--color-primary)",
              background: "transparent",
              cursor: "pointer",
            }}
          >
            查看生成详情 →
          </button>
        )}
        {card}
      </div>
    );
  }

  // pill variant (SubNav)
  return (
    <div className="flex flex-col" style={{ gap: 2 }}>
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoading}
        className="inline-flex items-center border-none"
        style={{
          height: 34,
          paddingInline: 18,
          background: "var(--color-primary)",
          color: "var(--color-on-primary)",
          fontSize: 14,
          fontWeight: 500,
          borderRadius: "var(--radius-pill)",
          cursor: isLoading ? "not-allowed" : "pointer",
          opacity: isLoading ? 0.7 : 1,
        }}
      >
        {label}
      </button>
      {state.kind === "error" && (
        <p className="text-xs" style={{ color: "var(--color-rose-deep)" }}>
          ✗ {state.message}
        </p>
      )}
      {card}
    </div>
  );
}
