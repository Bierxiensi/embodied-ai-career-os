/** 求职看板服务层。

 * 职责：
 * - getJobHuntBoard()：聚合 /api/job-hunt 数据，做 snake_case → camelCase 适配
 * - 投递记录 CRUD：list / create / update / delete（/api/job-applications）
 *
 * 与 taskService 等保持一致：services 层统一封装字段适配，组件只读 camelCase 类型。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  JobAppStatus,
  JobApplication,
  JobApplicationCreate,
  JobHuntBoard,
  JobTaskItem,
  MatchGrade,
  PostingTier,
  TaskTrackScope,
} from "@/types";
import { toScopeSummary, toScopedTaskRef, type TaskScopeDTO } from "./taskScope";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface JobHuntDTO {
  career: {
    target_role: string | null;
    salary_target: number | null;
    timeframe: string | null;
    notes: string | null;
  } | null;
  offer_deadline: string;
  days_left: number;
  target_roles: Array<{
    key: string;
    name: string;
    priority: string;
    salary_range: string;
    note: string;
    frozen?: boolean;
    match_pct: number;
    strict_pct: number;
    qualified_count: number;
    required_count: number;
    skills: Array<{
      name: string;
      level: number;
      required: number;
      gap: number;
      missing: boolean;
    }>;
  }>;
  skill_gaps: Array<{
    name: string;
    category: string;
    level: number;
    target_level: number;
    gap: number;
    evidence: string[];
  }>;
  job_project: {
    id: number | null;
    name: string | null;
    current_version: string | null;
    milestones: Array<{
      id: number;
      version: string;
      title: string;
      goal: string;
      status: string;
      sort_order: number;
    }>;
    milestone_total: number;
    milestone_completed: number;
  } | null;
  tasks: {
    total: number;
    done: number;
    doing: number;
    todo: number;
    frozen_excluded: number;
    unclassified?: number;
    items: Array<{
      id: number;
      title: string;
      skill_name: string | null;
      status: string;
      duration: number | null;
      objective: string | null;
      track_key?: string | null;
      scope?: string;
    }>;
    frozen_items?: Array<{
      id: number;
      title: string;
      track_key: string | null;
      status: string;
      scope: string;
    }>;
    scope?: TaskScopeDTO;
  };
  applications: {
    total: number;
    by_status: Record<string, number>;
    response_rate: number;
    items: JobAppDTO[];
  };
  job_pool?: {
    total: number;
    by_grade: Record<string, number>;
    recommended: number;
    top: Array<{
      id: number;
      company: string;
      title: string;
      track: string;
      tier: number;
      match_score: number;
      grade: string;
    }>;
  };
}

interface JobAppDTO {
  id: number;
  company: string;
  role: string;
  track: string;
  source: string | null;
  status: string;
  salary_range: string | null;
  applied_at: string | null;
  next_action: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/* ───────────────────────── 适配函数 ───────────────────────── */

