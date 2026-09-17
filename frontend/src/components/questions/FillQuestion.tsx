"use client";

import { useState } from "react";

interface Props {
  question: string;
  onAnswer: (answer: string) => void;
  disabled?: boolean;
}

export default function FillQuestion({ question, onAnswer, disabled }: Props) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    if (value.trim()) onAnswer(value.trim());
  };

  return (
    <div>
      <p style={{ fontSize: 16, lineHeight: 1.6, marginBottom: 16 }}>{question}</p>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder="输入你的答案..."
        style={{
          width: "100%",
          padding: "10px 14px",
          borderRadius: 8,
          border: "2px solid #e5e7eb",
          fontSize: 14,
          outline: "none",
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && value.trim() && !disabled) handleSubmit();
        }}
      />
      {!disabled && value.trim() && (
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
