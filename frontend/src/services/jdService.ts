/** 岗位池服务层（Batch 1）。

 * 职责：封装 /api/job-postings 的列表 / 统计 / 录入 / 重算 / 删除，
 * 并把后端 snake_case 适配为前端 camelCase 类型。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  DimensionScores,
  JobPoolStats,
  JobPosting,
  JobPostingCreateInput,
  MatchGap,
  MatchGrade,
  PostingTier,
} from "@/types";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface JobPostingDTO {
  id: number;
  company: string;
  title: string;
  city: string | null;
  salary_range: string | null;
  jd_text: string | null;
  source: string | null;
  url: string | null;
  posted_at: string | null;
  tier: number;
  track: string;
  required_skills: string[] | null;
  education: string | null;
  min_years: number | null;
  paper_required: boolean;
  status: string;
  created_at: string;
  updated_at: string;
  match_score: number | null;
  grade: string | null;
  dimension_scores: DimensionScores | null;
  gaps: MatchGap[] | null;
  matched_track: string | null;
  matched_at: string | null;
}

interface JobPoolStatsDTO {
  total: number;
  by_tier: Record<string, number>;
  by_grade: Record<string, number>;
  recommended: number;
  unmatched: number;
}

interface CreateResultDTO {
  created: JobPostingDTO[];
  skipped: string[];
  count: number;
}

/* ───────────────────────── 适配函数 ───────────────────────── */

function toPosting(dto: JobPostingDTO): JobPosting {
  return {
    id: String(dto.id),
    company: dto.company,
    title: dto.title,
    city: dto.city,
    salaryRange: dto.salary_range,
    jdText: dto.jd_text,
    source: dto.source,
    url: dto.url,
    postedAt: dto.posted_at,
    tier: dto.tier as PostingTier,
    track: dto.track,
    requiredSkills: dto.required_skills,
    education: dto.education,
    minYears: dto.min_years,
    paperRequired: dto.paper_required,
    status: dto.status,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    matchScore: dto.match_score,
    grade: (dto.grade as MatchGrade) ?? null,
    dimensionScores: dto.dimension_scores,
    gaps: dto.gaps,
    matchedTrack: dto.matched_track,
    matchedAt: dto.matched_at,
  };
}

/* ───────────────────────── API ───────────────────────── */

/** 岗位池列表（可按梯队/等级/赛道过滤）。 */
export async function listPostings(params?: {
  tier?: number;
  grade?: string;
  track?: string;
  status?: string;
}): Promise<JobPosting[]> {
  const qs = new URLSearchParams();
  if (params?.tier != null) qs.set("tier", String(params.tier));
  if (params?.grade) qs.set("grade", params.grade);
  if (params?.track) qs.set("track", params.track);
  if (params?.status) qs.set("status", params.status);
  const query = qs.toString();
  const dtos = await apiClient.get<JobPostingDTO[]>(
    `/api/job-postings${query ? `?${query}` : ""}`
  );
  return dtos.map(toPosting);
}

/** 岗位池统计。 */
export async function getPoolStats(): Promise<JobPoolStats> {
  const dto = await apiClient.get<JobPoolStatsDTO>("/api/job-postings/stats");
  return {
    total: dto.total,
    byTier: {
      1: dto.by_tier["1"] ?? 0,
      2: dto.by_tier["2"] ?? 0,
      3: dto.by_tier["3"] ?? 0,
    },
    byGrade: {
      A: dto.by_grade["A"] ?? 0,
      B: dto.by_grade["B"] ?? 0,
      C: dto.by_grade["C"] ?? 0,
      D: dto.by_grade["D"] ?? 0,
    },
    recommended: dto.recommended,
    unmatched: dto.unmatched,
  };
}

/** 录入一条 JD（自动解析技能 + 自动匹配）。 */
export async function createPosting(
  payload: JobPostingCreateInput
): Promise<{ created: JobPosting[]; skipped: string[]; count: number }> {
  const dto = await apiClient.post<CreateResultDTO>("/api/job-postings", payload);
  return {
    created: dto.created.map(toPosting),
    skipped: dto.skipped,
    count: dto.count,
  };
}

/** 重算某岗位匹配。 */
export async function recomputeMatch(id: string): Promise<JobPosting> {
  const dto = await apiClient.post<JobPostingDTO>(
    `/api/job-postings/${id}/match`
  );
  return toPosting(dto);
}

/** 删除岗位。 */
export async function deletePosting(id: string): Promise<void> {
  await apiClient.delete<void>(`/api/job-postings/${id}`);
}
