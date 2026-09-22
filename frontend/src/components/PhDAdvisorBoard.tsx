"use client";

import { useMemo, useState } from "react";

import {
  DIM_LABELS,
  matchAllAdvisors,
  getPhdAdvisors,
  patchPhdAdvisor,
  deletePhdAdvisor,
  type PhDAdvisorDTO,
  type ResearchDirectionDTO,
  type PhDMatchDTO,
} from "@/services/phdService";

/* 等级配色：全部走 globals.css token（2026-09-22 清硬编码色值，含暗色变体） */
const GRADE_COLOR: Record<string, string> = {
  A: "var(--color-emerald)",
  B: "var(--color-primary)",
  C: "var(--color-amber)",
  D: "var(--color-rose)",
};

function gradeColor(grade: string | undefined): string {
  return (grade && GRADE_COLOR[grade]) || "var(--color-ink-48)";
}

/** 距离报名截止日的天数（null=常年招生；负=已错过）。 */
function daysToDeadline(deadline: string | null): number | null {
  if (!deadline) return null;
  const today = new Date();
  const d = new Date(deadline);
  return Math.ceil((d.getTime() - today.getTime()) / 86400000);
}

/**
 * 倒计时标签（三态）。
 *
 * 为什么要区分「未录入」与「已过期」：库里现存院校的 deadline 全部落在过去，
 * 若统一显示"已错过 N 天"，用户无法分辨「这所我不去了」和「这所我还没查截止日」——
 * 前者是决策，后者是数据缺失，两者需要不同的下一步动作。
 * 数据缺失必须显式呈现为缺失，不能伪装成一种状态。
 *
 * 「常年招生」不再由"deadline 为空"表达（那是两种不同的事），
 * 需要时请在目标备注里写明。
 */
function countdownLabel(deadline: string | null): { text: string; color: string } {
  const days = daysToDeadline(deadline);
  if (days === null) return { text: "待补录截止日", color: "var(--color-ink-48)" };
  if (days < 0) return { text: `已过期 ${Math.abs(days)} 天 · 待补录新周期`, color: "var(--color-rose)" };
  if (days <= 60) return { text: `剩余 ${days} 天`, color: "var(--color-amber)" };
  return { text: `剩余 ${days} 天`, color: "var(--color-emerald)" };
}

function MatchRing({ match }: { match: PhDMatchDTO }) {
  const color = gradeColor(match.grade);
  return (
    <div
      className="flex flex-col items-center justify-center"
      style={{
        width: 64,
        height: 64,
        borderRadius: "50%",
        border: `3px solid ${color}`,
        flexShrink: 0,
      }}
    >
      <span className="text-lg font-bold" style={{ color }}>
        {match.overall}
      </span>
      <span className="text-[10px]" style={{ color: "var(--color-ink-48)" }}>
        {match.grade} 级
      </span>
    </div>
  );
}

