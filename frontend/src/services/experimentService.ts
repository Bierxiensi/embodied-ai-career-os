/** 实验记录 + 证据链 + commit 同步 服务层（P2 证据闭环）。
 *
 * 对应后端 /api/experiments、/api/skills/evidence、/api/plan/commits/sync。
 * 后端 snake_case → 前端 camelCase，int id → string id。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  CommitSyncResult,
  Experiment,
  ExperimentCreate,
  ExperimentMetric,
  ExperimentVariant,
  SkillEvidence,
} from "@/types";

interface ExperimentDTO {
  id: number;
  plan_day_id: number | null;
  day_seq: number;
  name: string;
  kind: string;
  skill_name: string | null;
  variants: ExperimentVariant[];
  metrics: ExperimentMetric[];
  conclusion: string | null;
  artifact_ids: string[];
  created_at: string;
  updated_at: string;
}

function toExperiment(d: ExperimentDTO): Experiment {
  return {
    id: String(d.id),
    planDayId: d.plan_day_id != null ? String(d.plan_day_id) : null,
    daySeq: d.day_seq,
    name: d.name,
    kind: d.kind as Experiment["kind"],
    skillName: d.skill_name ?? null,
    variants: d.variants ?? [],
    metrics: d.metrics ?? [],
    conclusion: d.conclusion ?? null,
    artifactIds: d.artifact_ids ?? [],
    createdAt: d.created_at,
    updatedAt: d.updated_at,
  };
}

/** 实验列表（可按技能 / 课程日过滤）。 */
export async function getExperiments(params?: {
  skillName?: string;
  daySeq?: number;
}): Promise<Experiment[]> {
  const qs = new URLSearchParams();
  if (params?.skillName) qs.set("skill_name", params.skillName);
  if (params?.daySeq != null) qs.set("day_seq", String(params.daySeq));
  const dtos = await apiClient.get<ExperimentDTO[]>(
    `/api/experiments?${qs.toString()}`,
  );
  return dtos.map(toExperiment);
}

/** 新增实验。 */
export async function createExperiment(payload: ExperimentCreate): Promise<Experiment> {
  const dto = await apiClient.post<ExperimentDTO>("/api/experiments", {
    plan_day_id: payload.planDayId ? Number(payload.planDayId) : null,
    day_seq: payload.daySeq,
    name: payload.name,
    kind: payload.kind,
    skill_name: payload.skillName ?? null,
    variants: payload.variants ?? [],
    metrics: payload.metrics ?? [],
    conclusion: payload.conclusion ?? null,
    artifact_ids: payload.artifactIds ?? [],
  });
  return toExperiment(dto);
}

/** 删除实验。 */
export async function deleteExperiment(id: string): Promise<void> {
  await apiClient.delete(`/api/experiments/${id}`);
}

/** GitHub commit 按课程日自动归集（无 token 时优雅跳过）。 */
export async function syncCommits(payload?: {
  repo?: string;
  token?: string;
  since?: string;
  until?: string;
  commits?: Record<string, unknown>[];
}): Promise<CommitSyncResult> {
  return apiClient.post<CommitSyncResult>("/api/plan/commits/sync", payload ?? {});
}

/** 全部技能的 evidence-gated 证据链。 */
export async function getSkillEvidenceList(): Promise<SkillEvidence[]> {
  const dtos = await apiClient.get<
    {
      id: number;
      name: string;
      level: number;
      target_level: number;
      evidence_gate: number;
      evidence: SkillEvidence["evidence"];
    }[]
  >("/api/skills/evidence");
  return dtos.map((d) => ({
    id: String(d.id),
    name: d.name,
    level: d.level,
    targetLevel: d.target_level,
    evidenceGate: d.evidence_gate,
    evidence: d.evidence,
  }));
}
