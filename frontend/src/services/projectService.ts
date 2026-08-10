/** 项目服务层。DTO snake_case → camelCase 转换。 */

import { apiClient } from "@/lib/apiClient";
import type { Milestone, Project } from "@/types";

interface ProjectDTO {
  id: number;
  name: string;
  goal: string;
  description: string | null;
  status: string;
  current_version: string;
  github_url: string | null;
  readme: string | null;
  sort_order: number;
  milestones?: MilestoneDTO[];
  milestone_total?: number;
  milestone_completed?: number;
  progress_pct?: number;
}

interface MilestoneDTO {
  id: number;
  project_id: number;
  version: string;
  title: string;
  goal: string;
  status: string;
  sort_order: number;
}

interface MilestoneCreateDTO {
  version: string;
  title: string;
  goal: string;
  status: string;
  sort_order: number;
}

function toMilestone(dto: MilestoneDTO): Milestone {
  return {
    id: String(dto.id),
    projectId: String(dto.project_id),
    version: dto.version,
    title: dto.title,
    goal: dto.goal,
    status: dto.status as Milestone["status"],
    sortOrder: dto.sort_order,
  };
}

function toProject(dto: ProjectDTO): Project {
  return {
    id: String(dto.id),
    name: dto.name,
    goal: dto.goal,
    description: dto.description,
    status: dto.status as Project["status"],
    currentVersion: dto.current_version,
    githubUrl: dto.github_url,
    readme: dto.readme,
    sortOrder: dto.sort_order,
    milestones: (dto.milestones || []).map(toMilestone),
    milestoneTotal: dto.milestone_total || 0,
    milestoneCompleted: dto.milestone_completed || 0,
    progressPct: dto.progress_pct || 0,
  };
}

export const projectService = {
  list: async (): Promise<Project[]> => {
    const dtos = await apiClient.get<ProjectDTO[]>("/api/projects");
    return dtos.map(toProject);
  },

  get: async (id: string): Promise<Project> => {
    const dto = await apiClient.get<ProjectDTO>(`/api/projects/${id}`);
    return toProject(dto);
  },

  create: async (data: {
    name: string; goal: string; status?: string;
    current_version?: string; description?: string; github_url?: string;
  }): Promise<Project> => {
    const dto = await apiClient.post<ProjectDTO>("/api/projects", data);
    return toProject(dto);
  },

  patch: async (id: string, data: Record<string, unknown>): Promise<Project> => {
    const dto = await apiClient.patch<ProjectDTO>(`/api/projects/${id}`, data);
    return toProject(dto);
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete<null>(`/api/projects/${id}`);
  },

  createMilestone: async (
    projectId: string, data: MilestoneCreateDTO
  ): Promise<Milestone> => {
    const dto = await apiClient.post<MilestoneDTO>(
      `/api/projects/${projectId}/milestones`, data
    );
    return toMilestone(dto);
  },

  patchMilestone: async (
    id: string, data: Record<string, unknown>
  ): Promise<Milestone> => {
    const dto = await apiClient.patch<MilestoneDTO>(
      `/api/milestones/${id}`, data
    );
    return toMilestone(dto);
  },

  deleteMilestone: async (id: string): Promise<void> => {
    await apiClient.delete<null>(`/api/milestones/${id}`);
  },

  generateTasks: async (
    milestoneId: string,
    data: {
      available_minutes: number;
      skills: Array<{ name: string; level: number; target: number }>;
    }
  ): Promise<unknown[]> => {
    return apiClient.post(`/api/milestones/${milestoneId}/tasks`, data);
  },
};
