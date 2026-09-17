"use client";

import { useState } from "react";

interface Props {
  question: string;
  options: string[];
  onAnswer: (answer: string) => void;
  disabled?: boolean;
}

export default function ChoiceQuestion({ question, options, onAnswer, disabled }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = (option: string) => {
    if (disabled) return;
    setSelected(option);
  };

  const handleSubmit = () => {
    if (selected) onAnswer(selected);
  };

  return (
    <div>
      <p style={{ fontSize: 16, lineHeight: 1.6, marginBottom: 16 }}>{question}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {options.map((opt, i) => {
          const letter = String.fromCharCode(65 + i); // A, B, C, D
          const isSelected = selected === letter || selected === opt;
          return (
            <button
              key={i}
              onClick={() => handleSelect(letter)}
              disabled={disabled}
              style={{
                textAlign: "left",
                padding: "10px 14px",
                borderRadius: 8,
                border: `2px solid ${isSelected ? "#3b82f6" : "#e5e7eb"}`,
                background: isSelected ? "#eff6ff" : "white",
                cursor: disabled ? "default" : "pointer",
                fontSize: 14,
                transition: "all 0.15s",
              }}
            >
              <strong>{letter}.</strong> {opt.replace(/^[A-D]\.\s*/, "")}
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
