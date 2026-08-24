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
 */

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/apiClient";
import { generateTask } from "@/services/plannerService";
import type { Skill } from "@/types";

type Props = {
  /** 全部技能，用于计算缺口并传入 Planner Agent。 */
  skills: Skill[];
  variant?: "pill" | "tile";
  /** 可用学习时长（分钟），默认 45。 */
  availableMinutes?: number;
};

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export default function GenerateTaskButton({
  skills,
  variant = "pill",
  availableMinutes = 45,
}: Props) {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "idle" });

  async function handleClick() {
    setState({ kind: "loading" });
    try {
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
        persist: true,
      });

      setState({
        kind: "success",
        message: result.taskId
          ? `已生成任务：${result.title}（已入库 #${result.taskId}）`
          : `已生成任务：${result.title}`,
      });
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
      : state.kind === "success"
        ? "再生成一个"
        : state.kind === "error"
          ? "重试"
          : "生成今日任务";

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
              <path d="M15 4L18 12L26 13L20 18L22 26L15 22L8 26L10 18L4 13L12 12L15 4Z" fill="#FFFFFF" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-white">{label}</span>
          <span className="text-xs" style={{ color: "#B8D4F0" }}>
            Planner Agent · 智能规划
          </span>
        </button>
        {(state.kind === "success" || state.kind === "error") && (
          <p
            className="text-xs"
            style={{
              color:
                state.kind === "success"
                  ? "var(--color-emerald-deep)"
                  : "var(--color-rose-deep)",
            }}
          >
            {state.kind === "success" ? "✓ " : "✗ "}
            {state.message}
          </p>
        )}
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
      {(state.kind === "success" || state.kind === "error") && (
        <p
          className="text-xs"
          style={{
            color:
              state.kind === "success"
                ? "var(--color-emerald-deep)"
                : "var(--color-rose-deep)",
          }}
        >
          {state.kind === "success" ? "✓ 已生成" : "✗ " + state.message}
        </p>
      )}
    </div>
  );
}
