"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type CSSProperties, type ReactNode } from "react";
import LearningLogCard from "@/components/LearningLogCard";
import ResourceList from "@/components/ResourceList";
import { createArtifact, deleteArtifact } from "@/services/planService";
import { updateTaskStatus } from "@/services/taskService";
import { syncCommits } from "@/services/experimentService";
import { ARTIFACT_META } from "@/types";
import type { ArtifactKind, LearningLog, Task, TodayView } from "@/types";

type Props = {
  today: TodayView;
  /** 学习日志（"今天学到什么"的内容位）。由 today/page.tsx 取好下发 */
  learningLogs?: LearningLog[];
};

const TRACK_LABEL: Record<string, string> = {
  llm: "LLM 主攻",
  vlm: "VLM 卡位",
  "ai-algo": "AI 算法保底",
  embodied: "具身智能（冻结）",
};

const STATUS_META: Record<string, { label: string; bg: string; fg: string }> = {
  todo: { label: "待办", bg: "#F5F5F5", fg: "var(--color-ink-32)" },
  doing: { label: "进行中", bg: "var(--color-amber-soft)", fg: "var(--color-amber-deep)" },
  done: { label: "已完成", bg: "var(--color-emerald-soft)", fg: "var(--color-emerald-deep)" },
};

const cardStyle: CSSProperties = {
  background: "var(--color-card)",
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-card-lg)",
  padding: "var(--spacing-lg)",
};

