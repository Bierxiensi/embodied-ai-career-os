import { COUNTDOWN_COLOR, COUNTDOWN_LABEL, daysText } from "@/lib/countdown";
import type { CareerMode, CareerProgress, TrackProgress } from "@/types";

type Props = {
  /** 职业进度区（来自 /api/transition/dashboard）。 */
  progress: CareerProgress;
  /** 当前职业阶段（阶段名 + 阶段剩余天数）。 */
  mode: CareerMode;
  /** 数据基准日（服务端日期），显示"截至 X"。 */
  asOf: string;
};

/** 一条赛道的双轨指标（推进度 + 严格达标率）。
 *
 * 双轨并列是 v3.2 裁决②的硬要求：67% 的推进度极易被读成"已达标"，
 * 而真实硬性达标只有 23%。任一轨道单独出现都会被误读。
 */
function TrackMetrics({ track, emphasis }: { track: TrackProgress; emphasis: boolean }) {
  return (
    <div className="flex flex-col" style={{ gap: 6 }}>
      <div className="flex items-baseline justify-between" style={{ gap: 10 }}>
        <div className="flex items-center" style={{ gap: 8, minWidth: 0 }}>
          <span
            className={emphasis ? "text-[15px] font-semibold" : "text-[13px] font-medium"}
            style={{ color: emphasis ? "var(--text-primary)" : "var(--text-secondary)" }}
          >
            {track.name}
          </span>
          <span
            className="text-[11px] shrink-0"
            style={{
              color: "var(--text-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-pill)",
              padding: "1px 8px",
            }}
          >
            {track.priority}
          </span>
          {track.frozen ? (
            <span
              className="text-[11px] shrink-0"
              style={{
                color: "var(--text-muted)",
                background: "var(--color-zinc-100)",
                borderRadius: "var(--radius-pill)",
                padding: "1px 8px",
              }}
            >
              冻结
            </span>
          ) : null}
        </div>
        <div className="flex items-baseline shrink-0" style={{ gap: 10 }}>
          <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {track.matchPct}%
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            达标 {track.strictPct}%（{track.qualifiedCount}/{track.requiredCount}）
          </span>
        </div>
      </div>

      <div
        className="overflow-hidden"
        style={{ height: emphasis ? 6 : 4, background: "var(--color-zinc-100)", borderRadius: "var(--radius-pill)" }}
      >
        <div
          className="h-full"
          style={{
            width: `${track.matchPct}%`,
            background: emphasis ? "var(--accent-primary)" : "var(--text-muted)",
            borderRadius: "var(--radius-pill)",
          }}
        />
      </div>

      <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
        {track.skillCount} 项硬性要求技能，仍有 {track.gapCount} 项未达标
      </span>
    </div>
  );
}

/** 第 1 区：职业进度 —— 当前阶段 + 各赛道双轨就绪度 + 关键节点倒计时。
 *
 * 只做**摘要**：逐项技能的对齐情况在 SkillRadarCard（本区右侧）与 /jobs 页，
 * 这里不重复展开，避免同一份数据在三处各画一遍。
 *
 * 数字全部来自后端 `services/readiness`（与 /jobs 页逐字同源），
 * 前端不重算 —— 见 services/transitionService.ts 的口径纪律。
 */
export default function CareerProgressCard({ progress, mode, asOf }: Props) {
  const tracks = progress.tracks;
  const primary =
    tracks.find((t) => t.key === progress.primaryTrackKey) ?? tracks[0] ?? null;
  const others = tracks.filter((t) => t !== primary);

  return (
    <div
      className="flex flex-col"
      style={{
        flex: "1 1 420px",
        maxWidth: 690,
        minWidth: 0,
        gap: "var(--spacing-md)",
        padding: "var(--spacing-lg)",
        background: "var(--surface-card)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <div className="flex flex-col" style={{ gap: 4 }}>
        <div className="flex items-center justify-between" style={{ gap: 10 }}>
          <span className="text-[17px] font-semibold" style={{ color: "var(--text-primary)" }}>
            职业进度
          </span>
          <span
            className="text-[11px] font-semibold shrink-0"
            style={{
              color: "var(--accent-primary)",
              background: "var(--accent-primary-soft)",
              borderRadius: "var(--radius-pill)",
              padding: "2px 10px",
            }}
          >
            {mode.name}
            {mode.daysLeft !== null ? ` · 距阶段结束 ${daysText(mode.daysLeft)}` : ""}
          </span>
        </div>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          截至 {asOf} · {mode.objective}
        </span>
      </div>

      {primary ? (
        <TrackMetrics track={primary} emphasis />
      ) : (
        <span className="text-[13px]" style={{ color: "var(--text-muted)" }}>
          暂无赛道数据（后端 target_roles 为空）
        </span>
      )}

      {others.length > 0 ? (
        <div className="flex flex-col" style={{ gap: 12, paddingTop: 4, borderTop: "1px solid var(--border-default)" }}>
          {others.map((t) => (
            <TrackMetrics key={t.key} track={t} emphasis={false} />
          ))}
        </div>
      ) : null}

      {/* 关键节点倒计时（导师联系窗口 / 硕士答辩），由后端 transition_context 单点定义 */}
      {progress.milestones.length > 0 ? (
        <div
          className="flex flex-col"
          style={{ gap: 10, paddingTop: 12, borderTop: "1px solid var(--border-default)" }}
        >
          <span className="text-[13px] font-semibold" style={{ color: "var(--text-secondary)" }}>
            关键节点
          </span>
          {progress.milestones.map((m) => (
            <div key={m.key} className="flex items-start" style={{ gap: 10 }}>
              <span
                className="text-[11px] font-semibold shrink-0"
                style={{
                  color: COUNTDOWN_COLOR[m.status],
                  background: "var(--surface-canvas)",
                  border: `1px solid ${COUNTDOWN_COLOR[m.status]}`,
                  borderRadius: "var(--radius-pill)",
                  padding: "1px 8px",
                  marginTop: 1,
                }}
              >
                {COUNTDOWN_LABEL[m.status]}
              </span>
              <span className="text-[13px]" style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>
                <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{m.label}：</span>
                {daysText(m.daysLeft)}（{m.deadline}）· {m.note}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
