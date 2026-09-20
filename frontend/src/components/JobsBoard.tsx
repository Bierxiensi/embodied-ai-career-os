"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import type {
  JobAppStatus,
  JobHuntBoard,
  ScopedTaskRef,
  TargetRole,
  TaskScopeSummary,
} from "@/types";

/* ───────────────────────── 元数据 ───────────────────────── */

const APP_STATUS_META: Record<
  JobAppStatus,
  { label: string; color: string; soft: string }
> = {
  applied: { label: "已投递", color: "var(--color-ink-48)", soft: "var(--color-zinc-100)" },
  screening: { label: "筛选中", color: "#0EA5E9", soft: "rgba(14,165,233,0.12)" },
  interview: { label: "面试中", color: "#8B5CF6", soft: "rgba(139,92,246,0.12)" },
  offer: { label: "已拿offer", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  rejected: { label: "已挂", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
};

const PRIORITY_META: Record<string, { label: string; color: string; soft: string }> = {
  主攻: { label: "主攻", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
  卡位: { label: "卡位", color: "#8B5CF6", soft: "rgba(139,92,246,0.12)" },
  折中: { label: "折中", color: "#0EA5E9", soft: "rgba(14,165,233,0.12)" },
  保底: { label: "保底", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  暂缓: { label: "暂缓 · 不投入", color: "var(--color-ink-48)", soft: "rgba(0,0,0,0.05)" },
};

const TRACK_LABEL: Record<string, string> = {
  llm: "LLM",
  vlm: "VLM / 多模态",
  "ai-algo": "AI 算法",
  agent: "Agent",
  embodied: "具身",
  "robot-software": "机器人软件",
  other: "其他",
};

const GRADE_META: Record<string, { label: string; color: string; soft: string }> = {
  A: { label: "A · 强匹配", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  B: { label: "B · 正常投", color: "#0EA5E9", soft: "rgba(14,165,233,0.12)" },
  C: { label: "C · 练手", color: "var(--color-amber)", soft: "var(--color-amber-soft)" },
  D: { label: "D · 不推荐", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
};

/* ───────────────────────── 复用样式 ───────────────────────── */

const cardStyle: React.CSSProperties = {
  padding: 24,
  background: "var(--color-card)",
  border: "1px solid var(--color-hairline)",
  borderRadius: "var(--radius-card-lg)",
};

const sectionTitleStyle: React.CSSProperties = {
  fontSize: 15,
  fontWeight: 600,
  color: "var(--color-ink)",
  letterSpacing: "-0.01em",
};

/* ───────────────────────── 小组件 ───────────────────────── */

function Pill({
  label,
  color,
  soft,
}: {
  label: string;
  color: string;
  soft: string;
}) {
  return (
    <span
      style={{
        padding: "3px 10px",
        borderRadius: "var(--radius-pill)",
        fontSize: 12,
        fontWeight: 600,
        color,
        background: soft,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}

function SectionHeader({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
      <h2 style={sectionTitleStyle}>{title}</h2>
      {hint ? (
        <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{hint}</span>
      ) : null}
    </div>
  );
}

function MatchBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div
      style={{
        height: 6,
        width: "100%",
        background: "var(--color-zinc-100)",
        borderRadius: "var(--radius-pill)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: "100%",
          width: `${Math.min(100, Math.max(0, pct))}%`,
          background: color,
          borderRadius: "var(--radius-pill)",
        }}
      />
    </div>
  );
}

function MilestoneStatusBadge({ status }: { status: string }) {
  let label = "待启动";
  let color = "var(--color-ink-48)";
  let soft = "var(--color-zinc-100)";
  if (status === "completed") {
    label = "已完成";
    color = "var(--color-emerald)";
    soft = "var(--color-emerald-soft)";
  } else if (status === "doing" || status === "in_progress") {
    label = "进行中";
    color = "var(--color-amber)";
    soft = "var(--color-amber-soft)";
  }
  return <Pill label={label} color={color} soft={soft} />;
}

/* ───────────────────────── 主组件 ───────────────────────── */

type Props = {
  board: JobHuntBoard;
};

export default function JobsBoard({ board }: Props) {
  const daysLeft = board.daysLeft;
  const urgency =
    daysLeft > 21
      ? "var(--color-emerald)"
      : daysLeft > 7
        ? "var(--color-amber)"
        : "var(--color-rose)";
  const usedPct = Math.max(
    0,
    Math.min(100, Math.round(((90 - daysLeft) / 90) * 100))
  );

  const career = board.career;

  const topGaps = useMemo(
    () => [...board.skillGaps].sort((a, b) => b.gap - a.gap).slice(0, 8),
    [board.skillGaps]
  );

  /* 投递漏斗（从后端聚合数据读取） */
  const funnel = board.applications;

  return (
    <div className="flex flex-1 flex-col">
      <div
        className="flex flex-col"
        style={{
          gap: "var(--spacing-lg)",
          padding: "36px clamp(20px, 8vw, 120px) 48px",
        }}
      >
        {/* Page Header */}
        <div className="flex flex-col" style={{ gap: 8 }}>
          <span
            className="text-xs font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            JOB HUNT · 2026 Q4
          </span>
          <h1
            className="font-semibold"
            style={{
              fontSize: 40,
              color: "var(--color-ink)",
              letterSpacing: "-0.02em",
            }}
          >
            求职作战看板
          </h1>
          <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
            从学习记录切换到投递作战 · 主攻 LLM 大模型，卡位多模态/VLM，保底 AI 算法
          </p>
        </div>

        {/* Offer Countdown Banner */}
        <div
          style={{
            ...cardStyle,
            display: "flex",
            alignItems: "center",
            gap: 28,
            borderColor: urgency,
          }}
        >
          <div className="flex flex-col" style={{ alignItems: "center", minWidth: 120 }}>
            <span
              className="font-semibold"
              style={{ fontSize: 56, color: urgency, lineHeight: 1, letterSpacing: "-0.03em" }}
            >
              {daysLeft}
            </span>
            <span style={{ fontSize: 13, color: "var(--color-ink-48)" }}>天 · 距签约截止</span>
          </div>
          <div className="flex flex-1 flex-col" style={{ gap: 10 }}>
            <div className="flex items-center" style={{ gap: 12, flexWrap: "wrap" }}>
              <span style={{ fontSize: 14, color: "var(--color-ink-80)" }}>
                截止日 <b style={{ color: "var(--color-ink)" }}>{board.offerDeadline}</b>
              </span>
              {career?.salaryTarget ? (
                <Pill
                  label={`目标薪资 ¥${career.salaryTarget / 1000}K`}
                  color="var(--color-primary)"
                  soft="var(--color-primary-soft)"
                />
              ) : null}
              {career?.targetRole ? (
                <span style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
                  {career.targetRole}
                </span>
              ) : null}
            </div>
            <div
              style={{
                height: 6,
                width: "100%",
                background: "var(--color-zinc-100)",
                borderRadius: "var(--radius-pill)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${usedPct}%`,
                  background: urgency,
                  borderRadius: "var(--radius-pill)",
                }}
              />
            </div>
            <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
              冲刺进度约 {usedPct}% · 10月底前落定以防社保中断
            </span>
          </div>
        </div>

        {/* Target Roles */}
        <div style={cardStyle}>
          <SectionHeader title="目标岗位画像" hint="当前技能匹配度（后端实时计算）" />
          <div
            className="grid"
            style={{ gap: "var(--spacing-md)", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}
          >
            {board.targetRoles.map((role) => (
              <TargetRoleCard key={role.key} role={role} />
            ))}
          </div>
        </div>

        {/* Recommended Job Pool */}
        {board.jobPool && board.jobPool.total > 0 ? (
          <div style={cardStyle}>
            <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
              <h2 style={sectionTitleStyle}>推荐岗位（来自岗位池）</h2>
              <Link
                href="/jobs/pool"
                className="text-xs font-semibold no-underline"
                style={{ color: "var(--color-primary)" }}
              >
                去岗位池 →
              </Link>
            </div>
            <div className="flex items-center" style={{ gap: 16, flexWrap: "wrap", marginBottom: 14 }}>
              <FunnelStat label="岗位总数" value={board.jobPool.total} color="var(--color-ink)" />
              <FunnelStat label="可优先投 A+B" value={board.jobPool.recommended} color="var(--color-emerald)" />
            </div>
            <div className="flex flex-col" style={{ gap: 8 }}>
              {board.jobPool.top.map((t) => (
                <Link
                  key={t.id}
                  href="/jobs/pool"
                  className="flex items-center no-underline"
                  style={{
                    gap: 12,
                    padding: "10px 14px",
                    border: "1px solid var(--color-hairline-soft)",
                    borderRadius: "var(--radius-item-md)",
                  }}
                >
                  <div className="flex flex-col" style={{ gap: 2, flex: 1, minWidth: 160 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>{t.company}</span>
                    <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
                      {t.title} · {TRACK_LABEL[t.track] || t.track}
                    </span>
                  </div>
                  <span
                    style={{
                      padding: "3px 10px",
                      borderRadius: "var(--radius-pill)",
                      fontSize: 12,
                      fontWeight: 700,
                      color: GRADE_META[t.grade]?.color || "var(--color-ink-48)",
                      background: GRADE_META[t.grade]?.soft || "var(--color-zinc-100)",
                    }}
                  >
                    {t.grade} · {t.matchScore}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        ) : null}

        {/* Skill Gaps + Project Milestones */}
        <div className="flex flex-col" style={{ gap: "var(--spacing-lg)" }}>
          <div style={cardStyle}>
            <SectionHeader title="技能缺口" hint="按差距降序 · 优先补强" />
            {topGaps.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>暂无缺口数据。</p>
            ) : (
              <div className="flex flex-col" style={{ gap: 12 }}>
                {topGaps.map((g) => (
                  <div key={g.name} className="flex items-center" style={{ gap: 14 }}>
                    <div style={{ width: 130, flexShrink: 0 }}>
                      <span style={{ fontSize: 14, color: "var(--color-ink)", fontWeight: 500 }}>
                        {g.name}
                      </span>
                      <span style={{ fontSize: 12, color: "var(--color-ink-48)", marginLeft: 6 }}>
                        {g.level}→{g.targetLevel}
                      </span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <MatchBar pct={(g.gap / 5) * 100} color="var(--color-rose)" />
                    </div>
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 600,
                        color: "var(--color-rose-deep)",
                        width: 28,
                        textAlign: "right",
                      }}
                    >
                      +{g.gap}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={cardStyle}>
            <SectionHeader
              title={board.jobProject?.name || "求职项目里程碑"}
              hint={
                board.jobProject
                  ? `${board.jobProject.milestoneCompleted}/${board.jobProject.milestoneTotal} 已完成`
                  : undefined
              }
            />
            {board.jobProject && board.jobProject.milestones.length > 0 ? (
              <div className="flex flex-col" style={{ gap: 0 }}>
                {board.jobProject.milestones.map((m, i, arr) => (
                  <div key={m.id} className="flex" style={{ gap: 14 }}>
                    <div className="flex flex-col" style={{ alignItems: "center" }}>
                      <span
                        style={{
                          width: 26,
                          height: 26,
                          borderRadius: "var(--radius-pill)",
                          background:
                            m.status === "completed"
                              ? "var(--color-emerald)"
                              : m.status === "doing" || m.status === "in_progress"
                                ? "var(--color-amber)"
                                : "var(--color-zinc-100)",
                          color:
                            m.status === "completed" || m.status === "doing" || m.status === "in_progress"
                              ? "#fff"
                              : "var(--color-ink-48)",
                          fontSize: 11,
                          fontWeight: 700,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                        }}
                      >
                        {m.version}
                      </span>
                      {i < arr.length - 1 ? (
                        <div style={{ flex: 1, width: 2, background: "var(--color-hairline)" }} />
                      ) : null}
                    </div>
                    <div className="flex flex-col" style={{ gap: 4, paddingBottom: i < arr.length - 1 ? 16 : 0 }}>
                      <div className="flex items-center" style={{ gap: 10 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>
                          {m.title}
                        </span>
                        <MilestoneStatusBadge status={m.status} />
                      </div>
                      <span style={{ fontSize: 12, color: "var(--color-ink-48)", lineHeight: 1.5 }}>
                        {m.goal}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
                尚未创建求职项目，运行 seed_job_hunt.py 初始化。
              </p>
            )}
          </div>
        </div>

        {/* This Week Tasks */}
        <div style={cardStyle}>
          <SectionHeader
            title="本周任务"
            hint={
              board.tasks.frozenExcluded > 0
                ? `${board.tasks.done}/${board.tasks.total} 已完成 · 已排除冻结赛道 ${board.tasks.frozenExcluded} 条`
                : `${board.tasks.done}/${board.tasks.total} 已完成`
            }
          />

          <TaskScopeNote
            scope={board.tasks.scope}
            unclassified={board.tasks.unclassified}
            frozenItems={board.tasks.frozenItems}
          />

          <div className="flex flex-col" style={{ gap: 10 }}>
            {board.tasks.items.slice(0, 6).map((t) => (
              <div
                key={t.id}
                className="flex items-center"
                style={{ gap: 12, justifyContent: "space-between" }}
              >
                <div className="flex items-center" style={{ gap: 10 }}>
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "var(--radius-pill)",
                      background:
                        t.status === "done"
                          ? "var(--color-emerald)"
                          : t.status === "doing"
                            ? "var(--color-amber)"
                            : "var(--color-zinc-100)",
                    }}
                  />
                  <span style={{ fontSize: 14, color: "var(--color-ink)" }}>{t.title}</span>
                </div>
                <div className="flex items-center" style={{ gap: 8 }}>
                  {t.skillName ? (
                    <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{t.skillName}</span>
                  ) : null}
                  <Pill
                    label={t.status === "done" ? "已完成" : t.status === "doing" ? "进行中" : "待办"}
                    color={
                      t.status === "done"
                        ? "var(--color-emerald)"
                        : t.status === "doing"
                          ? "var(--color-amber)"
                          : "var(--color-ink-48)"
                    }
                    soft={
                      t.status === "done"
                        ? "var(--color-emerald-soft)"
                        : t.status === "doing"
                          ? "var(--color-amber-soft)"
                          : "var(--color-zinc-100)"
                    }
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Applications Summary */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
            <h2 style={sectionTitleStyle}>投递漏斗</h2>
            <Link
              href="/jobs/applications"
              className="text-xs font-semibold no-underline"
              style={{ color: "var(--color-primary)" }}
            >
              管理投递 →
            </Link>
          </div>
          <div
            className="grid"
            style={{ gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))" }}
          >
            <FunnelStat label="已投递" value={funnel.byStatus.applied ?? 0} color="var(--color-ink-48)" />
            <FunnelStat label="筛选中" value={funnel.byStatus.screening ?? 0} color="#0EA5E9" />
            <FunnelStat label="面试中" value={funnel.byStatus.interview ?? 0} color="#8B5CF6" />
            <FunnelStat label="已拿offer" value={funnel.byStatus.offer ?? 0} color="var(--color-emerald)" />
            <FunnelStat label="已挂" value={funnel.byStatus.rejected ?? 0} color="var(--color-rose)" />
            <FunnelStat label="回复率" value={`${funnel.responseRate}%`} color="var(--color-primary)" />
          </div>
        </div>

        <footer style={{ fontSize: 12, color: "var(--color-ink-48)", textAlign: "center", paddingTop: 8 }}>
          Career OS · 求职作战看板 · 数据来自 /api/job-hunt
        </footer>
      </div>
    </div>
  );
}

/* ───────────────────────── 子组件（同文件内联） ───────────────────────── */

/** 任务口径说明 + 「已排除任务」查看入口。 */
function TaskScopeNote({
  scope,
  unclassified,
  frozenItems,
}: {
  scope: TaskScopeSummary;
  unclassified: number;
  frozenItems: ScopedTaskRef[];
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!scope.scopeReason && unclassified === 0 && frozenItems.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col" style={{ gap: 8, marginBottom: 12 }}>
      {scope.scopeReason ? (
        <p style={{ fontSize: 12, color: "var(--color-ink-48)", lineHeight: 1.6 }}>
          {scope.scopeReason}
        </p>
      ) : null}

      {unclassified > 0 ? (
        <p style={{ fontSize: 12, color: "var(--color-ink-48)", lineHeight: 1.6 }}>
          另有 {unclassified} 条任务未归类赛道（历史 / 手写任务），仍列在下方。
        </p>
      ) : null}

      {frozenItems.length > 0 ? (
        <>
          <button
            type="button"
            onClick={() => setIsExpanded((previous) => !previous)}
            aria-expanded={isExpanded}
            style={{
              alignSelf: "flex-start",
              padding: "5px 12px",
              borderRadius: "var(--radius-pill)",
              border: "1px solid var(--color-hairline)",
              background: "transparent",
              color: "var(--color-ink-48)",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isExpanded ? "收起已排除任务" : `查看已排除的 ${frozenItems.length} 条冻结赛道任务`}
          </button>

          {isExpanded ? (
            <div className="flex flex-col" style={{ gap: 6 }}>
              {frozenItems.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center"
                  style={{ gap: 10, justifyContent: "space-between" }}
                >
                  <span style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
                    {task.title}
                  </span>
                  <Pill
                    label="冻结 · 不计入"
                    color="var(--color-ink-48)"
                    soft="var(--color-zinc-100)"
                  />
                </div>
              ))}
              <span style={{ fontSize: 11, color: "var(--color-ink-48)", lineHeight: 1.6 }}>
                这些任务只是不进默认统计与今日推荐，记录本身完整保留，随时可在任务页查看。
              </span>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function TargetRoleCard({ role }: { role: TargetRole }) {
  const pri = PRIORITY_META[role.priority] ?? PRIORITY_META["保底"];
  const matchColor =
    role.matchPct >= 60 ? "var(--color-emerald)" : role.matchPct >= 35 ? "var(--color-amber)" : "var(--color-rose)";
  return (
    <div
      style={{
        ...cardStyle,
        border: "1px solid var(--color-hairline)",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        opacity: role.frozen ? 0.62 : 1,
      }}
    >
      <div className="flex items-center justify-between">
        <Pill label={pri.label} color={pri.color} soft={pri.soft} />
        <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{role.salaryRange}</span>
      </div>
      <span style={{ fontSize: 15, fontWeight: 600, color: "var(--color-ink)" }}>{role.name}</span>

      <div className="flex items-center" style={{ gap: 10 }}>
        <span style={{ fontSize: 28, fontWeight: 700, color: matchColor, letterSpacing: "-0.02em" }}>
          {role.matchPct}%
        </span>
        <div style={{ flex: 1 }}>
          <MatchBar pct={role.matchPct} color={matchColor} />
        </div>
      </div>

      <div className="flex flex-col" style={{ gap: 6 }}>
        {role.skills.map((s) => (
          <div key={s.name} className="flex items-center" style={{ gap: 8 }}>
            <span style={{ fontSize: 12, width: 96, color: s.missing ? "var(--color-rose-deep)" : "var(--color-ink-80)" }}>
              {s.name}
              {s.missing ? " · 缺" : ""}
            </span>
            <div style={{ flex: 1 }}>
              <MatchBar
                pct={(s.level / Math.max(1, s.required)) * 100}
                color={s.gap > 0 ? "var(--color-amber)" : "var(--color-emerald)"}
              />
            </div>
            <span style={{ fontSize: 11, color: "var(--color-ink-48)", width: 30, textAlign: "right" }}>
              {s.level}/{s.required}
            </span>
          </div>
        ))}
      </div>

      <span style={{ fontSize: 11, color: "var(--color-ink-48)", lineHeight: 1.5 }}>{role.note}</span>
    </div>
  );
}

function FunnelStat({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div
      style={{
        padding: 14,
        background: "var(--color-zinc-100)",
        borderRadius: "var(--radius-item-md)",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        alignItems: "flex-start",
      }}
    >
      <span style={{ fontSize: 22, fontWeight: 700, color }}>{value}</span>
      <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{label}</span>
    </div>
  );
}
