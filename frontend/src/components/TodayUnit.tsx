"use client";

/** 今日关键单元：取 day_seq 对应单元，打开即懒生成（后端保证）。 */

import { useEffect, useState } from "react";
import { listUnits, getUnit } from "@/services/masteryService";
import type { MasteryUnit } from "@/types";
import UnitView from "./UnitView";

export default function TodayUnit({ daySeq }: { daySeq: number | null }) {
  const [unit, setUnit] = useState<MasteryUnit | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (daySeq === null) return;
    (async () => {
      try {
        const list = await listUnits(daySeq);
        if (list.length > 0) {
          setUnit(await getUnit(list[0].id));
        }
      } catch {
        setError("单元加载失败（后端不可用或网格未铺——cd backend && python -c \"from app.db.base import SessionLocal; from app.services.mastery.grid import sync_grid; sync_grid(SessionLocal())\"）");
      }
    })();
  }, [daySeq]);

  if (error) {
    return (
      <p className="text-xs" style={{ padding: 12, color: "var(--accent-danger)", background: "var(--accent-danger-soft)", borderRadius: "var(--radius-md)" }}>
        {error}
      </p>
    );
  }
  if (!unit) return null;
  return <UnitView unit={unit} />;
}
