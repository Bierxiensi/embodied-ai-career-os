"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type CSSProperties, type ReactNode } from "react";
import LearningLogCard from "@/components/LearningLogCard";
import ResourceList from "@/components/ResourceList";
import TodayCompletion from "@/components/TodayCompletion";
import { updateTaskStatus } from "@/services/taskService";
import type { LearningLog, MasteryUnit, Task, TodayView } from "@/types";

type Props = {
  today: TodayView;
  /** 学习日志（"今天学到什么"的内容位）。由 learn/page.tsx 取好下发 */
  learningLogs?: LearningLog[];
  /** 今日掌握单元（可选）。由 learn/page.tsx 服务端取好下发，
   * 供完成度三选一派生"测验实证过"（计划 2）。 */
  unit?: MasteryUnit | null;
};

const TRACK_LABEL: Record<string, string> = {
  llm: "LLM 主攻",
  vlm: "VLM 卡位",
  "ai-algo": "AI 算法保底",
  embodied: "具身智能（冻结）",
};

const STATUS_META: Record<string, { label: string; bg: string; fg: string }> = {
  todo: { label: "待办", bg: "#F5F5F5", fg: "var(--text-muted)" },
  doing: { label: "进行中", bg: "var(--accent-warning-soft)", fg: "var(--accent-warning)" },
  done: { label: "已完成", bg: "var(--accent-success-soft)", fg: "var(--accent-success)" },
};

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

/** 今日施工单（客户端交互层）。
 *
 * 这是把平台从「展示」变「学习」的那一页 —— 它回答三个问题：
 *   1. 今天第几天       → 顶部 Day 条
 *   2. 今天干什么       → 学习目标 / 验收标准 / 今日任务
 *   3. 今天做完没有     → 完成度三选一（测验过 / Teach-Back 过 / 证据挂上）
 *
 * 完成判据（spec §3.2）不再是四件套布尔勾选 —— 勾选没有约束力、可手点。
 * TodayCompletion 从真实记录派生：unit 的 isVerified、Teach-Back 学习日志、
 * 带 artifactUrl 的证据。四件套后端端点不动（撤 UI 留数据，spec D5）。
 */
