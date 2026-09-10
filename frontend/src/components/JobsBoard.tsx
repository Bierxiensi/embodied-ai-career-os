"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import type {
  JobAppStatus,
  JobApplication,
  JobApplicationCreate,
  JobHuntBoard,
  TargetRole,
} from "@/types";
import {
  createApplication,
  deleteApplication,
  updateApplication,
} from "@/services/jobHuntService";

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

const STATUS_ORDER: JobAppStatus[] = [
  "applied",
  "screening",
  "interview",
  "offer",
  "rejected",
];

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
  const [apps, setApps] = useState<JobApplication[]>(board.applications.items);
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<JobApplicationCreate>({
    company: "",
    role: "",
    track: "agent",
    source: "",
    status: "applied",
    salaryRange: "",
    appliedAt: null,
    nextAction: "",
  });

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

  /* 投递漏斗统计（从本地列表实时计算） */
  const funnel = useMemo(() => {
    const by: Record<JobAppStatus, number> = {
      applied: 0,
      screening: 0,
      interview: 0,
      offer: 0,
      rejected: 0,
    };
    for (const a of apps) by[a.status] += 1;
    const total = apps.length;
    const responded = by.screening + by.interview + by.offer;
    const responseRate = total ? Math.round((responded / total) * 100) : 0;
    return { by, total, responseRate, offerCount: by.offer };
  }, [apps]);

  const topGaps = useMemo(
    () => [...board.skillGaps].sort((a, b) => b.gap - a.gap).slice(0, 8),
    [board.skillGaps]
  );

  async function handleCreate() {
    if (!form.company.trim() || !form.role.trim()) return;
    setBusy(true);
    try {
      const created = await createApplication({
        ...form,
        appliedAt: form.appliedAt || null,
      });
      setApps((prev) => [created, ...prev]);
      setForm({
        company: "",
        role: "",
        track: "agent",
        source: "",
        status: "applied",
        salaryRange: "",
        appliedAt: null,
        nextAction: "",
      });
      setShowForm(false);
    } catch (e) {
      alert("添加失败：" + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }

  async function handleStatusChange(id: string, status: JobAppStatus) {
    const prev = apps.find((a) => a.id === id);
    if (!prev || prev.status === status) return;
    try {
      const updated = await updateApplication(id, { status });
      setApps((list) => list.map((a) => (a.id === id ? updated : a)));
    } catch (e) {
      alert("更新失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("确认删除该投递记录？")) return;
    try {
      await deleteApplication(id);
      setApps((list) => list.filter((a) => a.id !== id));
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

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
            background:
              "linear-gradient(120deg, var(--color-card), var(--color-card))",
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

        {/* Recommended Job Pool（Batch 1：岗位池推荐直接进求职看板） */}
        {board.jobPool && board.jobPool.total > 0 ? (
          <div style={cardStyle}>
            <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
              <h2 style={sectionTitleStyle}>推荐岗位（来自岗位池）</h2>
              <Link
                href="/jd"
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
                  href="/jd"
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
          <SectionHeader title="本周任务" hint={`${board.tasks.done}/${board.tasks.total} 已完成`} />
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

        {/* Applications */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between" style={{ marginBottom: 14 }}>
            <h2 style={sectionTitleStyle}>投递漏斗与跟进</h2>
            <button
              onClick={() => setShowForm((v) => !v)}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--color-primary)",
                background: showForm ? "var(--color-primary)" : "transparent",
                color: showForm ? "#fff" : "var(--color-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {showForm ? "收起" : "＋ 新增投递"}
            </button>
          </div>

          {/* Funnel stats */}
          <div className="grid" style={{ gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))", marginBottom: 16 }}>
            <FunnelStat label="已投递" value={funnel.by.applied} color="#86868B" />
            <FunnelStat label="筛选中" value={funnel.by.screening} color="#0EA5E9" />
            <FunnelStat label="面试中" value={funnel.by.interview} color="#8B5CF6" />
            <FunnelStat label="已拿offer" value={funnel.by.offer} color="var(--color-emerald)" />
            <FunnelStat label="已挂" value={funnel.by.rejected} color="var(--color-rose)" />
            <FunnelStat label="回复率" value={`${funnel.responseRate}%`} color="var(--color-primary)" />
          </div>

          {/* Add form */}
          {showForm ? (
            <div
              className="flex flex-col"
              style={{
                gap: 10,
                padding: 16,
                marginBottom: 16,
                background: "var(--color-zinc-100)",
                borderRadius: "var(--radius-item-md)",
              }}
            >
              <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
                <input
                  placeholder="公司 *"
                  value={form.company}
                  onChange={(e) => setForm({ ...form, company: e.target.value })}
                  style={inputStyle}
                />
                <input
                  placeholder="岗位 *"
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  style={inputStyle}
                />
                <select
                  value={form.track}
                  onChange={(e) => setForm({ ...form, track: e.target.value })}
                  style={inputStyle}
                >
                  {Object.entries(TRACK_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
                <input
                  placeholder="来源（Boss/内推/猎聘…）"
                  value={form.source ?? ""}
                  onChange={(e) => setForm({ ...form, source: e.target.value })}
                  style={inputStyle}
                />
                <input
                  placeholder="薪资范围 如 36-42K"
                  value={form.salaryRange ?? ""}
                  onChange={(e) => setForm({ ...form, salaryRange: e.target.value })}
                  style={inputStyle}
                />
                <input
                  type="date"
                  value={form.appliedAt ?? ""}
                  onChange={(e) => setForm({ ...form, appliedAt: e.target.value || null })}
                  style={inputStyle}
                />
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value as JobAppStatus })}
                  style={inputStyle}
                >
                  {STATUS_ORDER.map((s) => (
                    <option key={s} value={s}>
                      {APP_STATUS_META[s].label}
                    </option>
                  ))}
                </select>
              </div>
              <input
                placeholder="下一步动作（如 9/12 前发感谢信）"
                value={form.nextAction ?? ""}
                onChange={(e) => setForm({ ...form, nextAction: e.target.value })}
                style={inputStyle}
              />
              <div className="flex" style={{ gap: 10, justifyContent: "flex-end" }}>
                <button
                  onClick={handleCreate}
                  disabled={busy}
                  style={{
                    padding: "8px 20px",
                    borderRadius: "var(--radius-pill)",
                    border: "none",
                    background: "var(--color-primary)",
                    color: "#fff",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: busy ? "not-allowed" : "pointer",
                    opacity: busy ? 0.6 : 1,
                  }}
                >
                  {busy ? "添加中…" : "添加记录"}
                </button>
              </div>
            </div>
          ) : null}

          {/* List */}
          <div className="flex flex-col" style={{ gap: 8 }}>
            {apps.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>暂无投递记录，点击「＋ 新增投递」开始跟踪。</p>
            ) : (
              apps.map((a) => {
                const meta = APP_STATUS_META[a.status];
                return (
                  <div
                    key={a.id}
                    className="flex items-center"
                    style={{
                      gap: 12,
                      padding: "12px 14px",
                      border: "1px solid var(--color-hairline-soft)",
                      borderRadius: "var(--radius-item-md)",
                      flexWrap: "wrap",
                    }}
                  >
                    <div className="flex flex-col" style={{ gap: 2, minWidth: 180, flex: 1 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>
                        {a.company}
                      </span>
                      <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
                        {a.role}
                        {a.salaryRange ? ` · ${a.salaryRange}` : ""}
                      </span>
                    </div>
                    <Pill label={TRACK_LABEL[a.track] || a.track} color="var(--color-ink-48)" soft="var(--color-zinc-100)" />
                    {a.appliedAt ? (
                      <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{a.appliedAt}</span>
                    ) : null}
                    {a.nextAction ? (
                      <span
                        style={{
                          fontSize: 12,
                          color: "var(--color-amber-deep)",
                          flex: "1 1 160px",
                          minWidth: 120,
                        }}
                      >
                        → {a.nextAction}
                      </span>
                    ) : null}
                    <span
                      style={{
                        padding: "3px 10px",
                        borderRadius: "var(--radius-pill)",
                        fontSize: 12,
                        fontWeight: 600,
                        color: meta.color,
                        background: meta.soft,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {meta.label}
                    </span>
                    <select
                      value={a.status}
                      onChange={(e) => handleStatusChange(a.id, e.target.value as JobAppStatus)}
                      style={{ ...inputStyle, width: 110, padding: "4px 8px", fontSize: 12 }}
                    >
                      {STATUS_ORDER.map((s) => (
                        <option key={s} value={s}>
                          {APP_STATUS_META[s].label}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => handleDelete(a.id)}
                      title="删除"
                      style={{
                        border: "none",
                        background: "transparent",
                        color: "var(--color-ink-48)",
                        cursor: "pointer",
                        fontSize: 16,
                        lineHeight: 1,
                        padding: "2px 6px",
                      }}
                    >
                      ×
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <footer style={{ fontSize: 12, color: "var(--color-ink-48)", textAlign: "center", paddingTop: 8 }}>
          Career OS · 求职作战看板 · 数据来自 /api/job-hunt 与 /api/job-applications
        </footer>
      </div>
    </div>
  );
}

/* ───────────────────────── 子组件（同文件内联） ───────────────────────── */

const inputStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderRadius: "var(--radius-item-sm)",
  border: "1px solid var(--color-hairline)",
  background: "var(--color-card)",
  fontSize: 13,
  color: "var(--color-ink)",
  outline: "none",
  minWidth: 140,
};

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
        // 冻结赛道（长期观察）：仍展示匹配度，但视觉降权，避免误当成今日重点
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
