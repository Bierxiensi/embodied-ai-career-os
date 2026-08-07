/** Skill 服务层。
 *
 * 职责：调用后端 /api/skills，做字段适配。
 * 雷达图核心 8 维在此过滤（排除 Frontend/Web Engineering 已达成优势）。
 */

import { apiClient } from "@/lib/apiClient";
import type { Skill } from "@/types";

/** 后端 Skill 响应原始结构。 */
interface SkillDTO {
  id: number;
  name: string;
  category: string | null;
  level: number;
  target_level: number;
  evidence: string[];
}

function toSkill(dto: SkillDTO): Skill {
  return {
    id: String(dto.id),
    name: dto.name,
    category: dto.category ?? "Medium",
    level: dto.level,
    targetLevel: dto.target_level,
    evidence: dto.evidence ?? [],
  };
}

/** 获取全部技能（SkillCard 用）。 */
export async function getSkills(): Promise<Skill[]> {
  const dtos = await apiClient.get<SkillDTO[]>("/api/skills");
  return dtos.map(toSkill);
}

/** 雷达图排除的已达成优势技能（避免淹没转型缺口）。 */
const EXCLUDE_FROM_RADAR = new Set(["Frontend", "Web Engineering"]);

/** 纯函数：从全部技能中过滤出雷达图核心维度。
 *
 * 导出供 dashboardService 复用，避免重复请求后端。
 */
export function filterRadarSkills(all: Skill[]): Skill[] {
  return all.filter((s) => !EXCLUDE_FROM_RADAR.has(s.name));
}

/** 获取雷达图核心 8 维技能（独立请求场景使用）。 */
export async function getRadarSkills(): Promise<Skill[]> {
  const all = await getSkills();
  return filterRadarSkills(all);
}
