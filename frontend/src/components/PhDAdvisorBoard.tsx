"use client";

import { useMemo, useState } from "react";

import {
  DIM_LABELS,
  matchAllAdvisors,
  getPhdAdvisors,
  type PhDAdvisorDTO,
  type ResearchDirectionDTO,
  type PhDMatchDTO,
} from "@/services/phdService";

const GRADE_COLOR: Record<string, string> = {
  A: "#34c759",
  B: "#0a84ff",
  C: "#ff9f0a",
  D: "#ff453a",
};

function gradeColor(grade: string | undefined): string {
  return (grade && GRADE_COLOR[grade]) || "#8e8e93";
}

/** 距离报名截止日的天数（null=常年招生；负=已错过）。 */
function daysToDeadline(deadline: string | null): number | null {
  if (!deadline) return null;
  const today = new Date();
  const d = new Date(deadline);
  return Math.ceil((d.getTime() - today.getTime()) / 86400000);
}

function countdownLabel(deadline: string | null): { text: string; color: string } {
  const days = daysToDeadline(deadline);
  if (days === null) return { text: "常年招生", color: "#8e8e93" };
  if (days < 0) return { text: `已错过 ${Math.abs(days)} 天`, color: "#ff453a" };
  if (days <= 60) return { text: `剩余 ${days} 天`, color: "#ff9f0a" };
  return { text: `剩余 ${days} 天`, color: "#34c759" };
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
      <span className="text-[10px]" style={{ color: "#8e8e93" }}>
        {match.grade} 级
      </span>
    </div>
  );
}

function AdvisorCard({
  a,
  dirMap,
}: {
  a: PhDAdvisorDTO;
  dirMap: Record<string, string>;
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
        border: "1px solid var(--color-ink-12, rgba(0,0,0,0.08))",
        borderRadius: "var(--radius-card-lg, 16px)",
        padding: 18,
        gap: 12,
      }}
    >
      <div className="flex items-start justify-between" style={{ gap: 12 }}>
        <div className="flex flex-col" style={{ gap: 4, minWidth: 0 }}>
          <div className="flex items-center" style={{ gap: 8 }}>
            <span className="text-[15px] font-semibold" style={{ color: "var(--color-ink)" }}>
              {a.name}
            </span>
            {a.recruiting ? (
              <span
                className="text-[10px] font-medium"
                style={{ color: "#34c759", background: "rgba(52,199,89,0.12)", padding: "2px 6px", borderRadius: 6 }}
              >
                在招
              </span>
            ) : (
              <span
                className="text-[10px] font-medium"
                style={{ color: "#8e8e93", background: "rgba(0,0,0,0.06)", padding: "2px 6px", borderRadius: 6 }}
              >
                停招
              </span>
            )}
          </div>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            {[a.institution, a.tier, a.city].filter(Boolean).join(" · ")}
            {a.title ? ` · ${a.title}` : ""}
          </span>
          {a.research_area && (
            <span className="text-xs" style={{ color: "var(--color-ink-64, #636366)" }}>
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
                style={{ flex: 1, height: 6, background: "rgba(0,0,0,0.06)", borderRadius: 3, overflow: "hidden" }}
              >
                <div
                  style={{
                    width: `${dims[k]}%`,
                    height: "100%",
                    background: dims[k] < 60 ? "#ff9f0a" : "var(--color-primary)",
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

      {/* 倒计时 + 缺口 */}
      <div className="flex items-center justify-between" style={{ gap: 8 }}>
        <span className="text-xs font-medium" style={{ color: cd.color }}>
          {cd.text}
        </span>
        {a.in_service_friendly && (
          <span className="text-[10px]" style={{ color: "#0a84ff" }}>
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
            <span key={g.dimension} className="text-[11px]" style={{ color: "#ff9f0a" }}>
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

  const onRematch = async () => {
    setLoading(true);
    try {
      await matchAllAdvisors();
      const fresh = await getPhdAdvisors();
      setAdvisors(fresh);
    } finally {
      setLoading(false);
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
          暂无导师数据。可在后端执行 <code>python scripts/seed_phd.py</code> 灌入初始院校/导师。
        </div>
      ) : (
        <div
          className="grid"
          style={{ gap: 14, gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}
        >
          {sorted.map((a) => (
            <AdvisorCard key={a.id} a={a} dirMap={dirMap} />
          ))}
        </div>
      )}
    </main>
  );
}
