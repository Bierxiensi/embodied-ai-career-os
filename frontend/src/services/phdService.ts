/** 博士模块服务层（Phase 1）。

 * 调用后端 /api/phd/*，做字段适配。
 * 六维匹配结果由后端 PhDMatchEngine 计算，前端只渲染，不重算。
 */

import { apiClient } from "@/lib/apiClient";

/** 研究方向 DTO。 */
export interface ResearchDirectionDTO {
  id: number;
  key: string;
  name: string;
  description: string | null;
  interest_weight: number;
  created_at: string;
}

/** 六维匹配结果（对齐 backend/app/agents/phd/agent.py）。 */
export interface PhDMatchDTO {
  overall: number;
  grade: string;
  dimensions: {
    direction_fit: number;
    institution_tier: number;
    geo: number;
    publication_match: number;
    in_service_friendly: number;
    timeline: number;
  };
  gaps: { dimension: string; score: number; hint: string }[];
  computed_at?: string;
}

/** 导师 DTO（含从所属机会反查的展示字段）。 */
export interface PhDAdvisorDTO {
  id: number;
  target_id: number | null;
  name: string;
  title: string | null;
  research_area: string | null;
  recruiting: boolean;
  in_service_friendly: boolean;
  homepage: string | null;
  notes: string | null;
  match_json: PhDMatchDTO | null;
  last_matched_at: string | null;
  source: string;
  // 反查字段
  institution: string | null;
  city: string | null;
  tier: string | null;
  direction_key: string | null;
  track_key: string | null;
  application_deadline: string | null;
}

/** 六维维度中文标签（前端展示用）。 */
export const DIM_LABELS: Record<keyof PhDMatchDTO["dimensions"], string> = {
  direction_fit: "研究方向契合",
  institution_tier: "院校层次",
  geo: "地域/在职便利",
  publication_match: "成果门槛匹配",
  in_service_friendly: "在职/非全友好",
  timeline: "时间窗口",
};

/** 获取全部导师（含所属机会字段 + 六维匹配）。 */
export async function getPhdAdvisors(): Promise<PhDAdvisorDTO[]> {
  return apiClient.get<PhDAdvisorDTO[]>("/api/phd/advisors");
}

/** 获取研究方向主数据。 */
export async function getPhdDirections(): Promise<ResearchDirectionDTO[]> {
  return apiClient.get<ResearchDirectionDTO[]>("/api/phd/directions");
}

/** 重算全部导师的六维匹配。 */
export async function matchAllAdvisors(): Promise<{ matched: number }> {
  return apiClient.post<{ matched: number }>("/api/phd/advisors/match-all");
}
