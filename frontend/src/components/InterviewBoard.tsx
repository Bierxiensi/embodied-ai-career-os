"use client";

import { useState } from "react";
import type {
  Difficulty,
  InterviewLog,
  InterviewQuestion,
  InterviewStats,
  QuestionCategory,
  TaskDraft,
} from "@/types";
import {
  createLog,
  createQuestion,
  deleteLog,
  deleteQuestion,
  getStats,
  listLogs,
  listQuestions,
  simulate,
  toTasks,
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

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div style={{ height: 6, width: "100%", background: "var(--color-zinc-100)", borderRadius: "var(--radius-pill)", overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${Math.min(100, Math.max(0, pct))}%`, background: color, borderRadius: "var(--radius-pill)" }} />
    </div>
  );
}

/** textarea 文本 → 列表（按行拆分，兼容英文逗号）。 */
function linesToArr(s: string): string[] {
  return s
    .split(/\n|,/)
    .map((x) => x.trim())
    .filter(Boolean);
}

/* ───────────────────────── 主组件 ───────────────────────── */

type Props = {
  initialLogs: InterviewLog[];
  initialQuestions: InterviewQuestion[];
  initialStats: InterviewStats;
};

export default function InterviewBoard({ initialLogs, initialQuestions, initialStats }: Props) {
  const [logs, setLogs] = useState<InterviewLog[]>(initialLogs);
  const [questions, setQuestions] = useState<InterviewQuestion[]>(initialQuestions);
  const [stats, setStats] = useState<InterviewStats>(initialStats);

  const [busy, setBusy] = useState(false);
  const [showLogForm, setShowLogForm] = useState(false);
  const [showQForm, setShowQForm] = useState(false);
  const [filterCat, setFilterCat] = useState<string>("");
  const [expandQ, setExpandQ] = useState<string | null>(null);

  // 模拟抽题
  const [simCat, setSimCat] = useState<string>("");
  const [simDiff, setSimDiff] = useState<string>("");
  const [simLimit, setSimLimit] = useState("5");
  const [picked, setPicked] = useState<InterviewQuestion[]>([]);
  const [pickedOutline, setPickedOutline] = useState<string | null>(null);

  const [logForm, setLogForm] = useState({
    company: "",
    role: "",
    round: "一面",
    interviewedAt: "",
    askedQuestions: "",
    weakQuestions: "",
    jdGaps: "",
    knowledgeGaps: "",
    nextActions: "",
    notes: "",
  });

  const [qForm, setQForm] = useState({
    category: "LLM" as QuestionCategory,
    difficulty: "intermediate" as Difficulty,
    question: "",
    answerOutline: "",
    source: "",
  });

  const refresh = async () => {
    const [ls, qs, st] = await Promise.all([listLogs(), listQuestions(), getStats()]);
    setLogs(ls);
    setQuestions(qs);
    setStats(st);
  };

  async function applyFilter(cat: string) {
    setFilterCat(cat);
    const qs = await listQuestions(cat ? { category: cat } : undefined);
    setQuestions(qs);
  }

  async function handleCreateLog() {
    if (!logForm.company.trim() || !logForm.role.trim()) return;
    setBusy(true);
    try {
      await createLog({
        company: logForm.company,
        role: logForm.role,
        round: logForm.round || null,
        interviewedAt: logForm.interviewedAt || null,
        askedQuestions: linesToArr(logForm.askedQuestions),
        weakQuestions: linesToArr(logForm.weakQuestions),
        jdGaps: linesToArr(logForm.jdGaps),
        knowledgeGaps: linesToArr(logForm.knowledgeGaps),
        nextActions: linesToArr(logForm.nextActions),
        notes: logForm.notes || null,
      });
      alert("已记录面经");
      setLogForm({
        company: "", role: "", round: "一面", interviewedAt: "",
        askedQuestions: "", weakQuestions: "", jdGaps: "",
        knowledgeGaps: "", nextActions: "", notes: "",
      });
      setShowLogForm(false);
      await refresh();
    } catch (e) {
      alert("记录失败：" + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteLog(id: string) {
    if (!confirm("确认删除该面经？")) return;
    try {
      await deleteLog(id);
      await refresh();
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleToTasks(id: string) {
    try {
      const res = await toTasks(id, { limit: 5, duration: 40 });
      const titles = res.created.map((d: TaskDraft) => `· ${d.title}`).join("\n");
      alert(`已回写 ${res.count} 个学习任务：\n${titles}`);
      await refresh();
    } catch (e) {
      alert("回写失败：" + (e instanceof Error ? e.message : String(e)));
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

  async function handleCreateQuestion() {
    if (!qForm.question.trim()) return;
    try {
      await createQuestion({
        category: qForm.category,
        difficulty: qForm.difficulty,
        question: qForm.question,
        answerOutline: qForm.answerOutline || null,
        source: qForm.source || null,
      });
      alert("已新增题目");
      setQForm({ category: "LLM", difficulty: "intermediate", question: "", answerOutline: "", source: "" });
      setShowQForm(false);
      await applyFilter(filterCat);
      await refresh();
    } catch (e) {
      alert("新增失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  async function handleDeleteQuestion(id: string) {
    if (!confirm("确认删除该题目？")) return;
    try {
      await deleteQuestion(id);
      await refresh();
    } catch (e) {
      alert("删除失败：" + (e instanceof Error ? e.message : String(e)));
    }
  }

  const maxWeak = stats.weakTopics.length ? stats.weakTopics[0].count : 1;

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
            INTERVIEW · FEEDBACK LOOP
          </span>
          <h1
            className="font-semibold"
            style={{ fontSize: 40, color: "var(--color-ink)", letterSpacing: "-0.02em" }}
          >
            面试线 · 面经 → 弱项 → 任务
          </h1>
          <p className="text-[17px]" style={{ color: "var(--color-ink-48)" }}>
            记录面经自动聚合弱项 · 一键回写学习任务 · 题库按弱项抽题（纯规则，不依赖 LLM）
          </p>
        </div>

        {/* Stats */}
        <div className="grid" style={{ gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" }}>
          <StatCard label="面经数" value={stats.totalLogs} color="var(--color-ink)" />
          <StatCard label="弱项条目" value={stats.totalWeak} color="var(--color-rose)" />
          <StatCard label="题库规模" value={questions.length} color="var(--color-ink)" />
          <StatCard label="不重复弱项" value={stats.weakTopics.length} color="var(--color-amber)" />
        </div>

        {/* 弱项排行榜 */}
        <div style={cardStyle}>
          <h2 style={{ ...sectionTitleStyle, marginBottom: 14 }}>弱项排行榜（跨面经聚合）</h2>
          {stats.weakTopics.length === 0 ? (
            <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>暂无弱项，去记录一条面经吧。</p>
          ) : (
            <div className="flex flex-col" style={{ gap: 10 }}>
              {stats.weakTopics.map((w) => (
                <div key={w.topic} className="flex items-center" style={{ gap: 12 }}>
                  <span style={{ fontSize: 13, width: 220, color: "var(--color-ink-80)" }}>{w.topic}</span>
                  <div style={{ flex: 1 }}>
                    <Bar pct={(w.count / maxWeak) * 100} color="var(--color-rose)" />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-rose-deep)", width: 28, textAlign: "right" }}>
                    ×{w.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 模拟面试抽题 */}
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

          {picked.length > 0 ? (
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
          ) : null}
        </div>

        {/* 面经记录 */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between">
            <h2 style={sectionTitleStyle}>面经记录</h2>
            <button
              onClick={() => setShowLogForm((v) => !v)}
              style={{
                padding: "6px 14px",
                borderRadius: "var(--radius-pill)",
                border: "1px solid var(--color-primary)",
                background: showLogForm ? "var(--color-primary)" : "transparent",
                color: showLogForm ? "#fff" : "var(--color-primary)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {showLogForm ? "收起" : "＋ 记录面经"}
            </button>
          </div>

          {showLogForm ? (
            <div className="flex flex-col" style={{ gap: 10, marginTop: 14 }}>
              <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
                <input placeholder="公司 *" value={logForm.company} onChange={(e) => setLogForm({ ...logForm, company: e.target.value })} style={inputStyle} />
                <input placeholder="岗位 *" value={logForm.role} onChange={(e) => setLogForm({ ...logForm, role: e.target.value })} style={inputStyle} />
                <select value={logForm.round} onChange={(e) => setLogForm({ ...logForm, round: e.target.value })} style={inputStyle}>
                  {["一面", "二面", "三面", "HR", "技术面", "交叉面", "终面"].map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                <input type="date" value={logForm.interviewedAt} onChange={(e) => setLogForm({ ...logForm, interviewedAt: e.target.value })} style={inputStyle} />
              </div>
              <div className="grid" style={{ gap: 10, gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
                {([
                  ["askedQuestions", "被问到的问题（每行一条）"],
                  ["weakQuestions", "答得不好的问题（弱项，每行一条）"],
                  ["jdGaps", "JD 能力缺口（每行一条）"],
                  ["knowledgeGaps", "知识盲区（每行一条）"],
                  ["nextActions", "下一步行动（每行一条）"],
                ] as const).map(([key, ph]) => (
                  <textarea
                    key={key}
                    placeholder={ph}
                    value={logForm[key]}
                    onChange={(e) => setLogForm({ ...logForm, [key]: e.target.value })}
                    style={{ ...inputStyle, minHeight: 76, resize: "vertical", width: "100%" }}
                  />
                ))}
              </div>
              <textarea
                placeholder="备注 / 复盘"
                value={logForm.notes}
                onChange={(e) => setLogForm({ ...logForm, notes: e.target.value })}
                style={{ ...inputStyle, minHeight: 60, resize: "vertical", width: "100%" }}
              />
              <div className="flex" style={{ gap: 10, justifyContent: "flex-end" }}>
                <button onClick={handleCreateLog} disabled={busy} style={{ ...primaryBtn, opacity: busy ? 0.6 : 1 }}>
                  {busy ? "保存中…" : "保存面经"}
                </button>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col" style={{ gap: 8, marginTop: 14 }}>
            {logs.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>暂无面经。</p>
            ) : (
              logs.map((l) => (
                <div
                  key={l.id}
                  style={{ padding: "12px 14px", border: "1px solid var(--color-hairline-soft)", borderRadius: "var(--radius-item-md)" }}
                >
                  <div className="flex items-center" style={{ gap: 10, flexWrap: "wrap" }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)" }}>{l.company}</span>
                    <span style={{ fontSize: 12, color: "var(--color-ink-48)" }}>{l.role}{l.round ? ` · ${l.round}` : ""}{l.interviewedAt ? ` · ${l.interviewedAt}` : ""}</span>
                    <div style={{ flex: 1 }} />
                    <button onClick={() => handleToTasks(l.id)} style={{ ...iconBtn, fontSize: 13, color: "var(--color-primary)" }}>
                      回写学习任务
                    </button>
                    <button onClick={() => handleDeleteLog(l.id)} title="删除" style={iconBtn}>×</button>
                  </div>
                  {l.weakQuestions.length > 0 ? (
                    <div className="flex flex-wrap" style={{ gap: 6, marginTop: 8 }}>
                      {l.weakQuestions.map((w, i) => (
                        <span key={i} style={{ padding: "2px 8px", borderRadius: "var(--radius-pill)", fontSize: 11, color: "var(--color-rose-deep)", background: "rgba(244,63,94,0.10)" }}>
                          {w}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {l.generatedTaskIds.length > 0 ? (
                    <div style={{ fontSize: 11, color: "var(--color-ink-48)", marginTop: 6 }}>
                      已回写任务 #{l.generatedTaskIds.join(", #")}
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>

        {/* 题库 */}
        <div style={cardStyle}>
          <div className="flex items-center justify-between">
            <h2 style={sectionTitleStyle}>题库</h2>
            <div className="flex items-center" style={{ gap: 10 }}>
              <select value={filterCat} onChange={(e) => applyFilter(e.target.value)} style={inputStyle}>
                <option value="">全部分类</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>{CATEGORY_META[c].label}</option>
                ))}
              </select>
              <button
                onClick={() => setShowQForm((v) => !v)}
                style={{
                  padding: "6px 14px",
                  borderRadius: "var(--radius-pill)",
                  border: "1px solid var(--color-primary)",
                  background: showQForm ? "var(--color-primary)" : "transparent",
                  color: showQForm ? "#fff" : "var(--color-primary)",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {showQForm ? "收起" : "＋ 新增题目"}
              </button>
            </div>
          </div>

          {showQForm ? (
            <div className="flex flex-col" style={{ gap: 10, marginTop: 14 }}>
              <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
                <select value={qForm.category} onChange={(e) => setQForm({ ...qForm, category: e.target.value as QuestionCategory })} style={inputStyle}>
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{CATEGORY_META[c].label}</option>
                  ))}
                </select>
                <select value={qForm.difficulty} onChange={(e) => setQForm({ ...qForm, difficulty: e.target.value as Difficulty })} style={inputStyle}>
                  <option value="beginner">入门</option>
                  <option value="intermediate">进阶</option>
                  <option value="advanced">高阶</option>
                </select>
                <input placeholder="来源（可选）" value={qForm.source} onChange={(e) => setQForm({ ...qForm, source: e.target.value })} style={inputStyle} />
              </div>
              <textarea
                placeholder="题目 *"
                value={qForm.question}
                onChange={(e) => setQForm({ ...qForm, question: e.target.value })}
                style={{ ...inputStyle, minHeight: 60, resize: "vertical", width: "100%" }}
              />
              <textarea
                placeholder="答题要点 / 参考答案大纲"
                value={qForm.answerOutline}
                onChange={(e) => setQForm({ ...qForm, answerOutline: e.target.value })}
                style={{ ...inputStyle, minHeight: 70, resize: "vertical", width: "100%" }}
              />
              <div className="flex" style={{ gap: 10, justifyContent: "flex-end" }}>
                <button onClick={handleCreateQuestion} style={primaryBtn}>新增题目</button>
              </div>
            </div>
          ) : null}

          <div className="flex flex-col" style={{ gap: 8, marginTop: 14 }}>
            {questions.length === 0 ? (
              <p style={{ fontSize: 13, color: "var(--color-ink-48)" }}>题库为空。</p>
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
                      <span style={{ fontSize: 11, color: "var(--color-ink-48)" }}>练过 {q.hitCount}</span>
                      <button onClick={(e) => { e.stopPropagation(); handleDeleteQuestion(q.id); }} title="删除" style={iconBtn}>×</button>
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

        <footer style={{ fontSize: 12, color: "var(--color-ink-48)", textAlign: "center", paddingTop: 8 }}>
          Career OS · 面试线 · 数据来自 /api/interviews（弱项聚合与抽题纯规则，不依赖 LLM）
        </footer>
      </div>
    </div>
  );
}
