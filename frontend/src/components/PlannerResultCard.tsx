"use client";

import type { PlannerResult } from "@/types";

type Props = {
  result: PlannerResult;
  onClose: () => void;
};

/** Planner 生成结果卡 —— 回答"Agent 到底干了什么"。
 *
 * 为什么需要它（2026-09-10 用户反馈「Agent 生成今日任务不是很明确，没看明白」）：
 *   改动前点「生成今日任务」只回一句 `✓ 已生成`，用户看不到：
 *     - 选了哪个技能、为什么是它
 *     - 它的当前等级 / 要求等级 / 缺口
 *     - 属于哪条赛道（切到具身视角时生成的还叫"今日任务"？）
 *     - 是**新建**一条还是**复用**了今天已有的（幂等命中，改动前两者文案一样）
 *
 * 布局：固定右下角浮层。选浮层而非内联展开，是因为按钮有两个 variant
 * （SubNav 顶栏 pill / QuickActions 磁贴），后者撑高会把顶栏挤变形。
 */
export default function PlannerResultCard({ result, onClose }: Props) {
  const isFrozen = result.trackFrozen;

  return (
    <div
      role="status"
      style={{
        position: "fixed",
        right: 24,
        bottom: 24,
        zIndex: 60,
        width: 420,
        maxWidth: "calc(100vw - 48px)",
        maxHeight: "calc(100vh - 120px)",
        overflowY: "auto",
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
        boxShadow: "0 12px 32px rgba(0,0,0,0.16)",
      }}
    >
      {/* 头部：状态 + 关闭 */}
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="flex items-center" style={{ gap: 8 }}>
          <span
            className="inline-flex items-center"
            style={{
              padding: "3px 9px",
              borderRadius: "var(--radius-pill)",
              fontSize: 11,
              fontWeight: 700,
              background: "var(--color-emerald-soft)",
              color: "var(--color-emerald-deep)",
            }}
          >
            ✓ 已生成
          </span>
          {/* 新建 vs 复用 —— 幂等命中时明确告知，避免误以为点一次加一条 */}
          <span
            className="inline-flex items-center"
            style={{
              padding: "3px 9px",
              borderRadius: "var(--radius-pill)",
              fontSize: 11,
              fontWeight: 600,
              background: result.reused ? "var(--color-amber-soft)" : "#F5F5F5",
              color: result.reused
                ? "var(--color-amber-deep)"
                : "var(--color-ink-32)",
            }}
          >
            {result.reused ? "复用今日已有" : "新建入库"}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="关闭"
          className="shrink-0 border-none"
          style={{
            width: 22,
            height: 22,
            borderRadius: "var(--radius-pill)",
            background: "transparent",
            color: "var(--color-ink-48)",
            fontSize: 14,
            lineHeight: 1,
            cursor: "pointer",
          }}
        >
          ✕
        </button>
      </div>

      {/* 任务标题 */}
      <div className="flex flex-col" style={{ gap: 6, marginTop: 14 }}>
        <span
          className="text-[17px] font-semibold"
          style={{ color: "var(--color-ink)", letterSpacing: "-0.01em" }}
        >
          {result.title}
        </span>
        {result.objective && (
          <span className="text-[13px]" style={{ color: "var(--color-ink-48)" }}>
            {result.objective}
          </span>
        )}
      </div>

      {/* 决策依据：为什么是这条任务 */}
      <div
        className="flex flex-col"
        style={{
          gap: 8,
          marginTop: 14,
          padding: "12px 14px",
          background: "var(--color-primary-soft)",
          borderRadius: "var(--radius-item-md)",
        }}
      >
        <span
          className="text-[11px] font-semibold uppercase"
          style={{ color: "var(--color-primary)", letterSpacing: "0.04em" }}
        >
          为什么是这条
        </span>
        {result.trackName && (
          <span className="text-xs" style={{ color: "var(--color-ink-80)" }}>
            视角赛道 · <strong>{result.trackName}</strong>
            {isFrozen && " （已冻结，仅低强度巩固）"}
          </span>
        )}
        {result.skillLevel !== null && result.skillTarget !== null && (
          <div className="flex items-center" style={{ gap: 8, flexWrap: "wrap" }}>
            <span className="text-xs" style={{ color: "var(--color-ink-80)" }}>
              技能 <strong>{result.skill}</strong>
            </span>
            <span
              className="inline-flex items-center"
              style={{
                padding: "2px 8px",
                borderRadius: "var(--radius-pill)",
                fontSize: 11,
                fontWeight: 600,
                background: "var(--color-card)",
                color: "var(--color-ink-80)",
              }}
            >
              {result.skillLevel} → {result.skillTarget}
            </span>
            {result.gap !== null && result.gap > 0 && (
              <span
                className="inline-flex items-center"
                style={{
                  padding: "2px 8px",
                  borderRadius: "var(--radius-pill)",
                  fontSize: 11,
                  fontWeight: 700,
                  background: "var(--color-amber-soft)",
                  color: "var(--color-amber-deep)",
                }}
              >
                差 {result.gap} 级
              </span>
            )}
          </div>
        )}
        {result.reason && (
          <span
            className="text-[11px]"
            style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}
          >
            {result.reason}
          </span>
        )}
      </div>

      {/* 任务规格 */}
      <div
        className="flex items-center"
        style={{ gap: 8, marginTop: 12, flexWrap: "wrap" }}
      >
        <Meta label={`${result.duration} min`} />
        {result.difficulty && <Meta label={result.difficulty} />}
        {result.taskId !== null && <Meta label={`任务 #${result.taskId}`} />}
      </div>

      {/* 验收标准 */}
      {result.acceptance.length > 0 && (
        <div className="flex flex-col" style={{ gap: 6, marginTop: 14 }}>
          <span
            className="text-[11px] font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            验收标准
          </span>
          <ol
            className="flex flex-col"
            style={{ gap: 4, margin: 0, paddingLeft: 18 }}
          >
            {result.acceptance.map((a, i) => (
              <li
                key={`${a}-${i}`}
                className="text-xs"
                style={{ color: "var(--color-ink-80)", lineHeight: 1.6 }}
              >
                {a}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function Meta({ label }: { label: string }) {
  return (
    <span
      className="inline-flex items-center"
      style={{
        padding: "3px 9px",
        borderRadius: "var(--radius-pill)",
        fontSize: 11,
        fontWeight: 600,
        background: "#F5F5F5",
        color: "var(--color-ink-32)",
      }}
    >
      {label}
    </span>
  );
}
