"use client";

import { useEffect, useRef, type ReactNode } from "react";

type Size = "sm" | "md" | "lg" | "full";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  size?: Size;
  title?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const sizeMap: Record<Size, React.CSSProperties> = {
  sm: { maxWidth: 400 },
  md: { maxWidth: 560 },
  lg: { maxWidth: 720 },
  full: { maxWidth: "90vw", maxHeight: "90vh" },
};

export default function Modal({ open, onClose, size = "md", title, footer, children, className, style }: ModalProps) {
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

  return (
    <div
      ref={overlayRef}
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--surface-overlay)",
        backdropFilter: "var(--backdrop-blur)",
        zIndex: 1000,
        padding: 24,
      }}
    >
      <div
        role="dialog"
        aria-modal
        className={className}
        style={{
          width: "100%",
          ...sizeMap[size],
          background: "var(--surface-elevated)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-card)",
          boxShadow: "var(--shadow-elevated)",
          display: "flex",
          flexDirection: "column",
          maxHeight: size === "full" ? "90vh" : "80vh",
          animation: "modal-enter 200ms ease-out",
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
                transition: "120ms ease-out",
              }}
              aria-label="关闭"
            >
              ✕
            </button>
          </div>
        )}
        <div style={{ flex: 1, padding: 20, overflow: "auto" }}>{children}</div>
        {footer && (
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 8,
              padding: "16px 20px",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
