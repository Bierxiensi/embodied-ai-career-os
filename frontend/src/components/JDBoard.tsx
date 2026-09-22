"use client";

import { useState } from "react";
import type {
  DimensionScores,
  JobPosting,
  JobPoolStats,
  MatchGrade,
  PostingTier,
} from "@/types";
import {
  createPosting,
  deletePosting,
  getPoolStats,
  listPostings,
  recomputeMatch,
} from "@/services/jdService";

/* ───────────────────────── 元数据 ───────────────────────── */

const GRADE_META: Record<MatchGrade, { label: string; color: string; soft: string }> = {
  A: { label: "A · 强匹配", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  B: { label: "B · 正常投", color: "var(--color-sky)", soft: "var(--color-sky-soft)" },
  C: { label: "C · 练手", color: "var(--color-amber)", soft: "var(--color-amber-soft)" },
  D: { label: "D · 不推荐", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
};

const TIER_META: Record<number, { label: string; color: string; soft: string }> = {
  1: { label: "主攻", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
  2: { label: "卡位", color: "var(--color-violet)", soft: "var(--color-violet-soft)" },
  3: { label: "保底", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
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

const GRADE_ORDER: MatchGrade[] = ["A", "B", "C", "D"];

const DIMENSION_META: Array<{ key: keyof DimensionScores; label: string; weight: string }> = [
  { key: "tech_stack", label: "技术栈", weight: "40%" },
  { key: "project", label: "项目经验", weight: "25%" },
  { key: "edu_exp", label: "学历 / 年限", weight: "15%" },
  { key: "research", label: "科研 / 论文", weight: "10%" },
  { key: "industry", label: "行业匹配", weight: "10%" },
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

/* ───────────────────────── 小组件 ───────────────────────── */

function Pill({ label, color, soft }: { label: string; color: string; soft: string }) {
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

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
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
        minWidth: 96,
      }}
    >
      <span style={{ fontSize: 22, fontWeight: 700, color }}>{value}</span>
      <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{label}</span>
    </div>
  );
}

/* ───────────────────────── 主组件 ───────────────────────── */

type Props = {
  initialPostings: JobPosting[];
  initialStats: JobPoolStats;
};

export default function JDBoard({ initialPostings, initialStats }: Props) {
  const [postings, setPostings] = useState<JobPosting[]>(initialPostings);
  const [stats, setStats] = useState<JobPoolStats>(initialStats);
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [expandId, setExpandId] = useState<string | null>(null);

  const [form, setForm] = useState({
    company: "",
    title: "",
    track: "llm",
    tier: 1 as PostingTier,
    city: "",
    salaryRange: "",
    source: "",
    education: "",
    minYears: "",
    paperRequired: false,
    jdText: "",
  });

  const refresh = async () => {
    const [ps, st] = await Promise.all([listPostings(), getPoolStats()]);
    setPostings(ps);
    setStats(st);
  };

  async function handleCreate() {
    if (!form.company.trim() || !form.title.trim()) return;
    setBusy(true);
    try {
      const res = await createPosting({
        company: form.company,
        title: form.title,
        track: form.track,
        tier: form.tier,
        city: form.city || null,
        salaryRange: form.salaryRange || null,
        source: form.source || null,
        education: form.education || null,
        minYears: form.minYears ? Number(form.minYears) : null,
        paperRequired: form.paperRequired,
        jdText: form.jdText || null,
      });
      let msg = `已录入 ${res.count} 条岗位`;
      if (res.skipped.length) msg += `，跳过重复 ${res.skipped.length} 条`;
      alert(msg);
      setForm({
        company: "", title: "", track: "llm", tier: 1, city: "", salaryRange: "",
        source: "", education: "", minYears: "", paperRequired: false, jdText: "",
      });
      setShowForm(false);
      await refresh();
    } catch (e) {
      alert("录入失败：" + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }

  async function handleRematch(id: string) {
    try {
      await recomputeMatch(id);
      await refresh();
    } catch (e) {
      alert("重算失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("确认删除该岗位？")) return;
    try {
      await deletePosting(id);
      await refresh();
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  return (
    <div className="flex flex-1 flex-col">
      <div
        className="flex flex-col"
        style={{ gap: "var(--spacing-lg)", padding: "36px clamp(20px, 8vw, 120px) 48px" }}
      >
        {/* Header */}
        <div className="flex flex-col" style={{ gap: 8 }}>
          <span
            className="text-xs font-semibold uppercase"
            style={{ color: "var(--color-ink-48)", letterSpacing: "0.04em" }}
          >
            JOB POOL · JD MATCH
          </span>
          <h1
            className="font-semibold"
            style={{ fontSize: 40, color: "var(--color-ink)", letterSpacing: "-0.02em" }}
          >
            岗位池 · JD 匹配
          </h1>
          <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
            录 JD 即得 A/B/C/D 评级与差距 · 纯规则评分（技术栈40 / 项目25 / 学历年限15 / 科研10 / 行业10），可解释不盲投
          </p>
        </div>

        {/* Stats */}
        <div style={cardStyle}>
          <h2 style={sectionTitleStyle} className="flex items-center" >
            岗位池概览
          </h2>
          <div className="grid" style={{ gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(96px, 1fr))", marginTop: 14 }}>
            <StatCard label="岗位总数" value={stats.total} color="var(--color-ink)" />
            <StatCard label="可优先投 (A+B)" value={stats.recommended} color="var(--color-emerald)" />
            <StatCard label="未匹配" value={stats.unmatched} color="var(--color-ink-48)" />
            {GRADE_ORDER.map((g) => (
              <StatCard
                key={g}
                label={`等级 ${g}`}
                value={stats.byGrade[g] ?? 0}
                color={GRADE_META[g].color}
              />
            ))}
          </div>
        </div>

        {/* Entry form toggle */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between">
            <h2 style={sectionTitleStyle}>录入 JD</h2>
            <button
              onClick={() => setShowForm((v) => !v)}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--color-primary)",
                background: showForm ? "var(--color-primary)" : "transparent",
                color: showForm ? "var(--color-on-primary)" : "var(--color-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {showForm ? "收起" : "＋ 新增 JD"}
            </button>
          </div>

          {showForm ? (
            <div className="flex flex-col" style={{ gap: 10, marginTop: 14 }}>
              <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
                <input
                  placeholder="公司 *"
                  value={form.company}
                  onChange={(e) => setForm({ ...form, company: e.target.value })}
                  style={inputStyle}
                />
                <input
                  placeholder="岗位名 *"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  style={inputStyle}
                />
                <select
                  value={form.track}
                  onChange={(e) => setForm({ ...form, track: e.target.value })}
                  style={inputStyle}
                >
                  {Object.entries(TRACK_LABEL).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
                <select
                  value={String(form.tier)}
                  onChange={(e) => setForm({ ...form, tier: Number(e.target.value) as PostingTier })}
                  style={inputStyle}
                >
                  <option value={1}>梯队 1 · 主攻</option>
                  <option value={2}>梯队 2 · 卡位</option>
                  <option value={3}>梯队 3 · 保底</option>
                </select>
                <input
                  placeholder="城市"
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                  style={inputStyle}
                />
                <input
                  placeholder="薪资 如 36-45K"
                  value={form.salaryRange}
                  onChange={(e) => setForm({ ...form, salaryRange: e.target.value })}
                  style={inputStyle}
                />
                <input
                  placeholder="来源 Boss/内推/猎聘"
                  value={form.source}
                  onChange={(e) => setForm({ ...form, source: e.target.value })}
                  style={inputStyle}
                />
                <select
                  value={form.education}
                  onChange={(e) => setForm({ ...form, education: e.target.value })}
                  style={inputStyle}
                >
                  <option value="">学历要求（不限）</option>
                  <option value="本科">本科</option>
                  <option value="硕士">硕士</option>
                  <option value="博士">博士</option>
                </select>
                <input
                  placeholder="经验年数 如 3"
                  value={form.minYears}
                  onChange={(e) => setForm({ ...form, minYears: e.target.value })}
                  style={{ ...inputStyle, width: 120 }}
                />
                <label className="flex items-center" style={{ gap: 6, fontSize: 13, color: "var(--color-ink-80)" }}>
                  <input
                    type="checkbox"
                    checked={form.paperRequired}
                    onChange={(e) => setForm({ ...form, paperRequired: e.target.checked })}
                  />
                  要求论文
                </label>
              </div>
              <textarea
                placeholder="粘贴 JD 全文（系统自动抽取技能关键词并计算匹配；留空则技术栈维度记 0）"
                value={form.jdText}
                onChange={(e) => setForm({ ...form, jdText: e.target.value })}
                style={{ ...inputStyle, minHeight: 120, resize: "vertical", width: "100%" }}
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
                    color: "var(--color-on-primary)",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: busy ? "not-allowed" : "pointer",
                    opacity: busy ? 0.6 : 1,
                  }}
                >
                  {busy ? "匹配中…" : "录入并匹配"}
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {/* List */}
        <div style={cardStyle}>
          <h2 style={{ ...sectionTitleStyle, marginBottom: 14 }}>岗位列表（按匹配分降序）</h2>
          {postings.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
              岗位池为空，点击「＋ 新增 JD」录入第一条。
            </p>
          ) : (
            <div className="flex flex-col" style={{ gap: 8 }}>
              {postings.map((p) => {
                const grade = p.grade ? GRADE_META[p.grade] : null;
                const tier = TIER_META[p.tier] ?? TIER_META[2];
                const matchColor = grade ? grade.color : "var(--color-ink-48)";
                const expanded = expandId === p.id;
                return (
                  <div
                    key={p.id}
                    style={{
                      border: "1px solid var(--color-hairline-soft)",
                      borderRadius: "var(--radius-item-md)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      className="flex items-center"
                      style={{ gap: 12, padding: "12px 14px", flexWrap: "wrap", cursor: "pointer" }}
                      onClick={() => setExpandId(expanded ? null : p.id)}
                    >
                      <div className="flex flex-col" style={{ gap: 2, minWidth: 180, flex: 1 }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>
                          {p.company}
                        </span>
                        <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
                          {p.title}
                          {p.salaryRange ? ` · ${p.salaryRange}` : ""}
                        </span>
                      </div>
                      <Pill label={TRACK_LABEL[p.track] || p.track} color="var(--color-ink-48)" soft="var(--color-zinc-100)" />
                      <Pill label={tier.label} color={tier.color} soft={tier.soft} />
                      {p.matchScore != null ? (
                        <div className="flex items-center" style={{ gap: 10, minWidth: 150 }}>
                          <span style={{ fontSize: 20, fontWeight: 700, color: matchColor, letterSpacing: "-0.02em" }}>
                            {p.matchScore}
                          </span>
                          <div style={{ flex: 1, minWidth: 70 }}>
                            <MatchBar pct={p.matchScore} color={matchColor} />
                          </div>
                          {grade ? <Pill label={grade.label} color={grade.color} soft={grade.soft} /> : null}
                        </div>
                      ) : (
                        <Pill label="未匹配" color="var(--color-ink-48)" soft="var(--color-zinc-100)" />
                      )}
                      <div className="flex items-center" style={{ gap: 6 }}>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleRematch(p.id); }}
                          title="重算匹配"
                          style={iconBtn}
                        >
                          ↻
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDelete(p.id); }}
                          title="删除"
                          style={iconBtn}
                        >
                          ×
                        </button>
                      </div>
                    </div>

                    {/* Detail */}
                    {expanded ? (
                      <div
                        style={{
                          padding: "14px 16px",
                          background: "var(--color-zinc-100)",
                          borderTop: "1px solid var(--color-hairline-soft)",
                        }}
                      >
                        <MatchDetail posting={p} />
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <footer style={{ fontSize: 12, color: "var(--color-ink-48)", textAlign: "center", paddingTop: 8 }}>
          Career OS · 岗位池 · 数据来自 /api/job-postings（纯规则匹配，不依赖 LLM）
        </footer>
      </div>
    </div>
  );
}

/* ───────────────────────── 匹配详情 ───────────────────────── */

const iconBtn: React.CSSProperties = {
  border: "none",
  background: "transparent",
  color: "var(--color-ink-48)",
  cursor: "pointer",
  fontSize: 16,
  lineHeight: 1,
  padding: "2px 6px",
};

function MatchDetail({ posting }: { posting: JobPosting }) {
  const dims = posting.dimensionScores;
  return (
    <div className="flex flex-col" style={{ gap: 16 }}>
      {/* 维度分 */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-ink)", marginBottom: 10 }}>
          匹配维度（v2.0 §22 权重）
        </div>
        <div className="flex flex-col" style={{ gap: 10 }}>
          {DIMENSION_META.map((d) => {
            const v = dims ? dims[d.key] : 0;
            const color = v >= 80 ? "var(--color-emerald)" : v >= 50 ? "var(--color-amber)" : "var(--color-rose)";
            return (
              <div key={d.key} className="flex items-center" style={{ gap: 12 }}>
                <span style={{ fontSize: 13, width: 96, color: "var(--color-ink-80)" }}>{d.label}</span>
                <span style={{ fontSize: 11, color: "var(--color-ink-48)", width: 36 }}>{d.weight}</span>
                <div style={{ flex: 1 }}>
                  <MatchBar pct={v} color={color} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 600, color, width: 30, textAlign: "right" }}>{v}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 差距 */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-ink)", marginBottom: 8 }}>
          能力差距（按缺口降序）
        </div>
        {posting.gaps && posting.gaps.length > 0 ? (
          <div className="flex flex-wrap" style={{ gap: 8 }}>
            {posting.gaps.map((g) => (
              <span
                key={g.skill}
                style={{
                  padding: "4px 10px",
                  borderRadius: "var(--radius-pill)",
                  fontSize: 12,
                  color: "var(--color-rose-deep)",
                  background: "rgba(244,63,94,0.10)",
                }}
              >
                {g.skill} · {g.level}/{g.required}（差 {g.gap}）
              </span>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
            无显著技能缺口（JD 要求的技能均已达标）。
          </p>
        )}
      </div>

      {/* JD 原文 */}
      {posting.jdText ? (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-ink)", marginBottom: 6 }}>
            JD 原文
          </div>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              fontSize: 12,
              lineHeight: 1.6,
              color: "var(--color-ink-80)",
              margin: 0,
              maxHeight: 240,
              overflow: "auto",
            }}
          >
            {posting.jdText}
          </pre>
        </div>
      ) : null}

      {posting.requiredSkills && posting.requiredSkills.length > 0 ? (
        <div className="flex flex-wrap" style={{ gap: 6 }}>
          {posting.requiredSkills.map((s) => (
            <span
              key={s}
              style={{
                padding: "2px 8px",
                borderRadius: "var(--radius-pill)",
                fontSize: 11,
                color: "var(--color-ink-48)",
                background: "var(--color-card)",
                border: "1px solid var(--color-hairline)",
              }}
            >
              {s}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
