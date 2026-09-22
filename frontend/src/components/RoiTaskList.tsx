import type { RoiTask } from "@/types";

type Props = {
  /** ROI 排名 Top5 任务（后端已按 roi 降序）。 */
  tasks: RoiTask[];
};

/** ROI 颜色：高回报（>=1.0）emerald，中（>=0.5）amber，低 rose。 */
function roiColor(roi: number): string {
  if (roi >= 1.0) return "var(--color-emerald)";
  if (roi >= 0.5) return "var(--color-amber)";
  return "var(--color-rose)";
}

/** Phase 2 Career ROI 排名卡片 — Top5 任务列表。
 *
 * 每行：title + 关联技能 + roi（两位小数，按回报档位着色）+ reasons chips。
 * 数据来自 GET /api/plan/today 的 roi_ranked_tasks（后端已算好权重与时长系数）。
 */
export default function RoiTaskList({ tasks }: Props) {
  return (
    <div
      className="flex flex-col"
      style={{
        flex: "1 1 420px",
        maxWidth: 690,
        minWidth: 0,
        gap: "var(--spacing-md)",
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[17px] font-semibold" style={{ color: "var(--color-ink)" }}>
          今日 ROI 排名
        </span>
        <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
          高回报任务优先做
        </span>
      </div>

      {tasks.length === 0 ? (
        <span className="text-[13px]" style={{ color: "var(--color-ink-48)", paddingBlock: 16 }}>
          今日暂无带 ROI 评分的任务
        </span>
      ) : (
        <div className="flex flex-col" style={{ gap: 10 }}>
          {tasks.map((t, i) => (
            <div
              key={t.taskId}
              className="flex flex-col"
              style={{
                gap: 6,
                padding: 12,
                background: "var(--color-canvas)",
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-card)",
              }}
            >
              <div className="flex items-center justify-between" style={{ gap: 10 }}>
                <div className="flex items-center" style={{ gap: 8, minWidth: 0 }}>
                  <span
                    className="text-xs font-semibold shrink-0"
                    style={{
                      color: "var(--color-ink-48)",
                      width: 18,
                    }}
                  >
                    {i + 1}
                  </span>
                  <span
                    className="text-[14px] font-medium"
                    style={{ color: "var(--color-ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  >
                    {t.title}
                  </span>
                </div>
                <span
                  className="text-[15px] font-semibold shrink-0"
                  style={{ color: roiColor(t.roi) }}
                >
                  {t.roi.toFixed(2)}
                </span>
              </div>

              <div className="flex flex-wrap items-center" style={{ gap: 6, paddingLeft: 26 }}>
                {t.skillName && (
                  <span
                    className="text-[11px]"
                    style={{
                      color: "var(--color-ink-80)",
                      background: "var(--color-card)",
                      border: "1px solid var(--color-hairline)",
                      borderRadius: "var(--radius-pill)",
                      padding: "1px 8px",
                    }}
                  >
                    {t.skillName}
                  </span>
                )}
                {t.reasons.map((r, j) => (
                  <span
                    key={j}
                    className="text-[11px]"
                    style={{
                      color: "var(--color-ink-48)",
                      background: "var(--color-card)",
                      border: "1px solid var(--color-hairline)",
                      borderRadius: "var(--radius-pill)",
                      padding: "1px 8px",
                    }}
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
