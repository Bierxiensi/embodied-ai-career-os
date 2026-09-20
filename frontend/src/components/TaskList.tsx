"use client";

import { useState } from "react";
import type { Task } from "@/types";
import TaskCompleteForm from "./TaskCompleteForm";
import { cardShell, itemBg, STATUS_MAP, pillStyle, type TaskStatusKey } from "@/ui";

type Props = {
  /** 当前阶段范围内的任务（CareerMode 口径）。 */
  tasks: Task[];
  /** 可选的视图筛选：仅收窄"显示哪几条"，不改统计、不发请求。 */
  viewFilter?: { trackKey: string; trackName: string; isFrozen: boolean } | null;
  /** 被当前阶段排除的冻结赛道任务数。 */
  excludedFrozen?: number;
  /** 范围内未归类任务数（仅提示）。 */
  unclassified?: number;
  /** 口径说明文案，由后端给出。 */
  scopeReason?: string | null;
};

/** 任务列表卡片 — 展示当前阶段范围内的任务，支持完成复盘交互。
 *
 * 数据来源：CareerMode 口径，与 /jobs、/today 同源。
 * 视图筛选是纯前端行为，只收窄展示，不改统计。
 */
export default function TaskList({
  tasks,
  viewFilter = null,
  excludedFrozen = 0,
  unclassified = 0,
  scopeReason = null,
}: Props) {
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [viewFilterOn, setViewFilterOn] = useState(false);

  const totalCount = tasks.length;
  const doneCount = tasks.filter((t) => t.status === "done").length;

  const filterActive = viewFilterOn && viewFilter !== null;
  const visibleTasks = filterActive
    ? tasks.filter((t) => t.trackKey === viewFilter.trackKey)
    : tasks;

  return (
    <div
      className="flex flex-col"
      style={{
        ...cardShell,
        flex: "1 1 420px",
        maxWidth: 690,
        minWidth: 0,
        gap: 18,
      }}
    >
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="flex flex-col" style={{ gap: 4 }}>
          <span
            className="text-[17px] font-semibold"
            style={{ color: "var(--color-ink)" }}
          >
            当前任务池
          </span>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            按当前阶段筛选 · 与 /jobs、/today 同源
          </span>
        </div>
        <span
          className="shrink-0 text-right text-xs font-medium"
          style={{ color: "var(--color-ink-48)", lineHeight: 1.7 }}
        >
          共 {totalCount} 项 · 完成 {doneCount} 项
        </span>
      </div>

      {/* 口径透明度：隐藏不等于删除 */}
      {(scopeReason || excludedFrozen > 0 || unclassified > 0) && (
        <div
          className="flex flex-col"
          style={{
            gap: 2,
            padding: "8px 12px",
            background: "var(--color-item-bg)",
            borderRadius: "var(--radius-item-sm)",
          }}
        >
          {scopeReason && (
            <span className="text-xs" style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}>
              {scopeReason}
            </span>
          )}
          {excludedFrozen > 0 && (
            <span className="text-xs" style={{ color: "var(--color-ink-32)" }}>
              另有 {excludedFrozen} 项冻结赛道任务已按当前阶段排除
            </span>
          )}
          {unclassified > 0 && (
            <span className="text-xs" style={{ color: "var(--color-ink-32)" }}>
              其中 {unclassified} 项未归类（历史任务，仍计入范围）
            </span>
          )}
        </div>
      )}

      {/* 视图筛选：默认关闭，纯展示 */}
      {viewFilter && (
        <div className="flex items-center justify-between" style={{ gap: 12 }}>
          <button
            type="button"
            onClick={() => setViewFilterOn((v) => !v)}
            aria-pressed={viewFilterOn}
            className="inline-flex items-center border-none text-xs font-medium"
            style={{
              gap: 6,
              padding: "5px 10px",
              borderRadius: "var(--radius-pill)",
              cursor: "pointer",
              background: viewFilterOn ? "var(--color-primary-soft)" : "#F4F4F5",
              color: viewFilterOn ? "var(--color-primary)" : "var(--color-ink-48)",
            }}
          >
            <span
              aria-hidden
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                background: viewFilterOn ? "var(--color-primary)" : "#C4C4C8",
              }}
            />
            视图筛选{viewFilterOn ? "：开" : "：关"}
          </button>
          {filterActive && (
            <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
              {viewFilter.trackName} · 显示 {visibleTasks.length} / {totalCount} 项
              {viewFilter.isFrozen ? "（长期赛道）" : ""}
            </span>
          )}
        </div>
      )}

      {visibleTasks.map((task) => {
        const statusKey = (task.status as TaskStatusKey) ?? "todo";
      const statusLabel = STATUS_MAP[statusKey]?.label ?? "待办";
        const isOpen = activeTaskId === task.id;
        return (
          <div key={task.id}>
            <div
              className="flex flex-col"
              style={{
                gap: 6,
                padding: "14px 16px",
                background: "var(--color-item-bg)",
                borderRadius: "var(--radius-item-md)",
              }}
            >
              <div className="flex items-center justify-between" style={{ gap: 12 }}>
                <div className="flex items-center" style={{ gap: 8, minWidth: 0 }}>
                  <span style={pillStyle(statusKey)}>
                    {statusLabel}
                  </span>
                  {task.skill && (
                    <span
                      className="inline-flex items-center"
                      style={{
                        padding: "3px 9px",
                        borderRadius: "var(--radius-pill)",
                        fontSize: 11,
                        fontWeight: 600,
                        background: "var(--color-primary-soft)",
                        color: "var(--color-primary)",
                      }}
                    >
                      {task.skill}
                    </span>
                  )}
                </div>
                <span
                  className="shrink-0 text-xs font-medium"
                  style={{ color: "var(--color-ink-48)" }}
                >
                  {task.duration && task.duration > 0 ? `${task.duration} min` : "未估时"}
                </span>
              </div>
              <span
                className="text-[15px] font-semibold"
                style={{ color: "var(--color-ink)" }}
              >
                {task.title}
              </span>
              {task.acceptance && task.acceptance.length > 0 && (
                <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                  验收 · {task.acceptance.join("  ·  ")}
                </span>
              )}
              {task.status !== "done" && (
                <button
                  onClick={() => setActiveTaskId(isOpen ? null : task.id)}
                  className="mt-1 self-start border-none text-xs font-medium"
                  style={{
                    color: "var(--color-primary)",
                    background: "transparent",
                    cursor: "pointer",
                  }}
                >
                  {isOpen ? "取消" : "完成并复盘 →"}
                </button>
              )}
            </div>
            {isOpen && task.status !== "done" && (
              <div className="mt-2">
                <TaskCompleteForm
                  task={task}
                  onCancel={() => setActiveTaskId(null)}
                />
              </div>
            )}
          </div>
        );
      })}

      {visibleTasks.length === 0 && (
        <div
          className="flex flex-col items-center"
          style={{ gap: 6, padding: "32px 16px" }}
        >
          <span className="text-sm font-medium" style={{ color: "var(--color-ink)" }}>
            {filterActive ? "该视图筛选下暂无任务" : "还没有任务"}
          </span>
          <span
            className="text-center text-xs"
            style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}
          >
            {filterActive ? (
              <>关掉「视图筛选」可以看到全部 {totalCount} 项任务。</>
            ) : (
              <>
                点右上角「生成今日任务」，Planner 会按当前阶段的硬性技能
                挑一个缺口最大的来规划。
              </>
            )}
          </span>
        </div>
      )}
    </div>
  );
}