function toApp(dto: JobAppDTO): JobApplication {
  return {
    id: String(dto.id),
    company: dto.company,
    role: dto.role,
    track: dto.track,
    source: dto.source,
    status: dto.status as JobAppStatus,
    salaryRange: dto.salary_range,
    appliedAt: dto.applied_at,
    nextAction: dto.next_action,
    notes: dto.notes,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toBoard(dto: JobHuntDTO): JobHuntBoard {
  return {
    career: dto.career
      ? {
          targetRole: dto.career.target_role,
          salaryTarget: dto.career.salary_target,
          timeframe: dto.career.timeframe,
          notes: dto.career.notes,
        }
      : null,
    offerDeadline: dto.offer_deadline,
    daysLeft: dto.days_left,
    targetRoles: dto.target_roles.map((r) => ({
      key: r.key,
      name: r.name,
      priority: r.priority as "主攻" | "卡位" | "保底" | "暂缓",
      salaryRange: r.salary_range,
      note: r.note,
      matchPct: r.match_pct,
      strictPct: r.strict_pct,
      qualifiedCount: r.qualified_count,
      requiredCount: r.required_count,
      frozen: r.frozen ?? false,
      skills: r.skills.map((s) => ({
        name: s.name,
        level: s.level,
        required: s.required,
        gap: s.gap,
        missing: s.missing,
      })),
    })),
    skillGaps: dto.skill_gaps.map((g) => ({
      name: g.name,
      category: g.category,
      level: g.level,
      targetLevel: g.target_level,
      gap: g.gap,
      evidence: g.evidence ?? [],
    })),
    jobProject: dto.job_project
      ? {
          id: dto.job_project.id != null ? String(dto.job_project.id) : null,
          name: dto.job_project.name,
          currentVersion: dto.job_project.current_version,
          milestones: dto.job_project.milestones.map((m) => ({
            id: String(m.id),
            version: m.version,
            title: m.title,
            goal: m.goal,
            status: m.status,
            sortOrder: m.sort_order,
          })),
          milestoneTotal: dto.job_project.milestone_total,
          milestoneCompleted: dto.job_project.milestone_completed,
        }
      : null,
    tasks: {
      total: dto.tasks.total,
      done: dto.tasks.done,
      doing: dto.tasks.doing,
      todo: dto.tasks.todo,
      frozenExcluded: dto.tasks.frozen_excluded ?? 0,
      unclassified: dto.tasks.unclassified ?? 0,
      items: dto.tasks.items.map(
        (t): JobTaskItem => ({
          id: String(t.id),
          title: t.title,
          skillName: t.skill_name,
          status: t.status,
          duration: t.duration,
          objective: t.objective,
          trackKey: t.track_key ?? null,
          scope: (t.scope as TaskTrackScope | undefined) ?? undefined,
        })
      ),
      frozenItems: (dto.tasks.frozen_items ?? []).map(toScopedTaskRef),
      // 老后端（Milestone A 及更早）没有 scope 字段：回落到"未限缩"的空口径，
      // 而不是抛错或猜一个 —— 页面表现为"没有口径提示"，与改造前一致。
      scope: toScopeSummary(dto.tasks.scope, dto.tasks.frozen_excluded ?? 0),
    },
    applications: {
      total: dto.applications.total,
      byStatus: dto.applications.by_status as Record<JobAppStatus, number>,
      responseRate: dto.applications.response_rate,
      items: dto.applications.items.map(toApp),
    },
    jobPool: dto.job_pool
      ? {
          total: dto.job_pool.total,
          byGrade: dto.job_pool.by_grade as Record<MatchGrade, number>,
          recommended: dto.job_pool.recommended,
          top: dto.job_pool.top.map((t) => ({
            id: String(t.id),
            company: t.company,
            title: t.title,
            track: t.track,
            tier: t.tier as PostingTier,
            matchScore: t.match_score,
            grade: t.grade as MatchGrade,
          })),
        }
      : undefined,
  };
}

/* ───────────────────────── 求职看板 ───────────────────────── */

/** 获取求职看板聚合数据。 */
export async function getJobHuntBoard(): Promise<JobHuntBoard> {
  const dto = await apiClient.get<JobHuntDTO>("/api/job-hunt");
  return toBoard(dto);
}

/* ───────────────────────── 投递记录 CRUD ───────────────────────── */

/** 获取全部投递记录。 */
export async function listApplications(): Promise<JobApplication[]> {
  const dtos = await apiClient.get<JobAppDTO[]>("/api/job-applications");
  return dtos.map(toApp);
}

/** 新增投递记录。 */
export async function createApplication(
  payload: JobApplicationCreate
): Promise<JobApplication> {
  const dto = await apiClient.post<JobAppDTO>("/api/job-applications", payload);
  return toApp(dto);
}

/** 更新投递记录（状态流转 / 下一步 / 备注）。 */
export async function updateApplication(
  id: string,
  patch: Partial<JobApplicationCreate>
): Promise<JobApplication> {
  const dto = await apiClient.patch<JobAppDTO>(
    `/api/job-applications/${id}`,
    patch
  );
  return toApp(dto);
}

/** 删除投递记录。 */
export async function deleteApplication(id: string): Promise<void> {
  await apiClient.delete<void>(`/api/job-applications/${id}`);
}