export default function TodayBoard({ today, learningLogs = [], unit = null }: Props) {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { day } = today;
  const viewingOtherDay = day.seq !== today.dayIndex;

  /** 执行一次异步动作：锁定 → 刷新 → 解锁。失败时把 message 透到界面。 */
  async function run(key: string, fn: () => Promise<unknown>) {
    if (pending) return;
    setPending(key);
    setError(null);
    try {
      await fn();
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setPending(null);
    }
  }

  // 口径提示文案：只在"确实有任务被排除"或"有未归类任务"时出现，
  // 无事可提示时保持页面干净。措辞与数字全部取自后端，前端不加工。
  const scopeNotice = (() => {
    const s = today.taskScope;
    if (!s) return null;
    const parts: string[] = [];
    if (s.frozenExcluded > 0) {
      parts.push(`已排除冻结赛道任务 ${s.frozenExcluded} 条（${s.scopeReason}）`);
    }
    if (s.unclassified > 0) {
      parts.push(`另有 ${s.unclassified} 条任务未归类赛道，仍列在下方`);
    }
    return parts.length > 0 ? parts.join("；") : null;
  })();

  return (
    <div className="flex flex-col" style={{ gap: 18 }}>
      {/* ═══════ 顶部：今天第几天 ═══════ */}
      <div
        className="flex flex-wrap items-center justify-between"
        style={{ ...cardStyle, gap: 20 }}
      >
        <div className="flex flex-col" style={{ gap: 8, minWidth: 0 }}>
          <div className="flex items-center" style={{ gap: 12, flexWrap: "wrap" }}>
            <span
              className="font-semibold"
              style={{
                fontSize: 28,
                lineHeight: 1,
                color: "var(--text-primary)",
                letterSpacing: "-0.02em",
              }}
            >
              Day {day.seq}
              <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>
                {" "}
                / {today.totalDays}
              </span>
            </span>
            <span
              className="inline-flex items-center"
              style={{
                padding: "4px 10px",
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
              {day.phaseName}
            </span>
          </div>
          <span
            className="text-[17px] font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            {day.title}
          </span>
        </div>

        <div
          className="flex shrink-0 flex-col items-end"
          style={{ gap: 4, textAlign: "right" }}
        >
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            预计投入 {Math.round(day.estMinutes / 60)} 小时
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            日历已过 {today.calendarDaysElapsed} 天 · 起 {today.sprintStart}
          </span>
          {viewingOtherDay && (
            <Link
              href="/today"
              className="text-xs font-medium no-underline"
              style={{ color: "var(--accent-primary)" }}
            >
              回到今天（Day {today.dayIndex}）→
            </Link>
          )}
        </div>
      </div>

      {today.isBeforeStart && (
        <Notice tone="amber">
          冲刺窗口尚未开始（{today.sprintStart} 起）。当前显示的是 Day 1，可按此预热。
        </Notice>
      )}
      {today.isAfterEnd && (
        <Notice tone="rose">
          30 天窗口已结束。如果计划延长，请改 `target_roles.py` 的 SPRINT_END 后重跑种子脚本。
        </Notice>
      )}

      {/* ═══════ 今天做完没有：完成度三选一（spec §3.2）═══════
          不是布尔勾选：从 unit 实证状态 + 学习日志派生，不可手点。 */}
      <TodayCompletion unit={unit} logs={learningLogs} />

      {error && (
        <span className="text-xs" style={{ color: "var(--accent-danger)" }}>
          {error}
        </span>
      )}

      {/* ═══════ 今天学到什么（内容位）═══════
          完成度记"做没做到"，这里记"到底做了什么" —— 记录系统与成长系统的分界。 */}
      <LearningLogCard logs={learningLogs} />

      {/* ═══════ 今天干什么 ═══════ */}
      <div className="flex flex-wrap" style={{ gap: 18 }}>
        <div
          className="flex flex-col"
          style={{ ...cardStyle, flex: "1 1 380px", minWidth: 0, gap: 16 }}
        >
          <SectionTitle hint="做到什么算过">验收标准</SectionTitle>
          <ol className="flex flex-col" style={{ gap: 10, margin: 0, padding: 0, listStyle: "none" }}>
            {day.acceptance.map((item, i) => (
              <li key={i} className="flex" style={{ gap: 10 }}>
                <span
                  className="shrink-0 text-[11px] font-semibold"
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: 999,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "var(--accent-primary-soft)",
                    color: "var(--accent-primary)",
                  }}
                >
                  {i + 1}
                </span>
                <span
                  className="text-[13px]"
                  style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}
                >
                  {item}
                </span>
              </li>
            ))}
          </ol>

          {day.objectives.length > 0 && (
            <>
              <div style={{ height: 1, background: "var(--border-subtle)" }} />
              <SectionTitle>学习目标</SectionTitle>
              <ul className="flex flex-col" style={{ gap: 8, margin: 0, padding: 0, listStyle: "none" }}>
                {day.objectives.map((item, i) => (
                  <li
                    key={i}
                    className="text-[13px]"
                    style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}
                  >
                    · {item}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div
          className="flex flex-col"
          style={{ ...cardStyle, flex: "1 1 320px", minWidth: 0, gap: 16 }}
        >
          <SectionTitle hint="能答出来才算过">面试题主题</SectionTitle>
          <div className="flex flex-col" style={{ gap: 8 }}>
            {day.interviewTopics.map((q, i) => (
              <span
                key={i}
                className="text-[13px]"
                style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}
              >
                {q}
              </span>
            ))}
          </div>

          <div style={{ height: 1, background: "var(--border-subtle)" }} />
          {/* 口径：不写死数字 —— 资源锁曾从 5 类扩到 8 类，而这里一度仍写着"这 5 类"。
              写死的数字是负债，下次还会变。 */}
          <SectionTitle hint="均来自资源锁，不得自选">指定资源</SectionTitle>
          <ResourceList names={day.resources} />
        </div>
      </div>

      {/* ═══════ 今日任务 ═══════ */}
      <div className="flex flex-col" style={{ ...cardStyle, gap: 14 }}>
        <SectionTitle hint={`完成 ${today.completedTasks} / ${today.tasks.length} 项`}>
          今日任务
        </SectionTitle>

        {/* 口径提示（Milestone B）：为什么这里的条数比"当天全部任务"少。
            数字与措辞全部来自后端 taskScope，前端不重算、不改口径。 */}
        {scopeNotice ? <Notice tone="amber">{scopeNotice}</Notice> : null}

        {today.tasks.length === 0 ? (
          <span className="text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
            这一天还没有绑定的任务。本日的执行内容以上方「验收标准」为准；
            Planning 生成的任务会自动挂到当天（P1 起支持在页面内直接生成）。
          </span>
        ) : (
          today.tasks.map((task: Task) => {
            const meta = STATUS_META[task.status] ?? STATUS_META.todo;
            const busy = pending === `task-${task.id}`;
            return (
              <div
                key={task.id}
                className="flex flex-wrap items-center justify-between"
                style={{
                  gap: 10,
                  padding: "12px 14px",
                  background: "var(--color-item-bg)",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <div className="flex flex-col" style={{ gap: 4, minWidth: 0 }}>
                  <span className="flex items-center" style={{ gap: 8 }}>
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
                    {task.skill && (
                      <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                        {task.skill}
                      </span>
                    )}
                  </span>
                  <span
                    className="text-[14px] font-semibold"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {task.title}
                  </span>
                  {task.objective && (
                    <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                      {task.objective}
                    </span>
                  )}
                </div>

                {task.status !== "done" && (
                  <button
                    disabled={busy}
                    onClick={() =>
                      void run(`task-${task.id}`, () =>
                        updateTaskStatus(task.id, "done")
                      )
                    }
                    className="shrink-0 border-none text-xs font-medium"
                    style={{
                      padding: "6px 12px",
                      borderRadius: "var(--radius-pill)",
                      background: "var(--accent-primary-soft)",
                      color: "var(--accent-primary)",
                      cursor: busy ? "wait" : "pointer",
                    }}
                  >
                    {busy ? "处理中…" : "标记完成"}
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* ═══════ 总账 ═══════ */}
      <div className="flex flex-col" style={{ ...cardStyle, gap: 14 }}>
        <SectionTitle hint="30 天累计口径（计划 §十）">总账</SectionTitle>
        <div className="flex flex-wrap" style={{ gap: 14 }}>
          {today.ledger.map((item) => {
            const pct = item.target > 0 ? Math.min(100, Math.round((item.done / item.target) * 100)) : 0;
            return (
              <div
                key={item.key}
                className="flex flex-col"
                style={{ flex: "1 1 120px", minWidth: 110, gap: 6 }}
              >
                <span className="flex items-baseline justify-between" style={{ gap: 6 }}>
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {item.label}
                  </span>
                  <span
                    className="text-[13px] font-semibold"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {item.done}
                    <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>
                      /{item.target}
                    </span>
                  </span>
                </span>
                <span
                  style={{
                    height: 4,
                    borderRadius: 999,
                    background: "var(--border-subtle)",
                    overflow: "hidden",
                    display: "block",
                  }}
                >
                  <span
                    style={{
                      display: "block",
                      height: "100%",
                      width: `${pct}%`,
                      background: pct >= 100 ? "var(--accent-success)" : "var(--accent-primary)",
                    }}
                  />
                </span>
              </div>
            );
          })}
        </div>
      </div>
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
