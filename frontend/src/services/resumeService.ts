/** 简历线服务层（Batch 2）。

 * 职责：封装 /api/resume 的版本 / 事实 / 诊断接口，
 * 并把后端 snake_case 适配为前端 camelCase 类型。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  FactCategory,
  JdAlignmentItem,
  ResumeClaim,
  ResumeDiagnosis,
  ResumeFact,
  ResumeFactCreate,
  ResumeVersion,
  ResumeVersionCreate,
} from "@/types";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface ResumeVersionDTO {
  id: number;
  name: string;
  content_md: string | null;
  target_tier: number;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

interface ResumeFactDTO {
  id: number;
  category: string;
  title: string;
  org: string | null;
  start: string | null;
  end: string | null;
  facts: string[];
  source: string | null;
  created_at: string;
  updated_at: string;
}

interface ResumeClaimDTO {
  text: string;
  anchored: boolean;
  anchors: Array<{ fact_id: number; title: string; category: string }>;
  reason: string;
}

interface JdAlignmentDTO {
  skill: string;
  supported: boolean;
  evidence: string | null;
}

interface ResumeDiagnosisDTO {
  total: number;
  anchored_count: number;
  unanchored_count: number;
  fabrication_risk: number;
  claims: ResumeClaimDTO[];
  jd_alignment: JdAlignmentDTO[] | null;
}

interface ParseResultDTO {
  claims: string[];
  count: number;
}

/* ───────────────────────── 适配函数 ───────────────────────── */

function toVersion(dto: ResumeVersionDTO): ResumeVersion {
  return {
    id: String(dto.id),
    name: dto.name,
    contentMd: dto.content_md,
    targetTier: dto.target_tier as ResumeVersion["targetTier"],
    isPrimary: dto.is_primary,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toFact(dto: ResumeFactDTO): ResumeFact {
  return {
    id: String(dto.id),
    category: dto.category as FactCategory,
    title: dto.title,
    org: dto.org,
    start: dto.start,
    end: dto.end,
    facts: dto.facts || [],
    source: dto.source,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toDiagnosis(dto: ResumeDiagnosisDTO): ResumeDiagnosis {
  return {
    total: dto.total,
    anchoredCount: dto.anchored_count,
    unanchoredCount: dto.unanchored_count,
    fabricationRisk: dto.fabrication_risk,
    claims: (dto.claims || []).map((c) => ({
      text: c.text,
      anchored: c.anchored,
      anchors: c.anchors.map((a) => ({
        factId: a.fact_id,
        title: a.title,
        category: a.category,
      })),
      reason: c.reason,
    })),
    jdAlignment: (dto.jd_alignment || null) as JdAlignmentItem[] | null,
  };
}

/* ───────────────────────── API ───────────────────────── */

/** 简历版本列表。 */
export async function listVersions(): Promise<ResumeVersion[]> {
  const dtos = await apiClient.get<ResumeVersionDTO[]>("/api/resume");
  return dtos.map(toVersion);
}

/** 新建简历版本。 */
export async function createVersion(payload: ResumeVersionCreate): Promise<ResumeVersion> {
  const dto = await apiClient.post<ResumeVersionDTO>("/api/resume/versions", payload);
  return toVersion(dto);
}

/** 删除简历版本。 */
export async function deleteVersion(id: string): Promise<void> {
  await apiClient.delete<void>(`/api/resume/versions/${id}`);
}

/** 解析简历 md → claims。 */
export async function parseResume(contentMd: string): Promise<{ claims: string[]; count: number }> {
  const dto = await apiClient.post<ParseResultDTO>("/api/resume/parse", { content_md: contentMd });
  return { claims: dto.claims, count: dto.count };
}

/** 防虚构诊断。 */
export async function diagnose(payload: {
  versionId?: string | null;
  contentMd?: string | null;
  postingId?: string | null;
}): Promise<ResumeDiagnosis> {
  const dto = await apiClient.post<ResumeDiagnosisDTO>("/api/resume/diagnose", {
    version_id: payload.versionId ? Number(payload.versionId) : null,
    content_md: payload.contentMd,
    posting_id: payload.postingId ? Number(payload.postingId) : null,
  });
  return toDiagnosis(dto);
}

/** 事实锚点库。 */
export async function listFacts(): Promise<ResumeFact[]> {
  const dtos = await apiClient.get<ResumeFactDTO[]>("/api/resume/facts");
  return dtos.map(toFact);
}

/** 新增事实锚点。 */
export async function createFact(payload: ResumeFactCreate): Promise<ResumeFact> {
  const dto = await apiClient.post<ResumeFactDTO>("/api/resume/facts", payload);
  return toFact(dto);
}

/** 删除事实锚点。 */
export async function deleteFact(id: string): Promise<void> {
  await apiClient.delete<void>(`/api/resume/facts/${id}`);
}
