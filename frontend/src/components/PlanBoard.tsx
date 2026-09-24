"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type CSSProperties, type ReactNode } from "react";
import { setDayProgress } from "@/services/planService";
import type { DayProgressStatus, PlanDayStatus, PlanOverview } from "@/types";

type Props = {
  overview: PlanOverview;
};

const TRACK_LABEL: Record<string, string> = {
  llm: "LLM 主攻",
  vlm: "VLM 卡位",
  "ai-algo": "AI 算法保底",
  embodied: "具身（冻结）",
};

const STATUS_META: Record<DayProgressStatus, { label: string; bg: string; fg: string }> = {
  pending: { label: "未开始", bg: "#F5F5F5", fg: "var(--text-muted)" },
  done: { label: "完成", bg: "var(--accent-success-soft)", fg: "var(--accent-success)" },
  compressed: { label: "压缩通过", bg: "var(--accent-primary-soft)", fg: "var(--accent-primary)" },
  deferred: { label: "已顺延", bg: "var(--accent-warning-soft)", fg: "var(--accent-warning)" },
  skipped: { label: "已放弃", bg: "var(--accent-danger-soft)", fg: "var(--accent-danger)" },
};

/** 三个滑期决策：状态 + 默认偏离说明（落 deviation_note）。 */
const DECISIONS: { status: DayProgressStatus; label: string; note: string }[] = [
  {
    status: "compressed",
    label: "压缩",
    note: "压缩：本日验收降级为速通，缺口并入后续晨间时段",
  },
  {
    status: "deferred",
    label: "顺延",
    note: "顺延：本日内容推后手动补，不自动顺延后续天",
  },
  {
    status: "skipped",
    label: "放弃",
    note: "放弃：本日内容不再投入，释放时间给更高优先赛道",
  },
];

const cardStyle: CSSProperties = {
  background: "var(--surface-card)",
  border: "1px solid var(--border-default)",
  borderRadius: "var(--radius-lg)",
  padding: "var(--spacing-lg)",
};

/** 小节标题 */
function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between" style={{ gap: 12 }}>
      <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
        {children}
      </span>
      {hint && (
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {hint}
        </span>
      )}
    </div>
  );
}

/** 30 天课程脊梁总览 + 滑期决策（P1）。
 *
 * 回答「我落后了几天、哪些天需要决策」：
 *   - 顶部滑期横幅：课程进度 vs 日历进度，落后只提示不自动顺延
 *   - 4 个阶段分带，每带列出当日状态，标红的日期给出 压缩/顺延/放弃 三决策
 */
