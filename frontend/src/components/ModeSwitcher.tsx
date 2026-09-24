"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";

import ModeSwitchPanel from "@/components/ModeSwitchPanel";
import { useCareerMode } from "@/lib/careerModeContext";
import { ApiError } from "@/lib/apiClient";
import { switchCareerMode } from "@/services/careerModeService";
import type { CareerMode } from "@/types";

function badgeDeadlineText(mode: CareerMode): string {
  if (mode.daysLeft === null) return "长期";
  if (mode.daysLeft < 0) return "已过期";
  return `剩 ${mode.daysLeft} 天`;
}

/** 全局导航里的「当前阶段」徽章 + 切换入口。
 *
 * 数据来自 CareerModeContext（由 layout 层的 Provider 提供），
 * 不再自己 fetch —— 避免与 GlobalNav / Sidebar 重复请求。
 */
export default function ModeSwitcher() {
  const router = useRouter();
  const { current, available, isLoading, refreshMode } = useCareerMode();

  const [isOpen, setIsOpen] = useState(false);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [switchError, setSwitchError] = useState<string | null>(null);

  const openPanel = useCallback(() => {
    setPendingKey(null);
    setNote("");
    setSwitchError(null);
    setIsOpen(true);
  }, []);

  const closePanel = useCallback(() => setIsOpen(false), []);

  const confirmSwitch = useCallback(async () => {
    if (pendingKey === null) return;

    setIsSubmitting(true);
    setSwitchError(null);
    try {
      const result = await switchCareerMode(pendingKey, note.trim() || null);
      // 就地更新 Context：GlobalNav / Sidebar 立即响应
      refreshMode(result.current);
      setIsOpen(false);
      // 刷新服务端组件：任务与推荐口径随阶段变化
      router.refresh();
    } catch (err) {
      setSwitchError(
        err instanceof ApiError ? err.message : "切换失败，请稍后重试"
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [pendingKey, note, refreshMode, router]);

  if (isLoading) {
    return (
      <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
        阶段…
      </span>
    );
  }

  if (current === null) {
    return (
      <span className="text-[11px]" style={{ color: "var(--text-muted)" }} title="后端未连接">
        阶段不可用
      </span>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => (isOpen ? closePanel() : openPanel())}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        title={`${current.name} · ${current.objective}`}
        className="inline-flex items-center border-none"
        style={{
          gap: 8,
          height: 26,
          paddingInline: 12,
          borderRadius: "var(--radius-pill)",
          background: "rgba(255, 255, 255, 0.14)",
          color: "var(--surface-canvas)",
          fontSize: 12,
          fontWeight: 600,
          cursor: "pointer",
        }}
      >
        <span>{current.name}</span>
        <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>
          {badgeDeadlineText(current)}
        </span>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0" style={{ zIndex: 40 }} onClick={closePanel} />
          <ModeSwitchPanel
            current={current}
            available={available}
            pendingKey={pendingKey}
            note={note}
            isSubmitting={isSubmitting}
            errorMessage={switchError}
            onSelectMode={setPendingKey}
            onChangeNote={setNote}
            onCancel={closePanel}
            onConfirm={confirmSwitch}
          />
        </>
      )}
    </div>
  );
}
