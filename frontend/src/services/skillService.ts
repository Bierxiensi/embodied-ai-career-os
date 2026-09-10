/** Skill 服务层。
 *
 * 职责：调用后端 /api/skills，做字段适配。
 *
 * 注：雷达轴已不再在此过滤 —— 原先"全量技能减 2 项"会得到 46 条轴，标签互相压叠且
 * 混入已冻结的具身技能，形状无语义。现改为由「主攻赛道」的 required_skills 提供
 * 6–8 条轴，见 `dashboardService.computeRadar`。
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

/** 获取全部技能（技能图谱明细 + Planner 输入）。 */
export async function getSkills(): Promise<Skill[]> {
  const dtos = await apiClient.get<SkillDTO[]>("/api/skills");
  return dtos.map(toSkill);
}

