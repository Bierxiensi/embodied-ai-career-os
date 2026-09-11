"use client";

import { useState } from "react";
import type {
  CoverageSkill,
  Difficulty,
  InterviewQuestion,
  QuestionCategory,
  QuestionCoverage,
} from "@/types";
import {
  createQuestion,
  deleteQuestion,
  getQuestionCoverage,
  listQuestions,
  simulate,
} from "@/services/interviewService";

/* ───────────────────────── 元数据 ───────────────────────── */

const CATEGORY_META: Record<QuestionCategory, { label: string; color: string; soft: string }> = {
  LLM: { label: "LLM", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  Multimodal: { label: "多模态", color: "#8B5CF6", soft: "rgba(139,92,246,0.12)" },
  Project: { label: "项目", color: "#0EA5E9", soft: "rgba(14,165,233,0.12)" },
  Coding: { label: "编码", color: "var(--color-amber)", soft: "var(--color-amber-soft)" },
};

const DIFFICULTY_META: Record<Difficulty, { label: string; color: string; soft: string }> = {
  beginner: { label: "入门", color: "var(--color-emerald)", soft: "var(--color-emerald-soft)" },
  intermediate: { label: "进阶", color: "var(--color-amber)", soft: "var(--color-amber-soft)" },
  advanced: { label: "高阶", color: "var(--color-rose)", soft: "rgba(244,63,94,0.12)" },
};

const CATEGORIES: QuestionCategory[] = ["LLM", "Multimodal", "Project", "Coding"];

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

const iconBtn: React.CSSProperties = {
  border: "none",
  background: "transparent",
  color: "var(--color-ink-48)",
  cursor: "pointer",
  fontSize: 16,
  lineHeight: 1,
  padding: "2px 6px",
};

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

function Bar({ pct, color }: { pct: number; color: string }) {
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

/* ───────────────────────── 覆盖率矩阵 ───────────────────────── */

const RED = "#F43F5E";
const RED_SOFT = "rgba(244,63,94,0.10)";
const GREEN = "#10B981";
const GREEN_SOFT = "rgba(16,185,129,0.12)";

function CoverageMatrix({ coverage }: { coverage: QuestionCoverage }) {
  const cats = coverage.categories.map((c) => c.key);
  const pct = coverage.cellsTotal
    ? Math.round((coverage.cellsFilled / coverage.cellsTotal) * 100)
    : 0;

  return (
    <div style={cardStyle}>
      <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 10 }}>
        <h2 style={sectionTitleStyle}>覆盖率矩阵 · 缺口在哪</h2>
        <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
          格子覆盖率 {coverage.cellsFilled}/{coverage.cellsTotal}（{pct}%）· 红格 = 该技能该分类一题为 0
        </span>
      </div>

      {/* 分类进度 */}
      <div className="grid" style={{ gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", marginTop: 14 }}>
        {coverage.categories.map((c) => (
          <div key={c.key} className="flex flex-col" style={{ gap: 6 }}>
            <div className="flex items-center justify-between">
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-ink)" }}>
                {CATEGORY_META[c.key].label}
                {c.core && (
                  <span style={{ marginLeft: 6, fontSize: 11, color: "var(--color-rose-deep)", fontWeight: 600 }}>
                    核心
                  </span>
                )}
              </span>
              <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
                {c.done}/{c.target}
              </span>
            </div>
            <Bar pct={(c.done / c.target) * 100} color={c.gap === 0 ? GREEN : CATEGORY_META[c.key].color} />
          </div>
        ))}
      </div>

      {/* skill × category 矩阵 */}
      <div style={{ marginTop: 18, overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "6px 10px", color: "var(--color-ink-48)", fontWeight: 600 }}>
                技能 \ 分类
              </th>
              {cats.map((c) => (
                <th key={c} style={{ padding: "6px 10px", color: "var(--color-ink-48)", fontWeight: 600 }}>
                  {CATEGORY_META[c].label}
                </th>
              ))}
              <th style={{ padding: "6px 10px", color: "var(--color-ink-48)", fontWeight: 600 }}>合计</th>
            </tr>
          </thead>
          <tbody>
            {coverage.skills.map((s: CoverageSkill) => (
              <tr key={s.name}>
                <td
                  style={{
                    padding: "7px 10px",
                    color: "var(--color-ink)",
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  {s.name}
                </td>
                {cats.map((c) => {
                  const n = s.counts[c] ?? 0;
                  return (
                    <td key={c} style={{ padding: 4, textAlign: "center" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          minWidth: 30,
                          height: 24,
                          padding: "0 8px",
                          borderRadius: "var(--radius-item-sm)",
                          fontVariantNumeric: "tabular-nums",
                          fontWeight: 600,
                          color: n === 0 ? RED : GREEN,
                          background: n === 0 ? RED_SOFT : GREEN_SOFT,
                        }}
                      >
                        {n}
                      </span>
                    </td>
                  );
                })}
                <td style={{ padding: "7px 10px", textAlign: "center", color: "var(--color-ink-80)", fontWeight: 600 }}>
                  {s.total}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p style={{ fontSize: 12, color: "var(--color-ink-48)", marginTop: 10, lineHeight: 1.7 }}>
        累计目标 {coverage.targetTotal} 题（核心必达 {coverage.coreTarget}：LLM + 多模态），
        当前 {coverage.total} 题 / 核心 {coverage.coreDone} 题。每格目标 ≥1，一行齐 4 格才算该技能"讲得全"。
      </p>
    </div>
  );
}

/* ───────────────────────── 主组件 ───────────────────────── */

type Props = {
  initialQuestions: InterviewQuestion[];
  initialCoverage: QuestionCoverage;
};

export default function QuestionBoard({ initialQuestions, initialCoverage }: Props) {
  const [questions, setQuestions] = useState<InterviewQuestion[]>(initialQuestions);
  const [coverage, setCoverage] = useState<QuestionCoverage>(initialCoverage);
  const [busy, setBusy] = useState(false);
  const [filterCat, setFilterCat] = useState<string>("");
  const [expandQ, setExpandQ] = useState<string | null>(null);

  // 快速录题
  const [quickText, setQuickText] = useState("");
  const [quickCat, setQuickCat] = useState<QuestionCategory>("LLM");
  const [quickSkill, setQuickSkill] = useState<string>("");
  const [quickOutline, setQuickOutline] = useState("");
  const [showOutline, setShowOutline] = useState(false);

  // 抽题
  const [simCat, setSimCat] = useState<string>("");
  const [simDiff, setSimDiff] = useState<string>("");
  const [simLimit, setSimLimit] = useState("5");
  const [picked, setPicked] = useState<InterviewQuestion[]>([]);
  const [pickedOutline, setPickedOutline] = useState<string | null>(null);

  const skillOptions = coverage.skills.map((s) => s.name);

  async function refresh(cat = filterCat) {
    const [qs, cov] = await Promise.all([
      listQuestions(cat ? { category: cat } : undefined),
      getQuestionCoverage(),
    ]);
    setQuestions(qs);
    setCoverage(cov);
  }

  async function applyFilter(cat: string) {
    setFilterCat(cat);
    const qs = await listQuestions(cat ? { category: cat } : undefined);
    setQuestions(qs);
  }

  /** 快速录题：单框输入，按行拆分（可粘贴多行一次录多道），Enter 提交。 */
  async function handleQuickAdd() {
    const lines = quickText
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    if (lines.length === 0) return;
    setBusy(true);
    try {
      for (const q of lines) {
        await createQuestion({
          category: quickCat,
          difficulty: "intermediate",
          question: q,
          answerOutline: quickOutline || null,
          skillName: quickSkill || null,
        });
      }
      setQuickText("");
      setQuickOutline("");
      setShowOutline(false);
      await refresh();
    } catch (e) {
      alert("录入失败：" + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("确认删除该题目？")) return;
    try {
      await deleteQuestion(id);
      await refresh();
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleSimulate() {
    try {
      const res = await simulate({
        category: simCat || null,
        difficulty: simDiff || null,
        limit: Number(simLimit) || 5,
      });
      setPicked(res.picked);
      setPickedOutline(null);
      await refresh();
    } catch (e) {
      alert("抽题失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  return (
    <div className="flex flex-col" style={{ gap: 20 }}>
      {/* 快速录题 */}
      <div style={cardStyle}>
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 10 }}>
          <h2 style={sectionTitleStyle}>快速录题 · ≤ 1 分钟</h2>
          <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>
            Enter 录入 · Shift+Enter 换行 · 可粘贴多行一次录多道
          </span>
        </div>
        <div className="flex" style={{ gap: 10, marginTop: 12, flexWrap: "wrap", alignItems: "flex-start" }}>
          <textarea
            value={quickText}
            onChange={(e) => setQuickText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleQuickAdd();
              }
            }}
            placeholder="一道面试题…（今天被问到的 / 想练的）"
            rows={1}
            style={{ ...inputStyle, flex: 1, minWidth: 260, minHeight: 38, resize: "vertical" }}
          />
          <select
            value={quickCat}
            onChange={(e) => setQuickCat(e.target.value as QuestionCategory)}
            style={inputStyle}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{CATEGORY_META[c].label}</option>
            ))}
          </select>
          <select value={quickSkill} onChange={(e) => setQuickSkill(e.target.value)} style={inputStyle}>
            <option value="">关联技能（可选）</option>
            {skillOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button onClick={handleQuickAdd} disabled={busy} style={{ ...primaryBtn, opacity: busy ? 0.6 : 1 }}>
            {busy ? "录入中…" : "录入"}
          </button>
        </div>
        <button
          onClick={() => setShowOutline((v) => !v)}
          style={{ ...iconBtn, fontSize: 12, color: "var(--color-primary)", marginTop: 6 }}
        >
          {showOutline ? "− 收起答题要点" : "＋ 加答题要点（可选）"}
        </button>
        {showOutline && (
          <textarea
            value={quickOutline}
            onChange={(e) => setQuickOutline(e.target.value)}
            placeholder="答题要点 / 参考答案大纲（本批录入共用）"
            style={{ ...inputStyle, minHeight: 64, resize: "vertical", width: "100%", marginTop: 6 }}
          />
        )}
      </div>

      {/* 覆盖率矩阵 */}
      <CoverageMatrix coverage={coverage} />

      {/* 抽题 */}
      <div style={cardStyle}>
        <h2 style={{ ...sectionTitleStyle, marginBottom: 14 }}>模拟面试 · 抽题</h2>
        <div className="flex items-center" style={{ gap: 10, flexWrap: "wrap" }}>
          <select value={simCat} onChange={(e) => setSimCat(e.target.value)} style={inputStyle}>
            <option value="">全部分类</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{CATEGORY_META[c].label}</option>
            ))}
          </select>
          <select value={simDiff} onChange={(e) => setSimDiff(e.target.value)} style={inputStyle}>
            <option value="">全部难度</option>
            <option value="beginner">入门</option>
            <option value="intermediate">进阶</option>
            <option value="advanced">高阶</option>
          </select>
          <input
            value={simLimit}
            onChange={(e) => setSimLimit(e.target.value)}
            style={{ ...inputStyle, width: 90 }}
            placeholder="题数"
          />
          <button onClick={handleSimulate} style={primaryBtn}>抽 {simLimit} 题</button>
        </div>

        {picked.length > 0 && (
          <div className="flex flex-col" style={{ gap: 8, marginTop: 14 }}>
            {picked.map((q) => {
              const cat = CATEGORY_META[q.category];
              const dif = DIFFICULTY_META[q.difficulty];
              return (
                <div
                  key={q.id}
                  style={{ padding: "10px 12px", border: "1px solid var(--color-hairline-soft)", borderRadius: "var(--radius-item-md)" }}
                >
                  <div className="flex items-center" style={{ gap: 8, flexWrap: "wrap" }}>
                    <Pill label={cat.label} color={cat.color} soft={cat.soft} />
                    <Pill label={dif.label} color={dif.color} soft={dif.soft} />
                    <span style={{ fontSize: 13, color: "var(--color-ink)", flex: 1, minWidth: 200 }}>{q.question}</span>
                    <button
                      onClick={() => setPickedOutline(pickedOutline === q.id ? null : q.id)}
                      style={{ ...iconBtn, fontSize: 13, color: "var(--color-primary)" }}
                    >
                      {pickedOutline === q.id ? "隐藏要点" : "看要点"}
                    </button>
                  </div>
                  {pickedOutline === q.id && q.answerOutline ? (
                    <div style={{ marginTop: 8, fontSize: 12, lineHeight: 1.6, color: "var(--color-ink-80)", background: "var(--color-zinc-100)", padding: "8px 10px", borderRadius: "var(--radius-item-sm)" }}>
                      {q.answerOutline}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 题库 */}
      <div style={cardStyle}>
        <div className="flex items-center justify-between" style={{ flexWrap: "wrap", gap: 10 }}>
          <h2 style={sectionTitleStyle}>题库（{questions.length}）</h2>
          <select value={filterCat} onChange={(e) => applyFilter(e.target.value)} style={inputStyle}>
            <option value="">全部分类</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{CATEGORY_META[c].label}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col" style={{ gap: 8, marginTop: 14 }}>
          {questions.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>
              题库为空。上面输入框敲一道题开始攒（每天 5 题，30 天 150）。
            </p>
          ) : (
            questions.map((q) => {
              const cat = CATEGORY_META[q.category];
              const dif = DIFFICULTY_META[q.difficulty];
              const expanded = expandQ === q.id;
              return (
                <div key={q.id} style={{ border: "1px solid var(--color-hairline-soft)", borderRadius: "var(--radius-item-md)", overflow: "hidden" }}>
                  <div
                    className="flex items-center"
                    style={{ gap: 10, padding: "10px 12px", flexWrap: "wrap", cursor: "pointer" }}
                    onClick={() => setExpandQ(expanded ? null : q.id)}
                  >
                    <Pill label={cat.label} color={cat.color} soft={cat.soft} />
                    <Pill label={dif.label} color={dif.color} soft={dif.soft} />
                    <span style={{ fontSize: 13, color: "var(--color-ink)", flex: 1, minWidth: 200 }}>{q.question}</span>
                    {q.skillName && (
                      <span style={{ fontSize: 11, color: "var(--color-ink-48)" }}>{q.skillName}</span>
                    )}
                    {q.sourceDaySeq != null && (
                      <span style={{ fontSize: 11, color: "var(--color-ink-48)" }}>Day {q.sourceDaySeq}</span>
                    )}
                    <span style={{ fontSize: 11, color: "var(--color-ink-48)" }}>练过 {q.hitCount}</span>
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(q.id); }} title="删除" style={iconBtn}>×</button>
                  </div>
                  {expanded && q.answerOutline ? (
                    <div style={{ padding: "10px 12px", background: "var(--color-zinc-100)", borderTop: "1px solid var(--color-hairline-soft)", fontSize: 12, lineHeight: 1.6, color: "var(--color-ink-80)" }}>
                      {q.answerOutline}
                    </div>
                  ) : null}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
