/** 求职包装服务层（P4）。
 *
 * 职责：封装 README 骨架生成 / 保存 与「简历技能行（附证据）」接口，
 * 并把后端 snake_case 适配为前端 camelCase 类型。
 *
 * ⚠️ apiClient 不做 key 转换 —— 发出去的 body 必须显式写好后端要的字段名，
 * 否则会被 Pydantic 当未知字段静默丢弃。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  ProjectReadme,
  SkillEvidenceItem,
  SkillLine,
  SkillLinePending,
  SkillLineReport,
} from "@/types";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface ReadmeCountsDTO {
  milestones: number;
  skills: number;
  skills_with_evidence: number;
  experiments: number;
  chars: number;
}

interface ProjectReadmeDTO {
  project_id: number;
  name: string;
  saved_readme: string | null;
  draft: string;
  counts: ReadmeCountsDTO;
}

interface SaveReadmeDTO {
  project_id: number;
  saved_readme: string;
  chars: number;
}

interface SkillLineDTO {
  skill: string;
  level: number;
  category: string | null;
  gate_level: number;
  line: string;
  refs: SkillEvidenceItem[];
}

interface SkillLinePendingDTO {
  skill: string;
  level: number;
  category: string | null;
  gate_level: number;
  missing: string;
}

interface SkillLineReportDTO {
  ready: SkillLineDTO[];
  pending: SkillLinePendingDTO[];
  summary: {
    total: number;
    ready: number;
    pending: number;
    pending_min_level: number;
  };
  note: string;
}

/* ───────────────────────── 适配 ───────────────────────── */

function toProjectReadme(dto: ProjectReadmeDTO): ProjectReadme {
  return {
    projectId: String(dto.project_id),
    name: dto.name,
    savedReadme: dto.saved_readme,
    draft: dto.draft,
    counts: {
      milestones: dto.counts?.milestones ?? 0,
      skills: dto.counts?.skills ?? 0,
      skillsWithEvidence: dto.counts?.skills_with_evidence ?? 0,
      experiments: dto.counts?.experiments ?? 0,
      chars: dto.counts?.chars ?? 0,
    },
  };
}

function toSkillLine(dto: SkillLineDTO): SkillLine {
  return {
    skill: dto.skill,
    level: dto.level,
    category: dto.category,
    gateLevel: dto.gate_level,
    line: dto.line,
    refs: dto.refs || [],
  };
}

function toPending(dto: SkillLinePendingDTO): SkillLinePending {
  return {
    skill: dto.skill,
    level: dto.level,
    category: dto.category,
    gateLevel: dto.gate_level,
    missing: dto.missing,
  };
}

function toSkillLineReport(dto: SkillLineReportDTO): SkillLineReport {
  return {
    ready: (dto.ready || []).map(toSkillLine),
    pending: (dto.pending || []).map(toPending),
    summary: {
      total: dto.summary?.total ?? 0,
      ready: dto.summary?.ready ?? 0,
      pending: dto.summary?.pending ?? 0,
      pendingMinLevel: dto.summary?.pending_min_level ?? 3,
    },
    note: dto.note || "",
  };
}

/* ───────────────────────── API ───────────────────────── */

/** 生成（预览）项目 README 骨架 —— 不落库。 */
export async function getProjectReadme(id: string): Promise<ProjectReadme> {
  const dto = await apiClient.get<ProjectReadmeDTO>(`/api/projects/${id}/readme`);
  return toProjectReadme(dto);
}

/** 保存 README。不传 content 时用证据链重新生成（一键导出）。 */
export async function saveProjectReadme(
  id: string,
  content?: string
): Promise<{ savedReadme: string; chars: number }> {
  const dto = await apiClient.post<SaveReadmeDTO>(`/api/projects/${id}/readme`, {
    content: content ?? null,
  });
  return { savedReadme: dto.saved_readme, chars: dto.chars };
}

/** 简历技能行（附证据）。 */
export async function getSkillLines(): Promise<SkillLineReport> {
  const dto = await apiClient.get<SkillLineReportDTO>("/api/resume/skill-lines");
  return toSkillLineReport(dto);
}
