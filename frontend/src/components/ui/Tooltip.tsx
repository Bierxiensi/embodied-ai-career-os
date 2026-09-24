"use client";

import { useState, useRef, type ReactNode } from "react";

type Placement = "top" | "bottom" | "left" | "right";

interface TooltipProps {
  content: ReactNode;
  placement?: Placement;
  delay?: number;
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function Tooltip({ content, placement = "top", delay = 200, children, className, style }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const show = () => {
    timerRef.current = setTimeout(() => setVisible(true), delay);
  };

  const hide = () => {
    clearTimeout(timerRef.current);
    setVisible(false);
  };

  const posMap: Record<Placement, React.CSSProperties> = {
    top: { bottom: "100%", left: "50%", transform: "translateX(-50%)", marginBottom: 8 },
    bottom: { top: "100%", left: "50%", transform: "translateX(-50%)", marginTop: 8 },
    left: { right: "100%", top: "50%", transform: "translateY(-50%)", marginRight: 8 },
    right: { left: "100%", top: "50%", transform: "translateY(-50%)", marginLeft: 8 },
  };

  return (
    <span
      className={className}
      style={{ position: "relative", display: "inline-flex", ...style }}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {visible && (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            ...posMap[placement],
            padding: "6px 10px",
            fontSize: 11,
            fontWeight: 500,
            borderRadius: "var(--radius-item)",
            background: "var(--surface-elevated)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-default)",
            boxShadow: "var(--shadow-elevated)",
            whiteSpace: "nowrap",
            zIndex: 1000,
            pointerEvents: "none",
          }}
        >
          {content}
        </span>
      )}
    </span>
  );
}
