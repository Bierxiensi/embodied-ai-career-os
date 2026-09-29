/** 掌握单元服务（计划 2）。snake_case → camelCase 在此层完成。 */

import { apiClient } from "@/lib/apiClient";
import type { AnswerResult, MasteryUnit, UnitItem } from "@/types";

interface UnitItemDTO {
  id: number;
  unit_id: number;
  kind: UnitItem["kind"];
  body: string;
  is_verified: boolean;
  verified_at: string | null;
}

interface UnitDTO {
  id: number;
  source_type: string;
  source_ref: string;
  title: string;
  skill_ids: string[];
  day_seq: number | null;
  generation_mode: "llm" | "rule";
  status: string;
  items: UnitItemDTO[];
}

function toUnit(d: UnitDTO): MasteryUnit {
  return {
    id: d.id,
    sourceType: d.source_type,
    sourceRef: d.source_ref,
    title: d.title,
    skillIds: d.skill_ids,
    daySeq: d.day_seq,
    generationMode: d.generation_mode,
    status: d.status,
    items: d.items.map((i) => ({
      id: i.id,
      unitId: i.unit_id,
      kind: i.kind,
      body: i.body,
      isVerified: i.is_verified,
      verifiedAt: i.verified_at,
    })),
  };
}

export async function listUnits(daySeq?: number): Promise<MasteryUnit[]> {
  const qs = daySeq !== undefined ? `?day_seq=${daySeq}` : "";
  const dtos = await apiClient.get<UnitDTO[]>(`/api/mastery/units${qs}`);
  return dtos.map(toUnit);
}

export async function getUnit(id: number): Promise<MasteryUnit> {
  return toUnit(await apiClient.get<UnitDTO>(`/api/mastery/units/${id}`));
}

export async function answerItem(
  unitId: number,
  itemId: number,
  answer: string,
): Promise<AnswerResult> {
  const d = await apiClient.post<{
    item_id: number; correct: boolean; verified: boolean;
    rationale: string | null; card_id: number | null;
  }>(`/api/mastery/units/${unitId}/answer`, { item_id: itemId, answer });
  return { itemId: d.item_id, correct: d.correct, verified: d.verified, rationale: d.rationale, cardId: d.card_id };
}

export async function teachBackComplete(payload: {
  unitId: number;
  durationMinutes?: number | null;
  answers: { itemId: number; spoken: string }[];
}): Promise<{ logId: number; cardsCreated: number; verdicts: { itemId: number; passed: boolean; hint: string | null }[] }> {
  const d = await apiClient.post<{
    log_id: number; cards_created: number;
    verdicts: { item_id: number; passed: boolean; hint: string | null }[];
  }>("/api/teach-back/complete", {
    unit_id: payload.unitId,
    duration_minutes: payload.durationMinutes ?? null,
    answers: payload.answers.map((a) => ({ item_id: a.itemId, spoken: a.spoken })),
  });
  return {
    logId: d.log_id,
    cardsCreated: d.cards_created,
    verdicts: d.verdicts.map((v) => ({ itemId: v.item_id, passed: v.passed, hint: v.hint })),
  };
}
