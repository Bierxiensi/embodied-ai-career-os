/** Skill 服务层。
 *
 * 职责：调用后端 /api/skills 系列，做字段适配（snake_case → camelCase）。
 *
 * 雷达轴的两条来路（Phase 3）：
 *  - R1 岗位对齐（job_hunt 模式）：轴 = 主攻赛道的 required_skills，
 *    数据来自 `/api/job-hunt` 的 target_roles，在 `dashboardService` 里适配。
 *  - R2 域聚合（long_term_transition 模式）：轴 = 六域，
 *    数据来自本文件的 `getSkillDomains()`。
 *
 * 注：雷达轴已不再在此过滤全量技能 —— 原先"全量技能减 2 项"会得到 46 条轴，
 * 标签互相压叠且混入已冻结的具身技能，形状无语义。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  Skill,
  SkillDomainGap,
  SkillDomainKey,
  SkillDomainOverview,
  SkillGraph,
  SkillGraphEdge,
  SkillGraphNode,
  SkillPrereq,
} from "@/types";

/** 后端 Skill 响应原始结构。 */
interface SkillDTO {
  id: number;
  name: string;
  category: string | null;
  level: number;
  target_level: number;
  evidence: string[];
  /** Phase 3：六域 key；null = 不在六域内（冻结 / 历史旁证） */
  domain?: SkillDomainKey | null;
  domain_label?: string | null;
}

function toSkill(dto: SkillDTO): Skill {
  return {
    id: String(dto.id),
    name: dto.name,
    category: dto.category ?? "Medium",
    level: dto.level,
    targetLevel: dto.target_level,
    evidence: dto.evidence ?? [],
    domain: dto.domain ?? null,
    domainLabel: dto.domain_label ?? null,
  };
}

/** 获取全部技能（技能图谱明细 + Planner 输入）。 */
export async function getSkills(): Promise<Skill[]> {
  const dtos = await apiClient.get<SkillDTO[]>("/api/skills");
  return dtos.map(toSkill);
}

/* ───────────────────────── Phase 3：六域聚合（R2 雷达） ───────────────────────── */

interface SkillPrereqDTO {
  name: string;
  level: number | null;
  met: boolean;
  note?: string | null;
}

interface SkillDomainGapDTO {
  name: string;
  level: number;
  target_level: number;
  gap: number;
  prerequisites: SkillPrereqDTO[];
}

interface SkillDomainDTO {
  key: SkillDomainKey;
  label: string;
  skill_count: number;
  current_avg: number;
  target_avg: number;
  gap_avg: number;
  gap_skills: SkillDomainGapDTO[];
}

interface SkillDomainOverviewDTO {
  domains: SkillDomainDTO[];
  mapped_count: number;
  unmapped_count: number;
  unmapped_names: string[];
  prereq_satisfied_level: number;
}

function toPrereq(dto: SkillPrereqDTO): SkillPrereq {
  return {
    name: dto.name,
    level: dto.level ?? null,
    met: dto.met,
    note: dto.note ?? null,
  };
}

function toDomainGap(dto: SkillDomainGapDTO): SkillDomainGap {
  return {
    name: dto.name,
    level: dto.level,
    targetLevel: dto.target_level,
    gap: dto.gap,
    prerequisites: (dto.prerequisites ?? []).map(toPrereq),
  };
}

/** 六域聚合（long_term_transition 模式下技能雷达的数据源）。 */
export async function getSkillDomains(): Promise<SkillDomainOverview> {
  const dto = await apiClient.get<SkillDomainOverviewDTO>("/api/skills/domains");
  return {
    domains: (dto.domains ?? []).map((d) => ({
      key: d.key,
      label: d.label,
      skillCount: d.skill_count,
      currentAvg: d.current_avg,
      targetAvg: d.target_avg,
      gapAvg: d.gap_avg,
      gapSkills: (d.gap_skills ?? []).map(toDomainGap),
    })),
    mappedCount: dto.mapped_count,
    unmappedCount: dto.unmapped_count,
    unmappedNames: dto.unmapped_names ?? [],
    prereqSatisfiedLevel: dto.prereq_satisfied_level,
  };
}

/* ───────────────────────── Phase 3：依赖图 ───────────────────────── */

interface SkillGraphNodeDTO {
  name: string;
  domain: SkillDomainKey | null;
  domain_label: string | null;
  level: number | null;
  target_level: number | null;
  frozen: boolean;
}

interface SkillGraphEdgeDTO {
  prerequisite: string;
  dependent: string;
  note?: string | null;
}

interface SkillGraphDTO {
  nodes: SkillGraphNodeDTO[];
  edges: SkillGraphEdgeDTO[];
  prereq_satisfied_level: number;
}

function toGraphNode(dto: SkillGraphNodeDTO): SkillGraphNode {
  return {
    name: dto.name,
    domain: dto.domain ?? null,
    domainLabel: dto.domain_label ?? null,
    level: dto.level ?? null,
    targetLevel: dto.target_level ?? null,
    frozen: dto.frozen,
  };
}

/** 技能依赖图（先修 → 后继）。当前主要用于 R2 卡片的"先修"标注。 */
export async function getSkillGraph(): Promise<SkillGraph> {
  const dto = await apiClient.get<SkillGraphDTO>("/api/skills/graph");
  return {
    nodes: (dto.nodes ?? []).map(toGraphNode),
    edges: (dto.edges ?? []).map(
      (e): SkillGraphEdge => ({
        prerequisite: e.prerequisite,
        dependent: e.dependent,
        note: e.note ?? null,
      })
    ),
    prereqSatisfiedLevel: dto.prereq_satisfied_level,
  };
}
