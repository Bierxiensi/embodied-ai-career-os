/** Agent 服务层。
 *
 * Phase 2 Week 1 Day 6：Dashboard Agent Activity 面板数据来源。
 *
 * 职责：
 * - 调用后端 GET /api/agent/runs，获取 Agent 执行历史
 * - snake_case → camelCase 字段适配
 * - 组件层只消费 AgentActivity 类型，不感知后端字段命名
 */

import { apiClient } from "@/lib/apiClient";
import type { AgentActivity, AgentRunRecord } from "@/types";

/** 后端 AgentRunRecord 响应原始结构（snake_case）。 */
interface AgentRunRecordDTO {
  id: string;
  agent_name: string;
  status: string;
  duration_ms: number;
  trace_id: string | null;
  created_at: string;
  output_summary: string;
  input_context: Record<string, unknown>;
  output_result: Record<string, unknown>;
}

/** 后端 AgentActivity 响应原始结构。 */
interface AgentActivityDTO {
  total: number;
  runs: AgentRunRecordDTO[];
}

/** 后端 → 前端转换：snake_case → camelCase。 */
function toAgentRunRecord(dto: AgentRunRecordDTO): AgentRunRecord {
  return {
    id: dto.id,
    agentName: dto.agent_name,
    status: dto.status,
    durationMs: dto.duration_ms,
    traceId: dto.trace_id,
    createdAt: dto.created_at,
    outputSummary: dto.output_summary,
    inputContext: dto.input_context,
    outputResult: dto.output_result,
  };
}

/** 获取 Agent 执行历史。
 *
 * @param agentName 可选，按 Agent 名称过滤
 * @param limit 返回记录数，默认 20
 */
export async function getAgentRuns(
  agentName?: string,
  limit: number = 20
): Promise<AgentActivity> {
  const params = new URLSearchParams();
  if (agentName) params.set("agent_name", agentName);
  params.set("limit", String(limit));

  const dto = await apiClient.get<AgentActivityDTO>(
    `/api/agent/runs?${params.toString()}`
  );

  return {
    total: dto.total,
    runs: dto.runs.map(toAgentRunRecord),
  };
}
