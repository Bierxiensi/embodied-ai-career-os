/** GitHub 服务层 —— commit 感知建议。 */

import { apiClient } from "@/lib/apiClient";
import type { CommitSuggestion } from "@/types";

/** 后端 Suggestion 响应原始结构（snake_case）。 */
interface SuggestionDTO {
  id: string;
  commit_sha: string;
  commit_message: string;
  repo: string;
  ai_suggestions: Array<{
    skill: string;
    reason: string;
    confidence: number;
  }>;
  summary: string | null;
  created_at: string | null;
}

/** 后端 → 前端转换。snake_case → camelCase。 */
function toSuggestion(dto: SuggestionDTO): CommitSuggestion {
  return {
    id: dto.id,
    commitSha: dto.commit_sha,
    commitMessage: dto.commit_message,
    repo: dto.repo,
    aiSuggestions: dto.ai_suggestions,
    summary: dto.summary,
    createdAt: dto.created_at,
  };
}

export const githubService = {
  getSuggestions: async (): Promise<CommitSuggestion[]> => {
    const dtos = await apiClient.get<SuggestionDTO[]>("/api/github/suggestions");
    return dtos.map(toSuggestion);
  },

  confirm: (id: string, skill: string) =>
    apiClient.post<{ id: string; skill: string; status: string }>(
      `/api/github/suggestions/${id}/confirm`,
      { skill }
    ),

  reject: (id: string) =>
    apiClient.post<{ id: string; status: string }>(
      `/api/github/suggestions/${id}/reject`
    ),
};