function AdvisorCard({
  a,
  dirMap,
  busy,
  onToggleContacted,
  onDelete,
}: {
  a: PhDAdvisorDTO;
  dirMap: Record<string, string>;
  busy: boolean;
  onToggleContacted: (a: PhDAdvisorDTO) => void;
  onDelete: (a: PhDAdvisorDTO) => void;
}) {
  const cd = countdownLabel(a.application_deadline);
  const match = a.match_json;
  const dims = match?.dimensions;
  const dirName = a.direction_key ? dirMap[a.direction_key] ?? a.direction_key : "";

  return (
    <div
      className="flex flex-col"
      style={{
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg, 16px)",
        padding: 18,
        gap: 12,
      }}
    >
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="flex flex-col" style={{ gap: 4, minWidth: 0 }}>
          <div className="flex items-center" style={{ gap: 8, flexWrap: "wrap" }}>
            <span className="text-[15px] font-semibold" style={{ color: "var(--color-ink)" }}>
              {a.name}
            </span>
            {a.recruiting ? (
              <span
                className="text-[10px] font-medium"
                style={{ color: "var(--color-emerald)", background: "var(--color-emerald-soft)", padding: "2px 6px", borderRadius: 6 }}
              >
                在招
              </span>
            ) : (
              <span
                className="text-[10px] font-medium"
                style={{ color: "var(--color-ink-48)", background: "var(--color-zinc-100)", padding: "2px 6px", borderRadius: 6 }}
              >
                停招
              </span>
            )}
            {a.contacted && (
              <span
                className="text-[10px] font-medium"
                style={{ color: "var(--color-primary)", background: "var(--color-primary-soft)", padding: "2px 6px", borderRadius: 6 }}
              >
                已联系
              </span>
            )}
          </div>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            {[a.institution, a.tier, a.city].filter(Boolean).join(" · ")}
            {a.title ? ` · ${a.title}` : ""}
          </span>
          {a.research_area && (
            <span className="text-xs" style={{ color: "var(--color-ink-32)" }}>
              {a.research_area}
            </span>
          )}
          {a.direction_key && (
            <span className="text-xs" style={{ color: "var(--color-primary)" }}>
              方向：{dirName}
            </span>
          )}
        </div>
        {match ? <MatchRing match={match} /> : null}
      </div>

      {/* 六维条 */}
      {dims && (
        <div className="flex flex-col" style={{ gap: 5 }}>
          {(Object.keys(DIM_LABELS) as (keyof typeof dims)[]).map((k) => (
            <div key={k} className="flex items-center" style={{ gap: 8 }}>
              <span className="text-[10px]" style={{ color: "var(--color-ink-48)", width: 88, flexShrink: 0 }}>
                {DIM_LABELS[k]}
              </span>
              <div
                style={{ flex: 1, height: 6, background: "var(--color-zinc-100)", borderRadius: 3, overflow: "hidden" }}
              >
                <div
                  style={{
                    width: `${dims[k]}%`,
                    height: "100%",
                    background: dims[k] < 60 ? "var(--color-amber)" : "var(--color-primary)",
                    borderRadius: 3,
                  }}
                />
              </div>
              <span className="text-[10px] tabular-nums" style={{ color: "var(--color-ink-48)", width: 22, textAlign: "right" }}>
                {dims[k]}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* 倒计时 + 缺口（wrap：过期文案较长，窄卡片下需换行而非溢出）*/}
      <div className="flex items-center justify-between" style={{ gap: 8, flexWrap: "wrap" }}>
        <span className="text-xs font-medium" style={{ color: cd.color }}>
          {cd.text}
        </span>
        {a.in_service_friendly && (
          <span className="text-[10px]" style={{ color: "var(--color-primary)" }}>
            在职友好
          </span>
        )}
      </div>

      {match && match.gaps.length > 0 && (
        <div className="flex flex-col" style={{ gap: 3 }}>
          <span className="text-[10px]" style={{ color: "var(--color-ink-48)" }}>
            待补强
          </span>
          {match.gaps.map((g) => (
            <span key={g.dimension} className="text-[11px]" style={{ color: "var(--color-amber)" }}>
              · {DIM_LABELS[g.dimension as keyof typeof DIM_LABELS]}：{g.hint}
            </span>
          ))}
        </div>
      )}

      {a.notes && (
        <p className="text-[11px] leading-relaxed" style={{ color: "var(--color-ink-48)" }}>
          {a.notes}
        </p>
      )}

      {/* 操作区：主页 / 联系标记 / 删除 */}
      <div
        className="flex items-center justify-between"
        style={{ gap: 8, borderTop: "1px solid var(--color-hairline-soft)", paddingTop: 10 }}
      >
        <div className="flex items-center" style={{ gap: 10, minWidth: 0 }}>
          {a.homepage && (
            <a
              href={a.homepage}
              target="_blank"
              rel="noreferrer"
              className="text-[11px] no-underline"
              style={{ color: "var(--color-primary)" }}
            >
              主页 ↗
            </a>
          )}
          <span className="text-[10px]" style={{ color: "var(--color-ink-48)" }}>
            {a.contacted
              ? `已联系${a.contact_date ? ` · ${a.contact_date.slice(0, 10)}` : ""}`
              : "未联系"}
          </span>
        </div>
        <div className="flex items-center" style={{ gap: 10, flexShrink: 0 }}>
          <button
            onClick={() => onToggleContacted(a)}
            disabled={busy}
            className="text-[11px] font-medium"
            style={{
              color: "var(--color-primary)",
              background: "transparent",
              border: "none",
              cursor: busy ? "default" : "pointer",
              opacity: busy ? 0.5 : 1,
              padding: 0,
            }}
          >
            {a.contacted ? "取消联系标记" : "标记已联系"}
          </button>
          <button
            onClick={() => onDelete(a)}
            disabled={busy}
            className="text-[11px] font-medium"
            style={{
              color: "var(--color-rose)",
              background: "transparent",
              border: "none",
              cursor: busy ? "default" : "pointer",
              opacity: busy ? 0.5 : 1,
              padding: 0,
            }}
          >
            删除
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PhDAdvisorBoard({
  initialAdvisors,
  directions,
}: {
  initialAdvisors: PhDAdvisorDTO[];
  directions: ResearchDirectionDTO[];
}) {
  const [advisors, setAdvisors] = useState<PhDAdvisorDTO[]>(initialAdvisors);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  /* 录入面板 router.refresh() 后，server 端会带新的 initialAdvisors 下来；
   * useState 初值只在挂载时生效，故在渲染期同步（React 官方 adjust-state-during-render 模式）。 */
  const [prevInitial, setPrevInitial] = useState(initialAdvisors);
  if (prevInitial !== initialAdvisors) {
    setPrevInitial(initialAdvisors);
    setAdvisors(initialAdvisors);
  }

  const dirMap = useMemo(
    () => Object.fromEntries(directions.map((d) => [d.key, d.name])),
    [directions]
  );

  const sorted = useMemo(() => {
    return [...advisors].sort((x, y) => {
      const a = x.match_json?.overall ?? -1;
      const b = y.match_json?.overall ?? -1;
      return b - a;
    });
  }, [advisors]);

  const refreshAdvisors = async () => {
    const fresh = await getPhdAdvisors();
    setAdvisors(fresh);
  };

  const onRematch = async () => {
    setLoading(true);
    try {
      await matchAllAdvisors();
      await refreshAdvisors();
    } finally {
      setLoading(false);
    }
  };

  /** 切换联系状态；首次标记时补写 contact_date（取消标记保留历史日期）。 */
  const onToggleContacted = async (a: PhDAdvisorDTO) => {
    setBusyId(a.id);
    try {
      const contacted = !a.contacted;
      await patchPhdAdvisor(a.id, {
        contacted,
        contact_date:
          contacted && !a.contact_date ? new Date().toISOString() : a.contact_date,
      });
      await refreshAdvisors();
    } finally {
      setBusyId(null);
    }
  };

  const onDelete = async (a: PhDAdvisorDTO) => {
    if (!window.confirm(`确认删除导师「${a.name}」？此操作不可恢复。`)) return;
    setBusyId(a.id);
    try {
      await deletePhdAdvisor(a.id);
      await refreshAdvisors();
    } finally {
      setBusyId(null);
    }
  };

  return (
    <main className="min-h-full" style={{ background: "var(--color-canvas)", padding: "20px 24px" }}>
      <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
        <div>
          <h1 className="text-xl font-bold" style={{ color: "var(--color-ink)" }}>
            博士模块 · 导师匹配看板
          </h1>
          <p className="text-xs" style={{ color: "var(--color-ink-48)", marginTop: 4 }}>
            六维匹配：研究方向契合 · 院校层次 · 地域在职便利 · 成果门槛 · 在职友好 · 时间窗口
          </p>
        </div>
        <button
          onClick={onRematch}
          disabled={loading}
          className="text-xs font-medium no-underline"
          style={{
            padding: "8px 14px",
            borderRadius: 10,
            border: "1px solid var(--color-primary)",
            color: "var(--color-primary)",
            background: "transparent",
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "重算中…" : "重算全部匹配"}
        </button>
      </div>

      {sorted.length === 0 ? (
        <div
          className="text-sm"
          style={{ color: "var(--color-ink-48)", padding: 24, background: "var(--color-card)", borderRadius: 16 }}
        >
          暂无导师数据。用上方「录入」面板添加院校机会与导师，录完后点「重算全部匹配」。
        </div>
      ) : (
        <div
          className="grid"
          style={{ gap: 14, gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}
        >
          {sorted.map((a) => (
            <AdvisorCard
              key={a.id}
              a={a}
              dirMap={dirMap}
              busy={busyId === a.id}
              onToggleContacted={onToggleContacted}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </main>
  );
}
