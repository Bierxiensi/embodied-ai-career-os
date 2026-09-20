"use client";

/** 模式切换面板（纯展示 + 回调）。
 *
 * 拆出来的原因：ModeSwitcher 负责取数与提交，本组件只负责"长什么样"，
 * 两者分开后各自的职责能用一句话说清，也不会把交互状态机混进布局代码。
 *
 * 颜色一律走 var(--color-*)，深浅主题自适应（见 app/globals.css）。
 */

import type { CareerMode } from "@/types";

type Props = {
  /** 当前生效的模式 */
  current: CareerMode;
  /** 全部可选模式 */
  available: CareerMode[];
  /** 用户已选中、但尚未确认切换的目标模式 key；null = 还没选 */
  pendingKey: string | null;
  note: string;
  isSubmitting: boolean;
  /** 切换失败时的提示（来自 ApiError.message） */
  errorMessage: string | null;
  onSelectMode: (modeKey: string) => void;
  onChangeNote: (note: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
};

/** 把 deadline 渲染成一句人话：长期模式没有硬截止，不显示"剩余 0 天"。 */
function deadlineText(mode: CareerMode): string {
  if (mode.deadline === null) return "无硬性截止（按季度 / 里程碑推进）";
  if (mode.daysLeft !== null && mode.daysLeft < 0) return `目标日期 ${mode.deadline}（已过期）`;
  return `目标日期 ${mode.deadline}${mode.daysLeft !== null ? ` · 剩 ${mode.daysLeft} 天` : ""}`;
}

export default function ModeSwitchPanel({
  current,
  available,
  pendingKey,
  note,
  isSubmitting,
  errorMessage,
  onSelectMode,
  onChangeNote,
  onCancel,
  onConfirm,
}: Props) {
  const pending = available.find((mode) => mode.key === pendingKey) ?? null;

  return (
    <div
      className="absolute"
      style={{
        top: 34,
        right: 0,
        width: 380,
        zIndex: 50,
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
        padding: 20,
        boxShadow: "0 10px 32px rgba(0, 0, 0, 0.18)",
      }}
      role="dialog"
      aria-label="切换职业阶段"
    >
      <p className="text-xs font-semibold" style={{ color: "var(--color-ink-48)" }}>
        当前阶段
      </p>
      <p className="text-sm font-semibold" style={{ color: "var(--color-ink)", marginTop: 2 }}>
        {current.name}
      </p>
      <p className="text-xs" style={{ color: "var(--color-ink-32)", marginTop: 2 }}>
        {current.objective}
      </p>
      <p className="text-xs" style={{ color: "var(--color-ink-48)", marginTop: 2 }}>
        {deadlineText(current)}
      </p>

      <div style={{ height: 1, background: "var(--color-hairline-soft)", margin: "14px 0" }} />

      <div className="flex flex-col" style={{ gap: 6 }}>
        {available.map((mode) => {
          const isPending = mode.key === pendingKey;
          return (
            <button
              key={mode.key}
              type="button"
              disabled={mode.isCurrent || isSubmitting}
              onClick={() => onSelectMode(mode.key)}
              className="flex items-center justify-between border-none text-left"
              style={{
                gap: 10,
                width: "100%",
                padding: "10px 12px",
                borderRadius: "var(--radius-item-md)",
                background: isPending ? "var(--color-primary-soft)" : "transparent",
                border: `1px solid ${isPending ? "var(--color-primary)" : "var(--color-hairline-soft)"}`,
                cursor: mode.isCurrent || isSubmitting ? "default" : "pointer",
                opacity: mode.isCurrent ? 0.6 : 1,
              }}
            >
              <span className="flex flex-col" style={{ gap: 2 }}>
                <span className="text-xs font-semibold" style={{ color: "var(--color-ink)" }}>
                  {mode.name}
                </span>
                <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
                  {mode.objective}
                </span>
              </span>
              {mode.isCurrent && (
                <span
                  className="text-xs font-semibold"
                  style={{
                    flexShrink: 0,
                    padding: "1px 8px",
                    borderRadius: "var(--radius-pill)",
                    background: "var(--color-emerald-soft)",
                    color: "var(--color-emerald-deep)",
                  }}
                >
                  当前
                </span>
              )}
            </button>
          );
        })}
      </div>

      {pending && (
        <div style={{ marginTop: 14 }}>
          <div
            style={{
              padding: 12,
              borderRadius: "var(--radius-item-md)",
              background: "var(--color-amber-soft)",
            }}
          >
            <p className="text-xs" style={{ color: "var(--color-amber-deep)", lineHeight: 1.6 }}>
              切换到「{pending.name}」后，<strong>不会删除、修改或隐藏</strong>任何既有职业目标、
              岗位、任务、投递与面试记录 —— 只会改变默认导航、推荐与任务统计口径。
            </p>
          </div>

          <textarea
            value={note}
            onChange={(event) => onChangeNote(event.target.value)}
            placeholder="切换原因（可选，会记入阶段切换历史）"
            rows={2}
            maxLength={500}
            disabled={isSubmitting}
            style={{
              width: "100%",
              marginTop: 10,
              padding: "8px 10px",
              fontSize: 12,
              lineHeight: 1.5,
              color: "var(--color-ink)",
              background: "var(--color-card)",
              border: "1px solid var(--color-hairline)",
              borderRadius: "var(--radius-item-sm)",
              resize: "vertical",
              fontFamily: "inherit",
            }}
          />

          {errorMessage && (
            <p className="text-xs" style={{ color: "var(--color-rose-deep)", marginTop: 8 }}>
              {errorMessage}
            </p>
          )}

          <div className="flex items-center justify-end" style={{ gap: 8, marginTop: 12 }}>
            <button
              type="button"
              onClick={onCancel}
              disabled={isSubmitting}
              style={{
                height: 30,
                paddingInline: 14,
                fontSize: 12,
                fontWeight: 500,
                color: "var(--color-ink-80)",
                background: "transparent",
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-pill)",
                cursor: "pointer",
              }}
            >
              取消
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={isSubmitting}
              style={{
                height: 30,
                paddingInline: 16,
                fontSize: 12,
                fontWeight: 600,
                color: "var(--color-on-primary)",
                background: "var(--color-primary)",
                border: "none",
                borderRadius: "var(--radius-pill)",
                cursor: isSubmitting ? "wait" : "pointer",
              }}
            >
              {isSubmitting ? "切换中…" : "确认切换"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
