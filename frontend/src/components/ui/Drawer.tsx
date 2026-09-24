"use client";

import { useEffect, useRef, type ReactNode } from "react";

type Placement = "right" | "left" | "bottom";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  placement?: Placement;
  size?: number;
  title?: ReactNode;
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function Drawer({
  open,
  onClose,
  placement = "right",
  size = 360,
  title,
  children,
  className,
  style,
}: DrawerProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  const isVertical = placement === "bottom";
  const posStyle: React.CSSProperties =
    placement === "right"
      ? { right: 0, top: 0, bottom: 0, width: size }
      : placement === "left"
        ? { left: 0, top: 0, bottom: 0, width: size }
        : { bottom: 0, left: 0, right: 0, height: size };

  return (
    <div
      ref={overlayRef}
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--surface-overlay)",
        zIndex: 1000,
      }}
    >
      <div
        role="dialog"
        aria-modal
        className={className}
        style={{
          position: "absolute",
          ...posStyle,
          background: "var(--surface-elevated)",
          borderLeft: placement === "right" ? "1px solid var(--border-default)" : undefined,
          borderRight: placement === "left" ? "1px solid var(--border-default)" : undefined,
          borderTop: placement === "bottom" ? "1px solid var(--border-default)" : undefined,
          boxShadow: "var(--shadow-elevated)",
          display: "flex",
          flexDirection: "column",
          animation: `drawer-${placement} 200ms ease-out`,
          ...style,
        }}
      >
        {title && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "16px 20px",
              borderBottom: "1px solid var(--border-subtle)",
            }}
          >
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
              {title}
            </h2>
            <button
              onClick={onClose}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: 28,
                height: 28,
                borderRadius: "var(--radius-item)",
                border: "none",
                background: "transparent",
                color: "var(--text-muted)",
                cursor: "pointer",
                fontSize: 16,
              }}
              aria-label="关闭"
            >
              ✕
            </button>
          </div>
        )}
        <div style={{ flex: 1, padding: 20, overflow: "auto" }}>{children}</div>
      </div>
    </div>
  );
}
