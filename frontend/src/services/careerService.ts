/** Career 服务层。
 *
 * 职责：调用后端 /api/career，做 snake_case→camelCase 适配。
 * 组件只消费前端 Career 类型，不感知后端字段命名。
 */

import { apiClient } from "@/lib/apiClient";
import type { Career } from "@/types";

/** 后端 Career 响应原始结构（snake_case）。 */
interface CareerDTO {
  id: number;
  target_role: string;
  salary_target: number | null;
  timeframe: string | null;
  notes: string | null;
}

/** 后端 → 前端转换。progress 暂用固定值（Day7 由 Reviewer 计算）。 */
function toCareer(dto: CareerDTO): Career {
  return {
    id: String(dto.id),
    targetRole: dto.target_role,
    salaryTarget: dto.salary_target ?? 0,
    timeframe: dto.timeframe ?? "",
    progress: 35, // TODO Day7: 由 Reviewer Agent 根据 skills 计算真实进度
  };
}

export async function getCareer(): Promise<Career> {
  const dto = await apiClient.get<CareerDTO>("/api/career");
  return toCareer(dto);
}
