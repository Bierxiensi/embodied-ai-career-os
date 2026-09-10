"use client";

import { useState, useEffect } from "react";
import type { CommitSuggestion } from "@/types";
import { githubService } from "@/services/githubService";

export default function PendingSuggestions() {
  const [items, setItems] = useState<CommitSuggestion[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchItems = async () => {
    try {
      const data = await githubService.getSuggestions();
      setItems(data || []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchItems(); }, []);

  const handleConfirm = async (id: string, skill: string) => {
    await githubService.confirm(id, skill);
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleReject = async (id: string) => {
    await githubService.reject(id);
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  if (loading) return null;
  if (items.length === 0) return null;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">
        📋 待确认（{items.length} 条新 commit）
      </h2>
      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="rounded-lg border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800"
          >
            <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
              {item.commitMessage}
            </p>
            <p className="mt-0.5 text-xs text-zinc-500">
              {item.commitSha} · {item.summary || ""}
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {item.aiSuggestions.map((s, idx) => (
                <button
                  key={idx}
                  onClick={() => handleConfirm(item.id, s.skill)}
                  className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-300"
                  title={s.reason}
                >
                  ✓ {s.skill}
                </button>
              ))}
              <button
                onClick={() => handleReject(item.id)}
                className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs text-zinc-500 hover:bg-zinc-200 dark:bg-zinc-700 dark:text-zinc-400"
              >
                ✗ 都不是
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