/** 小节标题 */
function SectionTitle({ children, hint }: { children: ReactNode; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between" style={{ gap: 12 }}>
      <span className="text-[15px] font-semibold" style={{ color: "var(--color-ink)" }}>
        {children}
      </span>
      {hint && (
        <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
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
 *   3. 今天做完没有     → 四件套勾选（缺哪几项一目了然）
 *
 * 四件套是本页的核心机制：现在的 Task.status 是人为切换的、没有客观标准，
 * 所以"完成"没有约束力；四件套（代码/笔记/面试题/commit）是可核验的。
 * P0 为手工一键勾选；P2 起 commit 由 GitHub 自动归集、面试题由题库条数判定。
 */
export default function TodayBoard({ today, learningLogs = [] }: Props) {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncMsg, setSyncMsg] = useState<string | null>(null);

  const { day } = today;
  const missing = today.missingKinds;
  const doneCount = ARTIFACT_META.length - missing.length;
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

  /** 点击四件套：已交则取消，未交则记录。 */
  function toggleArtifact(kind: ArtifactKind, existingId?: string) {
    const meta = ARTIFACT_META.find((m) => m.kind === kind);
    if (existingId) {
      void run(`artifact-${kind}`, () => deleteArtifact(existingId));
      return;
    }
    void run(`artifact-${kind}`, () =>
      createArtifact({
        planDayId: day.id,
        kind,
        title: `Day ${day.seq} · ${meta?.label ?? kind}`,
      })
    );
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
                color: "var(--color-ink)",
                letterSpacing: "-0.02em",
              }}
            >
              Day {day.seq}
              <span style={{ color: "var(--color-ink-48)", fontWeight: 500 }}>
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
                background: "var(--color-primary-soft)",
                color: "var(--color-primary)",
              }}
            >
              {TRACK_LABEL[day.trackKey] ?? day.trackKey}
            </span>
            <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
              {day.phaseName}
            </span>
          </div>
          <span
            className="text-[17px] font-semibold"
            style={{ color: "var(--color-ink)" }}
          >
            {day.title}
          </span>
        </div>

        <div
          className="flex shrink-0 flex-col items-end"
          style={{ gap: 4, textAlign: "right" }}
        >
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            预计投入 {Math.round(day.estMinutes / 60)} 小时
          </span>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            日历已过 {today.calendarDaysElapsed} 天 · 起 {today.sprintStart}
          </span>
          {viewingOtherDay && (
            <Link
              href="/today"
              className="text-xs font-medium no-underline"
              style={{ color: "var(--color-primary)" }}
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

      {/* ═══════ 今天做完没有：四件套 ═══════ */}
      <div className="flex flex-col" style={{ ...cardStyle, gap: 16 }}>
        <SectionTitle
          hint={
            missing.length === 0
              ? "今天的四件东西都交齐了"
              : `还差 ${missing.length} 项 · 已交 ${doneCount}/4`
          }
        >
          今天做完没有
        </SectionTitle>

        <div className="flex flex-wrap" style={{ gap: 10 }}>
          {ARTIFACT_META.map((meta) => {
            const count = today.artifactStatus[meta.kind] ?? 0;
            const done = count > 0;
            const isPending = pending === `artifact-${meta.kind}`;
            return (
              <button
                key={meta.kind}
                aria-pressed={done}
                disabled={isPending}
                onClick={() =>
                  toggleArtifact(meta.kind, done ? today.artifacts.find((a) => a.kind === meta.kind)?.id : undefined)
                }
                className="flex flex-1 flex-col items-start"
                style={{
                  gap: 4,
                  minWidth: 140,
                  padding: "14px 16px",
                  borderRadius: "var(--radius-item-md)",
                  border: `1px solid ${done ? "var(--color-emerald)" : "var(--color-hairline)"}`,
                  background: done ? "var(--color-emerald-soft)" : "var(--color-item-bg)",
                  cursor: isPending ? "wait" : "pointer",
                  opacity: isPending ? 0.6 : 1,
                  textAlign: "left",
                }}
              >
                <span className="flex items-center" style={{ gap: 6 }}>
                  <span
                    className="inline-flex items-center justify-center"
                    style={{
                      width: 16,
                      height: 16,
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 700,
                      background: done ? "var(--color-emerald)" : "var(--color-card)",
                      border: done ? "none" : "1px solid var(--color-hairline)",
                      color: done ? "var(--color-on-primary)" : "transparent",
                    }}
                  >
                    ✓
                  </span>
                  <span
                    className="text-[13px] font-semibold"
                    style={{
                      color: done ? "var(--color-emerald-deep)" : "var(--color-ink)",
                    }}
                  >
                    {meta.label}
                  </span>
                </span>
                <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
                  {done ? `已交 ${count} 条` : meta.hint}
                </span>
              </button>
            );
          })}
        </div>

        {today.artifacts.length > 0 && (
          <div className="flex flex-wrap" style={{ gap: 8 }}>
            {today.artifacts.map((a) => (
              <span
                key={a.id}
                className="inline-flex items-center"
                style={{
                  gap: 6,
                  padding: "4px 10px",
                  borderRadius: "var(--radius-pill)",
                  background: "var(--color-item-bg)",
                  border: "1px solid var(--color-hairline)",
                  fontSize: 11,
                  color: "var(--color-ink-32)",
                }}
              >
                {a.title ?? a.kind}
                <button
                  onClick={() => toggleArtifact(a.kind, a.id)}
                  disabled={pending !== null}
                  title="移除"
                  className="border-none"
                  style={{
                    background: "transparent",
                    cursor: "pointer",
                    color: "var(--color-ink-48)",
                    fontSize: 12,
                    lineHeight: 1,
                    padding: 0,
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between" style={{ gap: 10 }}>
          <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
            P2：commit 已从 GitHub 按日期自动归集（auto-verified）；面试题由题库当日条数判定
            {today.questionsFromBank > 0 && ` · 今日题库 ${today.questionsFromBank} 题`}。
          </span>
          <button
            disabled={pending === "sync"}
            onClick={() =>
              void run("sync", async () => {
                const r = await syncCommits();
                setSyncMsg(
                  r.skipped
                    ? `跳过：${r.reason ?? "未配置 GITHUB_TOKEN"}`
                    : `已归集 ${r.synced} 条 commit${r.error ? `（${r.error}）` : ""}`,
                );
              })
            }
            className="border-none text-xs font-medium"
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-pill)",
              background: "var(--color-violet-soft)",
              color: "var(--color-violet)",
              cursor: pending === "sync" ? "wait" : "pointer",
            }}
          >
            {pending === "sync" ? "同步中…" : "同步 GitHub commits"}
          </button>
        </div>

        {syncMsg && (
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            {syncMsg}
          </span>
        )}

        {error && (
          <span className="text-xs" style={{ color: "var(--color-rose-deep)" }}>
            {error}
          </span>
        )}
      </div>

      {/* ═══════ 今天学到什么（内容位）═══════
          四件套只记"勾没勾"，这里记"到底做了什么" —— 记录系统与成长系统的分界。 */}
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
                    background: "var(--color-primary-soft)",
                    color: "var(--color-primary)",
                  }}
                >
                  {i + 1}
                </span>
                <span
                  className="text-[13px]"
                  style={{ color: "var(--color-ink-80)", lineHeight: 1.6 }}
                >
                  {item}
                </span>
              </li>
            ))}
          </ol>

          {day.objectives.length > 0 && (
            <>
              <div style={{ height: 1, background: "var(--color-hairline-soft)" }} />
              <SectionTitle>学习目标</SectionTitle>
              <ul className="flex flex-col" style={{ gap: 8, margin: 0, padding: 0, listStyle: "none" }}>
                {day.objectives.map((item, i) => (
                  <li
                    key={i}
                    className="text-[13px]"
                    style={{ color: "var(--color-ink-80)", lineHeight: 1.6 }}
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
                style={{ color: "var(--color-ink-80)", lineHeight: 1.6 }}
              >
                {q}
              </span>
            ))}
          </div>

          <div style={{ height: 1, background: "var(--color-hairline-soft)" }} />
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
          <span className="text-xs" style={{ color: "var(--color-ink-48)", lineHeight: 1.7 }}>
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
                  borderRadius: "var(--radius-item-md)",
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
                      <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                        {task.skill}
                      </span>
                    )}
                  </span>
                  <span
                    className="text-[14px] font-semibold"
                    style={{ color: "var(--color-ink)" }}
                  >
                    {task.title}
                  </span>
                  {task.objective && (
                    <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
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
                      background: "var(--color-primary-soft)",
                      color: "var(--color-primary)",
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
                  <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                    {item.label}
                  </span>
                  <span
                    className="text-[13px] font-semibold"
                    style={{ color: "var(--color-ink)" }}
                  >
                    {item.done}
                    <span style={{ color: "var(--color-ink-48)", fontWeight: 400 }}>
                      /{item.target}
                    </span>
                  </span>
                </span>
                <span
                  style={{
                    height: 4,
                    borderRadius: 999,
                    background: "var(--color-hairline-soft)",
                    overflow: "hidden",
                    display: "block",
                  }}
                >
                  <span
                    style={{
                      display: "block",
                      height: "100%",
                      width: `${pct}%`,
                      background: pct >= 100 ? "var(--color-emerald)" : "var(--color-primary)",
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
    amber: { bg: "var(--color-amber-soft)", fg: "var(--color-amber-deep)" },
    rose: { bg: "var(--color-rose-soft)", fg: "var(--color-rose-deep)" },
  } as const;
  const c = map[tone];
  return (
    <div
      className="text-xs"
      style={{
        padding: "10px 14px",
        borderRadius: "var(--radius-item-md)",
        background: c.bg,
        color: c.fg,
        lineHeight: 1.6,
      }}
    >
      {children}
    </div>
  );
}
