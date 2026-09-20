/** 职业阶段模式服务层（Milestone A：模式骨架）。
 *
 * 职责：
 * - getCareerModeOverview()：拉 /api/career-mode，做 snake_case → camelCase 适配
 * - switchCareerMode()：切 /api/career-mode/switch，同样统一适配
 *
 * 与 jobHuntService / taskService 保持同一取向：DTO 到领域模型的转换只在这里
 * 发生一次，组件只读 camelCase 的 CareerMode 类型，不感知后端字段形状。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  CareerMode,
  CareerModeKey,
  CareerModeOverview,
  CareerModeSwitchResult,
  CareerModeTransition,
} from "@/types";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface CareerModeDTO {
  id: number;
  key: string;
  name: string;
  objective: string;
  deadline: string | null;
  days_left: number | null;
  active_track_keys: string[];
  frozen_track_keys: string[];
  is_current: boolean;
}

interface ModeTransitionDTO {
  id: number;
  from_mode: string | null;
  to_mode: string;
  transitioned_at: string;
  note: string | null;
}

interface CareerModeOverviewDTO {
  current: CareerModeDTO;
  available: CareerModeDTO[];
}

interface CareerModeSwitchResultDTO {
  current: CareerModeDTO;
  transition: ModeTransitionDTO;
}

/* ───────────────────────── 适配函数 ───────────────────────── */

function toCareerMode(dto: CareerModeDTO): CareerMode {
  return {
    id: String(dto.id),
    key: dto.key as CareerModeKey,
    name: dto.name,
    objective: dto.objective,
    deadline: dto.deadline,
    daysLeft: dto.days_left,
    // 防御：字段缺失时给空数组，避免里程碑 B 之前的旧后端让页面崩在 .map()
    activeTrackKeys: dto.active_track_keys ?? [],
    frozenTrackKeys: dto.frozen_track_keys ?? [],
    isCurrent: dto.is_current,
  };
}

function toCareerModeTransition(dto: ModeTransitionDTO): CareerModeTransition {
  return {
    id: String(dto.id),
    fromMode: dto.from_mode,
    toMode: dto.to_mode,
    transitionedAt: dto.transitioned_at,
    note: dto.note,
  };
}

/* ───────────────────────── 对外接口 ───────────────────────── */

/** 读取当前模式与全部可选模式。 */
export async function getCareerModeOverview(): Promise<CareerModeOverview> {
  const dto = await apiClient.get<CareerModeOverviewDTO>("/api/career-mode");
  return {
    current: toCareerMode(dto.current),
    available: dto.available.map(toCareerMode),
  };
}

/** 切换当前模式。
 *
 * note 是可选的切换原因，会记入后端切换历史（PRD §5 F1.4）。
 * 切换只改变阶段与默认口径，不会删除、修改或隐藏任何既有业务数据。
 */
export async function switchCareerMode(
  modeKey: string,
  note?: string | null
): Promise<CareerModeSwitchResult> {
  const dto = await apiClient.post<CareerModeSwitchResultDTO>(
    "/api/career-mode/switch",
    { mode_key: modeKey, note: note ?? null }
  );
  return {
    current: toCareerMode(dto.current),
    transition: toCareerModeTransition(dto.transition),
  };
}
