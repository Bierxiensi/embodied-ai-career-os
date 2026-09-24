/** 学习日志服务层（今日施工单的"内容位"）。
 *
 * 对应后端 /api/learning-logs 系列端点（⚠️ 路由是**连字符**，不是下划线）：
 *   GET  /api/learning-logs          列表（可选 ?task_id= 过滤，按 created_at 倒序）
 *   POST /api/learning-logs          创建（content 必填 1-2000；duration 1-480；artifact_url ≤500）
 *
 * 注意：后端**不提供 DELETE**（历史日志是 Reviewer 的决策依据，同 Task 的设计）。
 *
 * 🔴 时间戳陷阱：后端 `created_at` 是 **naive UTC**（`datetime.utcnow()`，串里没有时区后缀），
 *    形如 `2026-09-10T07:07:20.815959`。JS 的 `new Date()` 会把**无后缀的 ISO 串当本地时间**解析，
 *    上海时区下会差 8 小时（凌晨写的日志会被算到前一天）。
 *    故这里统一补 `Z`，下游可直接 `new Date(log.createdAt)`。
 */

import { apiClient } from "@/lib/apiClient";
import type { LearningLog } from "@/types";

/** 后端原始结构。 */
interface LearningLogDTO {
  id: number;
  task_id: number | null;
  content: string;
  duration_minutes: number | null;
  artifact_url: string | null;
  created_at: string;
}

/** 把 naive UTC 串补成带 Z 的合法 UTC ISO 串（已是带时区的则原样返回）。 */
function normalizeUtc(iso: string): string {
  return /[Zz]$|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`;
}

function toLearningLog(d: LearningLogDTO): LearningLog {
  return {
    id: String(d.id),
    taskId: d.task_id === null ? null : String(d.task_id),
    content: d.content,
    durationMinutes: d.duration_minutes,
    artifactUrl: d.artifact_url ?? null,
    createdAt: normalizeUtc(d.created_at),
  };
}

/** 获取学习日志列表（按时间倒序）。 */
export async function listLearningLogs(taskId?: string): Promise<LearningLog[]> {
  const qs = taskId !== undefined ? `?task_id=${taskId}` : "";
  const dtos = await apiClient.get<LearningLogDTO[]>(`/api/learning-logs${qs}`);
  return dtos.map(toLearningLog);
}

/** 创建一条学习日志。 */
export async function createLearningLog(payload: {
  content: string;
  durationMinutes?: number | null;
  artifactUrl?: string | null;
  taskId?: string | null;
}): Promise<LearningLog> {
  const dto = await apiClient.post<LearningLogDTO>("/api/learning-logs", {
    // 显式列 snake_case：apiClient 不做 key 转换
    task_id: payload.taskId ? Number(payload.taskId) : null,
    content: payload.content,
    duration_minutes: payload.durationMinutes ?? null,
    artifact_url: payload.artifactUrl ?? null,
  });
  return toLearningLog(dto);
}

/** 判断一条日志是否属于"今天"（按**浏览器本地日历日**比较）。
 *
 * 因为 createdAt 已在 service 层补过 Z，这里 `new Date()` 得到的是正确的本地时刻，
 * 再比 local 年月日 —— 避免用 ISO 串做字符串前缀比较（那是 UTC 日期，会错 8 小时）。
 */
export function isToday(log: LearningLog, now: Date = new Date()): boolean {
  const d = new Date(log.createdAt);
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}
