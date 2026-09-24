/** 知识库（论文 RAG）服务层。
 *
 * 对应后端 /api/paper 系列端点：
 *   GET  /api/paper/stats    知识库统计（论文数 / chunk 数 / 索引覆盖率 / 嵌入模型）
 *   GET  /api/paper/search   语义检索。⚠️ 参数名是 `query`（不是 q！），响应形状是 data.hits[]
 *   POST /api/paper/ask      问答（LLM 成句回答 + 引用；LLM 不可用时回落片段拼接）
 *
 * 与其它 service 同一套约定：后端 snake_case → 前端 camelCase，int id → string id。
 * 口径（模型名、覆盖率、置信度）一律透传后端值，前端不重算、不加工。
 */

import { apiClient } from "@/lib/apiClient";
import type { KnowledgeAnswer, KnowledgeCitation, KnowledgeStats } from "@/types";

/** 后端统计原始结构。 */
interface StatsDTO {
  paper_count: number;
  chunk_count: number;
  indexed_chunk_count: number;
  model_name: string;
  coverage: number;
}

/** 后端 citation 原始结构。 */
interface CitationDTO {
  chunk_id: string;
  paper_id: string;
  paper_title: string;
  section: string;
  page: number;
  score: number;
  text: string;
}

/** 后端检索响应原始结构（注意是对象，命中在 hits 字段里）。 */
interface SearchResultDTO {
  query: string;
  top_k: number;
  section: string | null;
  model_name: string;
  hits: CitationDTO[];
}

/** 后端问答响应原始结构。 */
interface AskDTO {
  question: string;
  answer: string;
  citations: CitationDTO[];
  confidence: string;
  model_name: string;
  hit_count: number;
  /** 后端追加字段；老响应可能没有，故给默认值 */
  answer_mode?: string;
}

function toStats(d: StatsDTO): KnowledgeStats {
  return {
    paperCount: d.paper_count ?? 0,
    chunkCount: d.chunk_count ?? 0,
    indexedChunkCount: d.indexed_chunk_count ?? 0,
    modelName: d.model_name ?? "",
    coverage: d.coverage ?? 0,
  };
}

function toCitation(d: CitationDTO): KnowledgeCitation {
  return {
    chunkId: d.chunk_id,
    paperId: d.paper_id,
    paperTitle: d.paper_title ?? "",
    section: d.section ?? "unknown",
    page: d.page ?? 1,
    score: d.score ?? 0,
    text: d.text ?? "",
  };
}

/** 知识库统计。 */
export async function getKnowledgeStats(): Promise<KnowledgeStats> {
  const dto = await apiClient.get<StatsDTO>("/api/paper/stats");
  return toStats(dto);
}

/** 语义检索。返回按相似度降序的命中列表。 */
export async function searchKnowledge(
  query: string,
  topK = 5
): Promise<KnowledgeCitation[]> {
  const qs = `?query=${encodeURIComponent(query)}&top_k=${topK}`;
  const dto = await apiClient.get<SearchResultDTO>(`/api/paper/search${qs}`);
  return (dto.hits ?? []).map(toCitation);
}

/** 知识库问答。 */
export async function askKnowledge(
  question: string,
  opts?: { topK?: number; section?: string }
): Promise<KnowledgeAnswer> {
  const dto = await apiClient.post<AskDTO>("/api/paper/ask", {
    question,
    top_k: opts?.topK ?? 5,
    section: opts?.section ?? null,
  });
  return {
    question: dto.question,
    answer: dto.answer ?? "",
    citations: (dto.citations ?? []).map(toCitation),
    confidence: dto.confidence ?? "low",
    modelName: dto.model_name ?? "",
    hitCount: dto.hit_count ?? 0,
    answerMode: dto.answer_mode ?? "rule",
  };
}
