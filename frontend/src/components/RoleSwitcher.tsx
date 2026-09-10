"use client";

/** 视角切换器（Client Component）。
 *
 * 作用：在「求职冲刺」与「具身智能」两个视角之间切换。
 * 同一份能力数据、两个观察方式 —— 视角只改「看什么」，不改数据。
 *
 * 状态存储（为什么不是纯 localStorage）：
 *   1. URL `?role=`    —— Server Component 的 searchParams 原生可读，SSR 无闪烁，可分享/收藏
 *   2. cookie 记忆     —— 从其他页面返回 Dashboard 时（无 URL 参数）沿用上次选择
 *   纯 localStorage 做不到第 1 点：Server Component 读不到，只能等客户端 hydrate
 *   后再渲染，会出现图表闪烁 + hydration mismatch。
 *
 * 数据流：点击 → 写 cookie → router.push(`?role=`) → Server Component 重渲染 → 新赛道雷达
 */

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import type { ViewRole, ViewRoleOption } from "@/types";
import { VIEW_ROLE_COOKIE, viewRoleHref } from "@/lib/viewRole";

const COOKIE_MAX_AGE = 60 * 60 * 24 * 180; // 180 天

type Props = {
  options: ViewRoleOption[];
  active: ViewRole;
};

export default function RoleSwitcher({ options, active }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const activeOption = options.find((o) => o.role === active) ?? null;

  function select(role: ViewRole) {
    if (role === active) return;

    // 记住选择：下次不带 ?role= 进入 Dashboard 时沿用
    document.cookie = `${VIEW_ROLE_COOKIE}=${role}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`;

    startTransition(() => router.push(viewRoleHref(role), { scroll: false }));
  }

  return (
    <div className="flex flex-col" style={{ gap: 8 }}>
      {/* 分段控件 */}
      <div
        className="inline-flex items-center self-start"
        style={{
          gap: 2,
          padding: 3,
          background: "var(--color-zinc-100)",
          border: "1px solid var(--color-hairline-soft)",
          borderRadius: "var(--radius-pill)",
          opacity: isPending ? 0.7 : 1,
        }}
      >
        {options.map((opt) => {
          const isActive = opt.role === active;
          return (
            <button
              key={opt.role}
              type="button"
              disabled={!opt.available || isPending}
              onClick={() => select(opt.role)}
              title={opt.available ? opt.description : "后端未提供对应赛道"}
              className="inline-flex items-center border-none"
              style={{
                gap: 7,
                height: 32,
                paddingInline: 14,
                borderRadius: "var(--radius-pill)",
                background: isActive ? "var(--color-card)" : "transparent",
                color: isActive
                  ? "var(--color-ink)"
                  : opt.available
                    ? "var(--color-ink-48)"
                    : "var(--color-ink-28)",
                fontSize: 13,
                fontWeight: isActive ? 600 : 500,
                cursor: !opt.available ? "not-allowed" : isPending ? "wait" : "pointer",
                boxShadow: isActive ? "0 1px 2px rgba(0,0,0,0.06)" : "none",
                transition: "background 0.15s ease, color 0.15s ease",
              }}
            >
              <span>{opt.label}</span>
              {opt.matchPct !== null && (
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    fontVariantNumeric: "tabular-nums",
                    color: isActive ? "var(--color-primary)" : "var(--color-ink-28)",
                  }}
                >
                  {opt.matchPct}%
                </span>
              )}
              {opt.isLongTerm && (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    padding: "1px 6px",
                    borderRadius: "var(--radius-pill)",
                    background: "var(--color-amber-soft)",
                    color: "var(--color-amber-deep)",
                  }}
                >
                  长期
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* 当前视角说明 —— 让「看的这个图是什么」一目了然 */}
      {activeOption && (
        <p className="text-xs" style={{ color: "var(--color-ink-48)" }}>
          {activeOption.trackName ? (
            <>
              视角对齐 <strong style={{ color: "var(--color-ink-80)" }}>{activeOption.trackName}</strong>
              （{activeOption.isLongTerm ? "长期目标" : "当前主线"}） · {activeOption.description}
            </>
          ) : (
            activeOption.description
          )}
        </p>
      )}
    </div>
  );
}
