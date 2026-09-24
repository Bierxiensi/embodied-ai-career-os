"use client";

import { useState, useRef, useEffect, type ReactNode } from "react";

type Placement = "top" | "bottom" | "left" | "right";

interface PopoverProps {
  trigger: ReactNode;
  content: ReactNode;
  placement?: Placement;
  className?: string;
  style?: React.CSSProperties;
}

export default function Popover({ trigger, content, placement = "bottom", className, style }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const posMap: Record<Placement, React.CSSProperties> = {
    top: { bottom: "100%", left: "50%", transform: "translateX(-50%)", marginBottom: 8 },
    bottom: { top: "100%", left: "50%", transform: "translateX(-50%)", marginTop: 8 },
    left: { right: "100%", top: "50%", transform: "translateY(-50%)", marginRight: 8 },
    right: { left: "100%", top: "50%", transform: "translateY(-50%)", marginLeft: 8 },
  };

  return (
    <div ref={ref} className={className} style={{ position: "relative", display: "inline-flex", ...style }}>
      <div onClick={() => setOpen(!open)} style={{ cursor: "pointer" }}>
        {trigger}
      </div>
      {open && (
        <div
          style={{
            position: "absolute",
            ...posMap[placement],
            minWidth: 180,
            background: "var(--surface-elevated)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-item)",
            boxShadow: "var(--shadow-elevated)",
            zIndex: 1000,
            padding: 12,
          }}
        >
          {content}
        </div>
      )}
    </div>
  );
}
