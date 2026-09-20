/** 任务赛道口径（Task Scope）的前端适配层 —— 两个 service 共用的唯一一份转换。
 *
 * 为什么单独一个文件：
 *   `/api/job-hunt` 与 `/api/plan/today` 返回的是**同一个**口径字段
 *   （后端 services/action_planning/task_scope.py 是唯一权威实现）。如果两个
 *   service 各写一遍 snake_case → camelCase 的映射，两边就会各自漂移：加了
 *   一个字段只改了一处、默认值取得不一样、可选字段的名字拼错一个字母 ——
 *   这类"同一份数据两种前端形状"的问题最难查。
 *
 * 本文件只做**形状转换**，不含任何业务判断：
 *   分类（active / frozen / unclassified）由后端给出，前端只搬不推。
 *   前端任何地方都不许用 trackKey 自己算"这条该不该显示"。
 */

import type { ScopedTaskRef, TaskScopeSummary, TaskTrackScope } from "@/types";

/** 后端 scope 段原始结构（两个端点的该字段形状一致）。 */
export interface TaskScopeDTO {
  mode_key: string;
  mode_name: string;
  is_track_scoped: boolean;
  active_track_keys: string[];
  frozen_track_keys: string[];
  scope_reason: string;
  included: number;
  frozen_excluded: number;
  unclassified: number;
}

/** 后端"被排除任务"原始结构。 */
export interface ScopedTaskRefDTO {
  id: number;
  title: string;
  track_key: string | null;
  status: string;
  scope: string;
}

/** 把后端口径转成前端类型。
 *
 * `dto` 缺省时（旧后端没有该字段）回落到"未限缩"的空口径：页面表现为没有口径
 * 提示，与改造前一致 —— 不抛错、不猜一个假口径，也不让老板本直接白屏。
 */
export function toScopeSummary(
  dto: TaskScopeDTO | null | undefined,
  frozenExcludedFallback = 0
): TaskScopeSummary {
  return {
    modeKey: dto?.mode_key ?? "",
    modeName: dto?.mode_name ?? "",
    isTrackScoped: dto?.is_track_scoped ?? false,
    activeTrackKeys: dto?.active_track_keys ?? [],
    frozenTrackKeys: dto?.frozen_track_keys ?? [],
    scopeReason: dto?.scope_reason ?? "",
    included: dto?.included ?? 0,
    frozenExcluded: dto?.frozen_excluded ?? frozenExcludedFallback,
    unclassified: dto?.unclassified ?? 0,
  };
}

/** 把后端"被排除任务"转成前端类型。 */
export function toScopedTaskRef(dto: ScopedTaskRefDTO): ScopedTaskRef {
  return {
    id: String(dto.id),
    title: dto.title,
    trackKey: dto.track_key,
    status: dto.status,
    scope: dto.scope as TaskTrackScope,
  };
}