export default function PlanBoard({ overview }: Props) {
  const { days } = overview;
  // 按阶段分带（phase 1..4）
  const bands: { phase: number; name: string; items: PlanDayStatus[] }[] = [];
  for (const d of days) {
    let band = bands.find((b) => b.phase === d.phase);
    if (!band) {
      band = { phase: d.phase, name: d.phaseName, items: [] };
      bands.push(band);
    }
    band.items.push(d);
  }
  bands.sort((a, b) => a.phase - b.phase);

  return (
    <div className="flex flex-col" style={{ gap: 18 }}>
      {/* ═══════ 滑期横幅 ═══════ */}
      <SlipBanner overview={overview} />

      {overview.isBeforeStart && (
        <Notice tone="amber">
          冲刺窗口尚未开始（{overview.sprintStart} 起）。当前显示的是 Day 1，可按此预热。
        </Notice>
      )}
      {overview.isAfterEnd && (
        <Notice tone="rose">
          30 天窗口已结束（{overview.sprintEnd}）。如需延长，改 `target_roles.py` 的
          SPRINT_END 后重跑种子脚本。
        </Notice>
      )}

      {/* ═══════ 阶段分带 ═══════ */}
      {bands.map((band) => {
        const passed = band.items.filter(
          (d) => d.status === "done" || d.status === "compressed"
        ).length;
        return (
          <div key={band.phase} className="flex flex-col" style={{ ...cardStyle, gap: 14 }}>
            <SectionTitle
              hint={`通过 ${passed} / ${band.items.length}`}
            >
              {band.name}
            </SectionTitle>
            <div className="flex flex-col" style={{ gap: 8 }}>
              {band.items.map((d) => (
                <DayCard key={d.planDayId} day={d} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** 滑期横幅：课程进度 vs 日历进度。 */
function SlipBanner({ overview }: { overview: PlanOverview }) {
  const { behind, completedDays, totalDays, dayIndex, calendarDaysElapsed } = overview;

  return (
    <div
      className="flex flex-wrap items-center justify-between"
      style={{
        ...cardStyle,
        gap: 16,
        background: behind > 0 ? "var(--accent-warning-soft)" : "var(--accent-success-soft)",
        border: `1px solid ${behind > 0 ? "var(--accent-warning)" : "var(--accent-success)"}`,
      }}
    >
      <div className="flex flex-col" style={{ gap: 6, minWidth: 0 }}>
        <span
          className="text-[15px] font-semibold"
          style={{ color: behind > 0 ? "var(--accent-warning)" : "var(--accent-success)" }}
        >
          {behind > 0
            ? `落后 ${behind} 天 · 需要决策`
            : `进度正常 · 已通过 ${completedDays} / ${totalDays} 天`}
        </span>
        <span className="text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
          课程进度 Day {completedDays} / {totalDays}　·　日历已过 {calendarDaysElapsed} 天
          （今天算 Day {dayIndex}）
        </span>
      </div>
      {behind > 0 ? (
        <span className="text-xs" style={{ color: "var(--accent-warning)", lineHeight: 1.6 }}>
          落后只提示、不自动顺延：对下方标红日期手动选「压缩 / 顺延 / 放弃」，
          选择会记入偏离说明。
        </span>
      ) : (
        <Link
          href="/today"
          className="text-xs font-medium no-underline"
          style={{ color: "var(--accent-success)" }}
        >
          去今日施工单 →
        </Link>
      )}
    </div>
  );
}

/** 单日卡片：状态 + 滑期决策入口。 */
function DayCard({ day }: { day: PlanDayStatus }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [choice, setChoice] = useState<DayProgressStatus | null>(null);
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const meta = STATUS_META[day.status];
  const passed = day.status === "done" || day.status === "compressed";
  const needsDecision = day.isMissed && !passed;

  async function submit(status: DayProgressStatus, deviationNote: string) {
    if (pending) return;
    setPending(`decide-${day.planDayId}`);
    setError(null);
    try {
      await setDayProgress({
        planDayId: day.planDayId,
        status,
        deviationNote: deviationNote.trim() || undefined,
      });
      setEditing(false);
      setChoice(null);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setPending(null);
    }
  }

  function startDecision(status: DayProgressStatus) {
    const def = DECISIONS.find((x) => x.status === status)?.note ?? "";
    setChoice(status);
    setNote(def);
    setEditing(true);
  }

  return (
    <div
      className="flex flex-wrap items-center justify-between"
      style={{
        gap: 10,
        padding: "12px 14px",
        background: day.isMissed ? "#FEF7F2" : "var(--color-item-bg)",
        border: day.isMissed
          ? "1px solid var(--accent-warning)"
          : "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div className="flex flex-col" style={{ gap: 4, minWidth: 0 }}>
        <span className="flex items-center" style={{ gap: 8 }}>
          <span
            className="text-[13px] font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            Day {day.seq}
          </span>
          <span
            className="inline-flex items-center"
            style={{
              padding: "3px 9px",
              borderRadius: "var(--radius-pill)",
              fontSize: 11,
              fontWeight: 600,
              background: meta.bg,
              color: meta.fg,
            }}
          >
            {meta.label}
          </span>
          <span
            className="inline-flex items-center"
            style={{
              padding: "3px 9px",
              borderRadius: "var(--radius-pill)",
              fontSize: 11,
              fontWeight: 600,
              background: "var(--accent-primary-soft)",
              color: "var(--accent-primary)",
            }}
          >
            {TRACK_LABEL[day.trackKey] ?? day.trackKey}
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            约 {Math.round(day.estMinutes / 60)}h
          </span>
        </span>
        <span className="text-[14px] font-semibold" style={{ color: "var(--text-primary)" }}>
          {day.title}
        </span>
        {day.deviationNote && (
          <span
            className="text-[11px]"
            style={{ color: "var(--text-muted)", lineHeight: 1.5 }}
          >
            偏离说明：{day.deviationNote}
          </span>
        )}
      </div>

      {/* 决策区 */}
      <div className="flex flex-wrap items-center" style={{ gap: 8 }}>
        {editing ? (
          <div className="flex flex-col" style={{ gap: 8, minWidth: 240 }}>
            <div className="flex flex-wrap" style={{ gap: 8 }}>
              {DECISIONS.map((dec) => (
                <button
                  key={dec.status}
                  disabled={pending !== null}
                  onClick={() => startDecision(dec.status)}
                  className="border-none text-xs font-medium"
                  style={{
                    padding: "6px 12px",
                    borderRadius: "var(--radius-pill)",
                    cursor: pending ? "wait" : "pointer",
                    background:
                      choice === dec.status ? "var(--accent-primary)" : "var(--surface-card)",
                    color: choice === dec.status ? "var(--text-inverse)" : "var(--text-muted)",
                    border:
                      choice === dec.status
                        ? "none"
                        : "1px solid var(--border-default)",
                  }}
                >
                  {dec.label}
                </button>
              ))}
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="偏离说明（为什么压缩 / 顺延 / 放弃）"
              rows={2}
              className="text-xs"
              style={{
                width: "100%",
                padding: "8px 10px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-default)",
                color: "var(--text-primary)",
                resize: "vertical",
                fontFamily: "inherit",
              }}
            />
            <div className="flex" style={{ gap: 8 }}>
              <button
                disabled={pending !== null || choice === null}
                onClick={() => choice && submit(choice, note)}
                className="border-none text-xs font-medium"
                style={{
                  padding: "6px 14px",
                  borderRadius: "var(--radius-pill)",
                  background: "var(--accent-primary)",
                  color: "var(--text-inverse)",
                  cursor: pending || choice === null ? "wait" : "pointer",
                  opacity: pending || choice === null ? 0.6 : 1,
                }}
              >
                {pending ? "处理中…" : "确认决策"}
              </button>
              <button
                disabled={pending !== null}
                onClick={() => {
                  setEditing(false);
                  setChoice(null);
                  setError(null);
                }}
                className="border-none text-xs font-medium"
                style={{
                  padding: "6px 14px",
                  borderRadius: "var(--radius-pill)",
                  background: "transparent",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                取消
              </button>
            </div>
          </div>
        ) : needsDecision ? (
          <button
            onClick={() => setEditing(true)}
            className="border-none text-xs font-medium"
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-pill)",
              background: "var(--accent-warning-soft)",
              color: "var(--accent-warning)",
              cursor: "pointer",
            }}
          >
            决策
          </button>
        ) : day.status === "deferred" || day.status === "skipped" ? (
          <button
            onClick={() => setEditing(true)}
            className="border-none text-xs font-medium"
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-pill)",
              background: "transparent",
              color: "var(--text-muted)",
              cursor: "pointer",
            }}
          >
            重新决策
          </button>
        ) : null}
      </div>

      {error && (
        <span
          className="text-xs"
          style={{ color: "var(--accent-danger)", width: "100%" }}
        >
          {error}
        </span>
      )}
    </div>
  );
}

/** 提示条。 */
function Notice({ tone, children }: { tone: "amber" | "rose"; children: ReactNode }) {
  const map = {
    amber: { bg: "var(--accent-warning-soft)", fg: "var(--accent-warning)" },
    rose: { bg: "var(--accent-danger-soft)", fg: "var(--accent-danger)" },
  } as const;
  const c = map[tone];
  return (
    <div
      className="text-xs"
      style={{
        padding: "10px 14px",
        borderRadius: "var(--radius-md)",
        background: c.bg,
        color: c.fg,
        lineHeight: 1.6,
      }}
    >
      {children}
    </div>
  );
}
