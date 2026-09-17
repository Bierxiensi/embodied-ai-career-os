"use client";

import { useState } from "react";

interface Props {
  question: string;
  onAnswer: (answer: string) => void;
  disabled?: boolean;
}

export default function JudgeQuestion({ question, onAnswer, disabled }: Props) {
  const [selected, setSelected] = useState<"正确" | "错误" | null>(null);

  const handleClick = (value: "正确" | "错误") => {
    if (disabled) return;
    setSelected(value);
  };

  const handleSubmit = () => {
    if (selected) onAnswer(selected);
  };

  return (
    <div>
      <p style={{ fontSize: 16, lineHeight: 1.6, marginBottom: 16 }}>{question}</p>
      <div style={{ display: "flex", gap: 12 }}>
        {(["正确", "错误"] as const).map((v) => {
          const isSelected = selected === v;
          return (
            <button
              key={v}
              onClick={() => handleClick(v)}
              disabled={disabled}
              style={{
                flex: 1,
                padding: "14px 20px",
                borderRadius: 8,
                border: `2px solid ${isSelected ? (v === "正确" ? "#22c55e" : "#ef4444") : "#e5e7eb"}`,
                background: isSelected ? (v === "正确" ? "#f0fdf4" : "#fef2f2") : "white",
                cursor: disabled ? "default" : "pointer",
                fontSize: 16,
                fontWeight: 600,
                transition: "all 0.15s",
              }}
            >
              {v === "正确" ? "✅" : "❌"} {v}
            </button>
          );
        })}
      </div>
      {!disabled && selected && (
        <button
          onClick={handleSubmit}
          style={{
            marginTop: 12,
            padding: "8px 24px",
            borderRadius: 8,
            background: "#3b82f6",
            color: "white",
            border: "none",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          提交
        </button>
      )}
    </div>
  );
}
