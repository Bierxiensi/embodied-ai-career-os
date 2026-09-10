"use client";

import { useEffect, useState } from "react";
import type {
  FactCategory,
  JobPosting,
  ResumeDiagnosis,
  ResumeFact,
  ResumeVersion,
} from "@/types";
import {
  createFact,
  createVersion,
  deleteFact,
  deleteVersion,
  diagnose,
  listFacts,
  listVersions,
} from "@/services/resumeService";
import { listPostings } from "@/services/jdService";

/* ───────────────────────── 元数据 ───────────────────────── */

const FACT_CATEGORY_META: Record<FactCategory, { label: string; color: string; soft: string }> = {
  work: { label: "工作", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  project: { label: "项目", color: "#0EA5E9", soft: "rgba(14,165,233,0.12)" },
  paper: { label: "论文", color: "#8B5CF6", soft: "rgba(139,92,246,0.12)" },
  edu: { label: "教育", color: "#F59E0B", soft: "rgba(245,158,11,0.12)" },
  metric: { label: "指标/技能", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
};

const TIER_META: Record<number, { label: string; color: string; soft: string }> = {
  1: { label: "主攻", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
  2: { label: "卡位", color: "#8B5CF6", soft: "rgba(139,92,246,0.12)" },
  3: { label: "保底", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
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

const iconBtn: React.CSSProperties = {
  border: "none",
  background: "transparent",
  color: "var(--color-ink-48)",
  cursor: "pointer",
  fontSize: 16,
  lineHeight: 1,
  padding: "2px 6px",
};

const primaryBtn: React.CSSProperties = {
  padding: "8px 20px",
  borderRadius: "var(--radius-pill)",
  border: "none",
  background: "var(--color-primary)",
  color: "#fff",
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
};

/* ───────────────────────── 主组件 ───────────────────────── */

type Props = {
  initialVersions: ResumeVersion[];
  initialFacts: ResumeFact[];
};

export default function ResumeBoard({ initialVersions, initialFacts }: Props) {
  const [versions, setVersions] = useState<ResumeVersion[]>(initialVersions);
  const [facts, setFacts] = useState<ResumeFact[]>(initialFacts);
  const [postings, setPostings] = useState<JobPosting[]>([]);

  const [md, setMd] = useState("");
  const [selectedPostingId, setSelectedPostingId] = useState<string>("");
  const [diagnosis, setDiagnosis] = useState<ResumeDiagnosis | null>(null);
  const [busy, setBusy] = useState(false);

  // 新建版本表单
  const [showVerForm, setShowVerForm] = useState(false);
  const [verForm, setVerForm] = useState({
    name: "",
    targetTier: 1 as 1 | 2 | 3,
    isPrimary: false,
    contentMd: "",
  });

  // 新增事实表单
  const [showFactForm, setShowFactForm] = useState(false);
  const [factForm, setFactForm] = useState({
    category: "work" as FactCategory,
    title: "",
    org: "",
    facts: "",
    source: "",
  });

  // 拉岗位池（供 JD 定向诊断下拉），并默认载入主版本内容
  useEffect(() => {
    listPostings().then(setPostings).catch(() => setPostings([]));
    const primary = initialVersions.find((v) => v.isPrimary) || initialVersions[0];
    if (primary?.contentMd) setMd(primary.contentMd);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshVersions = async () => setVersions(await listVersions());
  const refreshFacts = async () => setFacts(await listFacts());

  async function handleDiagnose() {
    if (!md.trim()) {
      alert("请先粘贴简历内容，或加载一个版本");
      return;
    }
    setBusy(true);
    try {
      const d = await diagnose({
        contentMd: md,
        postingId: selectedPostingId || null,
      });
      setDiagnosis(d);
    } catch (e) {
      alert("诊断失败：" + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateVersion() {
    if (!verForm.name.trim()) return;
    try {
      await createVersion({
        name: verForm.name,
        targetTier: verForm.targetTier,
        isPrimary: verForm.isPrimary,
        contentMd: verForm.contentMd || null,
      });
      alert("已新建简历版本");
      setVerForm({ name: "", targetTier: 1, isPrimary: false, contentMd: "" });
      setShowVerForm(false);
      await refreshVersions();
    } catch (e) {
      alert("新建失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleDeleteVersion(id: string) {
    if (!confirm("确认删除该版本？")) return;
    try {
      await deleteVersion(id);
      await refreshVersions();
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleCreateFact() {
    if (!factForm.title.trim()) return;
    try {
      await createFact({
        category: factForm.category,
        title: factForm.title,
        org: factForm.org || null,
        facts: factForm.facts.split("\n").map((s) => s.trim()).filter(Boolean),
        source: factForm.source || null,
      });
      alert("已新增事实锚点");
      setFactForm({ category: "work", title: "", org: "", facts: "", source: "" });
      setShowFactForm(false);
      await refreshFacts();
    } catch (e) {
      alert("新增失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleDeleteFact(id: string) {
    if (!confirm("确认删除该事实锚点？删除后依赖它的简历 claim 会重新变红")) return;
    try {
      await deleteFact(id);
      await refreshFacts();
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  // 事实按分类分组
  const factsByCat = (Object.keys(FACT_CATEGORY_META) as FactCategory[]).map((cat) => ({
    cat,
    items: facts.filter((f) => f.category === cat),
  })).filter((g) => g.items.length > 0);

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
            RESUME · ANTI-FABRICATION
          </span>
          <h1
            className="font-semibold"
            style={{ fontSize: 40, color: "var(--color-ink)", letterSpacing: "-0.02em" }}
          >
            简历线 · 防虚构诊断
          </h1>
          <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
            每条 claim 必须有事实锚点，否则标红 · 纯规则校验（不依赖 LLM），可解释、不写出假数据
          </p>
        </div>

        {/* 版本 + 事实概览 */}
        <div className="grid" style={{ gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" }}>
          <StatCard label="简历版本" value={versions.length} color="var(--color-ink)" />
          <StatCard label="事实锚点" value={facts.length} color="var(--color-ink)" />
          {diagnosis ? (
            <>
              <StatCard label="claim 总数" value={diagnosis.total} color="var(--color-ink)" />
              <StatCard label="已锚定" value={diagnosis.anchoredCount} color="var(--color-emerald)" />
              <StatCard label="未锚定" value={diagnosis.unanchoredCount} color="var(--color-rose)" />
              <StatCard
                label="虚构风险"
                value={`${diagnosis.fabricationRisk}%`}
                color={diagnosis.fabricationRisk > 0 ? "var(--color-rose-deep)" : "var(--color-emerald)"}
              />
            </>
          ) : null}
        </div>

        {/* 版本列表 + 新建 */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between">
            <h2 style={sectionTitleStyle}>简历版本</h2>
            <button
              onClick={() => setShowVerForm((v) => !v)}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--color-primary)",
                background: showVerForm ? "var(--color-primary)" : "transparent",
                color: showVerForm ? "#fff" : "var(--color-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {showVerForm ? "收起" : "＋ 新建版本"}
            </button>
          </div>

          <div className="flex flex-col" style={{ gap: 8, marginTop: 14 }}>
            {versions.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>暂无版本，点击「＋ 新建版本」创建。</p>
            ) : (
              versions.map((v) => {
                const tier = TIER_META[v.targetTier] ?? TIER_META[2];
                return (
                  <div
                    key={v.id}
                    className="flex items-center"
                    style={{
                      gap: 12,
                      padding: "10px 14px",
                      border: "1px solid var(--color-hairline-soft)",
                      borderRadius: "var(--radius-item-md)",
                      flexWrap: "wrap",
                    }}
                  >
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)", minWidth: 140 }}>
                      {v.name}
                    </span>
                    <Pill label={tier.label} color={tier.color} soft={tier.soft} />
                    {v.isPrimary ? <Pill label="主版本" color="var(--color-emerald)" soft="var(--color-emerald-soft)" /> : null}
                    <div style={{ flex: 1 }} />
                    <button
                      onClick={() => { if (v.contentMd) setMd(v.contentMd); alert("已载入到诊断框"); }}
                      style={{ ...iconBtn, fontSize: 13, color: "var(--color-primary)" }}
                    >
                      载入
                    </button>
                    <button onClick={() => handleDeleteVersion(v.id)} title="删除" style={iconBtn}>×</button>
                  </div>
                );
              })
            )}
          </div>

          {showVerForm ? (
            <div className="flex flex-col" style={{ gap: 10, marginTop: 14 }}>
              <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
                <input
                  placeholder="版本名（如 LLM 主攻版）*"
                  value={verForm.name}
                  onChange={(e) => setVerForm({ ...verForm, name: e.target.value })}
                  style={inputStyle}
                />
                <select
                  value={String(verForm.targetTier)}
                  onChange={(e) => setVerForm({ ...verForm, targetTier: Number(e.target.value) as 1 | 2 | 3 })}
                  style={inputStyle}
                >
                  <option value={1}>梯队 1 · 主攻</option>
                  <option value={2}>梯队 2 · 卡位</option>
                  <option value={3}>梯队 3 · 保底</option>
                </select>
                <label className="flex items-center" style={{ gap: 6, fontSize: 13, color: "var(--color-ink-80)" }}>
                  <input
                    type="checkbox"
                    checked={verForm.isPrimary}
                    onChange={(e) => setVerForm({ ...verForm, isPrimary: e.target.checked })}
                  />
                  设为主版本
                </label>
              </div>
              <textarea
                placeholder="简历 md 原文（bullet 行会被逐条校验）"
                value={verForm.contentMd}
                onChange={(e) => setVerForm({ ...verForm, contentMd: e.target.value })}
                style={{ ...inputStyle, minHeight: 120, resize: "vertical", width: "100%" }}
              />
              <div className="flex" style={{ gap: 10, justifyContent: "flex-end" }}>
                <button onClick={handleCreateVersion} style={primaryBtn}>新建版本</button>
              </div>
            </div>
          ) : null}
        </div>

        {/* 防虚构诊断 */}
        <div style={cardStyle}>
          <h2 style={{ ...sectionTitleStyle, marginBottom: 14 }}>防虚构诊断</h2>
          <textarea
            placeholder="粘贴简历 md（或点击版本「载入」）。bullet 行会被逐条校验是否在事实锚点库有依据。"
            value={md}
            onChange={(e) => setMd(e.target.value)}
            style={{ ...inputStyle, minHeight: 200, resize: "vertical", width: "100%", fontFamily: "var(--font-mono, monospace)", fontSize: 12, lineHeight: 1.6 }}
          />
          <div className="flex items-center" style={{ gap: 10, marginTop: 12, flexWrap: "wrap" }}>
            <select
              value={selectedPostingId}
              onChange={(e) => setSelectedPostingId(e.target.value)}
              style={inputStyle}
            >
              <option value="">（可选）定向某 JD 做技能对齐</option>
              {postings.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.company} · {p.title}
                </option>
              ))}
            </select>
            <button onClick={handleDiagnose} disabled={busy} style={{ ...primaryBtn, opacity: busy ? 0.6 : 1 }}>
              {busy ? "诊断中…" : "运行防虚构诊断"}
            </button>
          </div>

          {diagnosis ? (
            <div className="flex flex-col" style={{ gap: 18, marginTop: 18 }}>
              {/* 已锚定 */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-emerald)", marginBottom: 8 }}>
                  已锚定 · 有依据（{diagnosis.anchoredCount}）
                </div>
                <div className="flex flex-col" style={{ gap: 6 }}>
                  {diagnosis.claims.filter((c) => c.anchored).map((c, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "var(--radius-item-sm)",
                        background: "var(--color-emerald-soft)",
                        fontSize: 13,
                        color: "var(--color-ink)",
                      }}
                    >
                      <span style={{ color: "var(--color-emerald-deep)", marginRight: 6 }}>✓</span>
                      {c.text}
                      <span style={{ color: "var(--color-ink-48)", marginLeft: 8, fontSize: 11 }}>
                        ← {c.anchors[0]?.title}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 未锚定 */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-rose-deep)", marginBottom: 8 }}>
                  未锚定 · 疑似虚构 / 需补事实（{diagnosis.unanchoredCount}）
                </div>
                {diagnosis.unanchoredCount === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
                    全部 claim 均能在事实锚点库找到依据，无虚构风险。
                  </p>
                ) : (
                  <div className="flex flex-col" style={{ gap: 6 }}>
                    {diagnosis.claims.filter((c) => !c.anchored).map((c, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "8px 12px",
                          borderRadius: "var(--radius-item-sm)",
                          background: "rgba(244,63,94,0.10)",
                          fontSize: 13,
                          color: "var(--color-ink)",
                        }}
                      >
                        <span style={{ color: "var(--color-rose-deep)", marginRight: 6 }}>✗</span>
                        {c.text}
                        <div style={{ color: "var(--color-rose-deep)", marginTop: 2, fontSize: 11 }}>
                          {c.reason}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* JD 对齐 */}
              {diagnosis.jdAlignment ? (
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--color-ink)", marginBottom: 8 }}>
                    JD 技能对齐（简历是否有依据）
                  </div>
                  <div className="flex flex-wrap" style={{ gap: 8 }}>
                    {diagnosis.jdAlignment.map((a) => (
                      <span
                        key={a.skill}
                        style={{
                          padding: "4px 10px",
                          borderRadius: "var(--radius-pill)",
                          fontSize: 12,
                          color: a.supported ? "var(--color-emerald-deep)" : "var(--color-rose-deep)",
                          background: a.supported ? "var(--color-emerald-soft)" : "rgba(244,63,94,0.10)",
                        }}
                      >
                        {a.supported ? "✓" : "✗"} {a.skill}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        {/* 事实锚点库 */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between">
            <h2 style={sectionTitleStyle}>事实锚点库（防虚构依据）</h2>
            <button
              onClick={() => setShowFactForm((v) => !v)}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--color-primary)",
                background: showFactForm ? "var(--color-primary)" : "transparent",
                color: showFactForm ? "#fff" : "var(--color-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {showFactForm ? "收起" : "＋ 新增事实"}
            </button>
          </div>

          <div className="flex flex-col" style={{ gap: 16, marginTop: 14 }}>
            {factsByCat.map((g) => {
              const meta = FACT_CATEGORY_META[g.cat];
              return (
                <div key={g.cat}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: meta.color, marginBottom: 6 }}>
                    {meta.label}（{g.items.length}）
                  </div>
                  <div className="flex flex-col" style={{ gap: 6 }}>
                    {g.items.map((f) => (
                      <div
                        key={f.id}
                        style={{
                          padding: "10px 12px",
                          border: "1px solid var(--color-hairline-soft)",
                          borderRadius: "var(--radius-item-sm)",
                        }}
                      >
                        <div className="flex items-center" style={{ gap: 8, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-ink)" }}>{f.title}</span>
                          {f.org ? <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{f.org}</span> : null}
                          {f.source ? <Pill label={f.source} color="var(--color-ink-48)" soft="var(--color-zinc-100)" /> : null}
                          <div style={{ flex: 1 }} />
                          <button onClick={() => handleDeleteFact(f.id)} title="删除" style={iconBtn}>×</button>
                        </div>
                        {f.facts.length > 0 ? (
                          <div className="flex flex-wrap" style={{ gap: 6, marginTop: 6 }}>
                            {f.facts.map((s, i) => (
                              <span
                                key={i}
                                style={{
                                  padding: "2px 8px",
                                  borderRadius: "var(--radius-pill)",
                                  fontSize: 11,
                                  color: "var(--color-ink-80)",
                                  background: "var(--color-zinc-100)",
                                }}
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {showFactForm ? (
            <div className="flex flex-col" style={{ gap: 10, marginTop: 14 }}>
              <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
                <select
                  value={factForm.category}
                  onChange={(e) => setFactForm({ ...factForm, category: e.target.value as FactCategory })}
                  style={inputStyle}
                >
                  {(Object.keys(FACT_CATEGORY_META) as FactCategory[]).map((c) => (
                    <option key={c} value={c}>{FACT_CATEGORY_META[c].label}</option>
                  ))}
                </select>
                <input
                  placeholder="主题 *（如 标书审核 Agent）"
                  value={factForm.title}
                  onChange={(e) => setFactForm({ ...factForm, title: e.target.value })}
                  style={inputStyle}
                />
                <input
                  placeholder="机构 / 来源（可选）"
                  value={factForm.org}
                  onChange={(e) => setFactForm({ ...factForm, org: e.target.value })}
                  style={inputStyle}
                />
                <input
                  placeholder="来源说明（可选）"
                  value={factForm.source}
                  onChange={(e) => setFactForm({ ...factForm, source: e.target.value })}
                  style={inputStyle}
                />
              </div>
              <textarea
                placeholder="可陈述事实，每行一条（如：覆盖率 56%→90%）"
                value={factForm.facts}
                onChange={(e) => setFactForm({ ...factForm, facts: e.target.value })}
                style={{ ...inputStyle, minHeight: 90, resize: "vertical", width: "100%", fontFamily: "var(--font-mono, monospace)", fontSize: 12 }}
              />
              <div className="flex" style={{ gap: 10, justifyContent: "flex-end" }}>
                <button onClick={handleCreateFact} style={primaryBtn}>新增事实</button>
              </div>
            </div>
          ) : null}
        </div>

        <footer style={{ fontSize: 12, color: "var(--color-ink-48)", textAlign: "center", paddingTop: 8 }}>
          Career OS · 简历线 · 数据来自 /api/resume（纯规则防虚构校验，不依赖 LLM）
        </footer>
      </div>
    </div>
  );
}
