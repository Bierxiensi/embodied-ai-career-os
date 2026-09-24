import type { Position } from "@/types";

type Props = {
  /** 当前工作区（来自 /api/transition/dashboard）。 */
  position: Position;
};

/** 第 2 区：当前工作 —— 在职事实 + 在职转型窗口。
 *
 * 为什么落地页要有这一区：
 *   这个平台的使用者**在在职状态下转型**，"还有多少时间可支配"取决于
 *   在职窗口（2026.09–2027.03），而不是求职期的"offer 倒计时"。
 *   把在职事实摆在页面上，也是防止把转型期误按求职节奏推进。
 *
 * 文案一律取自后端 `core/transition_context`（公司/岗位/方向/起止月份单点定义），
 * 前端不硬编码 —— 换工作时只改后端一处。
 */
export default function PositionCard({ position }: Props) {
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
      <div className="flex items-center justify-between" style={{ gap: 10 }}>
        <span className="text-[17px] font-semibold" style={{ color: "var(--text-primary)" }}>
          当前工作
        </span>
        <span
          className="text-[11px] font-semibold shrink-0"
          style={{
            color: "var(--accent-success)",
            background: "var(--accent-success-soft)",
            borderRadius: "var(--radius-pill)",
            padding: "2px 10px",
          }}
        >
          {position.statusLabel}
        </span>
      </div>

      <div className="flex flex-col" style={{ gap: 4 }}>
        <span className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
          {position.company}
        </span>
        <span className="text-[13px]" style={{ color: "var(--text-secondary)" }}>
          {position.role}
        </span>
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          {position.focus}
        </span>
      </div>

      <div
        className="flex flex-col"
        style={{
          gap: 6,
          padding: 12,
          background: "var(--surface-canvas)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
        }}
      >
        <span
          className="text-[11px] font-semibold uppercase"
          style={{ color: "var(--text-muted)", letterSpacing: "0.04em" }}
        >
          在岗区间
        </span>
        <span className="text-[13px]" style={{ color: "var(--text-primary)" }}>
          {position.sinceLabel} – {position.endLabel ?? "在职中"}
        </span>
        <span
          className="text-[11px] font-semibold uppercase"
          style={{ color: "var(--text-muted)", letterSpacing: "0.04em", marginTop: 4 }}
        >
          {position.transitionWindowLabel}
        </span>
        <span className="text-[13px]" style={{ color: "var(--text-primary)" }}>
          {position.transitionWindowStart} – {position.transitionWindowEnd}
        </span>
      </div>

      <span className="text-xs" style={{ color: "var(--text-muted)", lineHeight: 1.7 }}>
        {position.note}
      </span>
    </div>
  );
}
