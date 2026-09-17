"use client";

import { useState } from "react";

interface Props {
  question: string;
  answerOutline?: string | null;
  onAnswer: (answer: string) => void;
  disabled?: boolean;
}

export default function OpenQuestion({ question, answerOutline, onAnswer, disabled }: Props) {
  const [value, setValue] = useState("");
  const [showOutline, setShowOutline] = useState(false);

  const handleSubmit = () => {
    if (value.trim()) onAnswer(value.trim());
  };

  return (
    <div>
      <p style={{ fontSize: 16, lineHeight: 1.6, marginBottom: 16 }}>{question}</p>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        placeholder="写下你的回答..."
        rows={5}
        style={{
          width: "100%",
          padding: "10px 14px",
          borderRadius: 8,
          border: "2px solid #e5e7eb",
          fontSize: 14,
          outline: "none",
          resize: "vertical",
          fontFamily: "inherit",
        }}
      />
      <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
        {!disabled && value.trim() && (
          <button
            onClick={handleSubmit}
            style={{
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
        {answerOutline && (
          <button
            onClick={() => setShowOutline(!showOutline)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              background: "transparent",
              color: "#6b7280",
              border: "1px solid #d1d5db",
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            {showOutline ? "隐藏参考答案" : "显示参考答案"}
          </button>
        )}
      </div>
      {showOutline && answerOutline && (
        <div
          style={{
            marginTop: 12,
            padding: 12,
            borderRadius: 8,
            background: "#f9fafb",
            border: "1px solid #e5e7eb",
            fontSize: 14,
            lineHeight: 1.6,
            whiteSpace: "pre-wrap",
          }}
        >
          <strong>参考答案要点：</strong>
          <br />
          {answerOutline}
        </div>
      )}
    </div>
  );
}
