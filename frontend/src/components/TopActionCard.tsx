import type { ActiveTrack, Task } from "@/types";
import { cardShell, itemBg } from "@/ui";

type Props = {
  /** 距截止日期天数（null 表示无截止日期或长期模式）。 */
  daysLeft: number | null;
  /** 当前主攻赛道。 */
  activeTrack: ActiveTrack | null;
  /** 当前阶段范围内的任务（用于提取首要行动）。 */
  tasks: Task[];
};

/** 首要行动卡片 — Dashboard 第 1 层。
 *
 * 回答"今天做什么？"：距截止日期、当前主攻赛道、今日最关键任务。
 */
export default function TopActionCard({ daysLeft, activeTrack, tasks }: Props) {
  // 取首要任务：优先 doing（进行中的最高优先），其次 todo
  const topTask =
    tasks.find((t) => t.status === "doing") ??
    tasks.find((t) => t.status === "todo") ??
    null;

  const doneCount = tasks.filter((t) => t.status === "done").length;
  const totalCount = tasks.length;

  return (
    <div
      className="flex flex-wrap items-center justify-between"
      style={{
        ...cardShell,
        gap: 24,
        padding: "var(--spacing-xl) 32px",
      }}
    >
      {/* 左侧：状态摘要 */}
      <div className="flex flex-col" style={{ gap: 10, minWidth: 240 }}>
        <div className="flex items-center" style={{ gap: 12 }}>
          {daysLeft !== null && (
            <span
              className="font-semibold"
              style={{
                fontSize: 36,
                lineHeight: 1,
                color: daysLeft <= 7 ? "var(--color-rose-deep)" : "var(--color-ink)",
                letterSpacing: "-0.02em",
              }}
            >
              {daysLeft}
              <span
                style={{
                  fontSize: 16,
                  fontWeight: 500,
                  color: "var(--color-ink-48)",
                  marginLeft: 4,
                }}
              >
                天
              </span>
            </span>
          )}
          {activeTrack && (
            <span
              className="inline-flex items-center"
              style={{
                padding: "4px 12px",
                borderRadius: "var(--radius-pill)",
                fontSize: 12,
                fontWeight: 600,
                background: "var(--color-primary-soft)",
                color: "var(--color-primary)",
              }}
            >
              {activeTrack.name}
            </span>
          )}
        </div>
        <span className="text-sm" style={{ color: "var(--color-ink-48)" }}>
          {daysLeft !== null
            ? `距 offer 目标截止 · 已完成 ${doneCount}/${totalCount} 项任务`
            : `长期模式 · 已完成 ${doneCount}/${totalCount} 项任务`}
        </span>
      </div>

      {/* 右侧：首要行动 */}
      <div
        className="flex flex-col"
        style={{
          gap: 8,
          flex: "1 1 320px",
          minWidth: 0,
          padding: "16px 20px",
          background: topTask ? "var(--color-item-bg)" : "transparent",
          borderRadius: "var(--radius-item-md)",
          border: topTask ? "1px solid var(--color-hairline)" : "none",
        }}
      >
        <span className="text-xs font-semibold" style={{ color: "var(--color-ink-48)" }}>
          {topTask ? "首要行动" : "暂无待办任务"}
        </span>
        {topTask && (
          <>
            <span
              className="text-[15px] font-semibold"
              style={{ color: "var(--color-ink)" }}
            >
              {topTask.title}
            </span>
            {topTask.skill && (
              <span
                className="self-start inline-flex items-center"
                style={{
                  padding: "2px 8px",
                  borderRadius: "var(--radius-pill)",
                  fontSize: 11,
                  fontWeight: 600,
                  background: "var(--color-primary-soft)",
                  color: "var(--color-primary)",
                }}
              >
                {topTask.skill}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}
