"use client";

import { useState, useEffect, useRef, type ReactNode } from "react";

interface CommandItem {
  id: string;
  label: string;
  icon?: ReactNode;
  action: () => void;
}

interface CommandGroup {
  label: string;
  items: CommandItem[];
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  groups: CommandGroup[];
  className?: string;
  style?: React.CSSProperties;
}

export default function CommandPalette({ open, onClose, groups, className, style }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // 过滤
  const filtered = groups
    .map((g) => ({
      ...g,
      items: g.items.filter((i) => i.label.toLowerCase().includes(query.toLowerCase())),
    }))
    .filter((g) => g.items.length > 0);

  const allItems = filtered.flatMap((g) => g.items);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(i + 1, allItems.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Enter" && allItems[selectedIdx]) {
        allItems[selectedIdx].action();
        onClose();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, allItems, selectedIdx, onClose]);

  if (!open) return null;

  let flatIdx = 0;

  return (
    <div
      ref={overlayRef}
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      className={className}
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "20vh",
        background: "var(--surface-overlay)",
        zIndex: 1000,
        ...style,
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 520,
          background: "var(--surface-elevated)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-card)",
          boxShadow: "var(--shadow-elevated)",
          overflow: "hidden",
          animation: "modal-enter 200ms ease-out",
        }}
      >
        {/* 搜索框 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "14px 16px",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <span style={{ color: "var(--text-muted)", fontSize: 16 }}>🔍</span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIdx(0);
            }}
            placeholder="搜索页面、任务、技能..."
            style={{
              flex: 1,
              border: "none",
              background: "transparent",
              color: "var(--text-primary)",
              fontSize: 14,
              outline: "none",
            }}
          />
          <kbd
            style={{
              fontSize: 10,
              padding: "2px 6px",
              borderRadius: 4,
              border: "1px solid var(--border-default)",
              background: "var(--surface-card)",
              color: "var(--text-muted)",
            }}
          >
            ESC
          </kbd>
        </div>

        {/* 结果列表 */}
        <div style={{ maxHeight: 360, overflow: "auto", padding: 8 }}>
          {filtered.length === 0 && (
            <div style={{ padding: 24, textAlign: "center", fontSize: 13, color: "var(--text-muted)" }}>
              无匹配结果
            </div>
          )}
          {filtered.map((group) => (
            <div key={group.label} style={{ marginBottom: 8 }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  padding: "4px 8px",
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                {group.label}
              </div>
              {group.items.map((item) => {
                const idx = flatIdx++;
                const isSelected = idx === selectedIdx;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      item.action();
                      onClose();
                    }}
                    onMouseEnter={() => setSelectedIdx(idx)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      width: "100%",
                      padding: "10px 12px",
                      border: "none",
                      borderRadius: "var(--radius-item)",
                      background: isSelected ? "var(--accent-primary-soft)" : "transparent",
                      color: isSelected ? "var(--accent-primary)" : "var(--text-primary)",
                      cursor: "pointer",
                      fontSize: 13,
                      fontWeight: isSelected ? 500 : 400,
                      textAlign: "left",
                      transition: "120ms ease-out",
                    }}
                  >
                    {item.icon && (
                      <span style={{ display: "flex", alignItems: "center", fontSize: 14, opacity: 0.7 }}>
                        {item.icon}
                      </span>
                    )}
                    {item.label}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
