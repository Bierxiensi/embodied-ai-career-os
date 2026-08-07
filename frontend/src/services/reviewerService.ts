/** Reviewer 服务层。
 *
 * Day7 闭环核心：调用 POST /api/reviewer/review，一次请求完成
 * Task→done + LearningLog + Reviewer Agent + Skill Update。
 *
 * 后端返回 snake_case，此处转换为前端 camelCase 类型。
 */

import { apiClient } from "@/lib/apiClient";
import type { ReviewerResult, SkillAssessment } from "@/types";

/** 后端 ReviewerResult 原始结构（snake_case）。 */
interface ReviewerResultDTO {
  task: {
    id: number;
    title: string;
    skill_name: string | null;
    status: string;
  };
  learning_log: {
    id: number;
    task_id: number | null;
    content: string;
    duration_minutes: number | null;
    artifact_url: string | null;
    created_at: string;
  };
  assessment: {
    id: number;
    skill_id: number;
    task_id: number | null;
    old_level: number;
    new_level: number;
    confidence: number;
    reason: string;
    evidence_score: number;
    created_at: string;
  };
  updated_skill: {
    id: number;
    name: string;
    level: number;
    target_level: number;
    evidence: string[];
  };
}

/** 后端 → 前端转换。 */
function toReviewerResult(dto: ReviewerResultDTO): ReviewerResult {
  return {
    task: {
      id: dto.task.id,
      title: dto.task.title,
      skillName: dto.task.skill_name,
      status: dto.task.status,
    },
    learningLog: {
      id: String(dto.learning_log.id),
      taskId: dto.learning_log.task_id ? String(dto.learning_log.task_id) : null,
      content: dto.learning_log.content,
      durationMinutes: dto.learning_log.duration_minutes,
      artifactUrl: dto.learning_log.artifact_url,
      createdAt: dto.learning_log.created_at,
    },
    assessment: {
      id: String(dto.assessment.id),
      skillId: String(dto.assessment.skill_id),
      taskId: dto.assessment.task_id ? String(dto.assessment.task_id) : null,
      oldLevel: dto.assessment.old_level,
      newLevel: dto.assessment.new_level,
      confidence: dto.assessment.confidence,
      reason: dto.assessment.reason,
      evidenceScore: dto.assessment.evidence_score,
      createdAt: dto.assessment.created_at,
    },
    updatedSkill: {
      id: dto.updated_skill.id,
      name: dto.updated_skill.name,
      level: dto.updated_skill.level,
      targetLevel: dto.updated_skill.target_level,
      evidence: dto.updated_skill.evidence,
    },
  };
}

/** Reviewer 请求参数。 */
export interface ReviewTaskParams {
  taskId: string;
  content: string;
  durationMinutes?: number;
  artifactUrl?: string;
}

/** 提交任务复盘。
 *
 * 一次请求完成全链路：Task→done + LearningLog + Reviewer + Skill Update。
 * 成功后调用方应 router.refresh() 刷新 Dashboard。
 */
export async function reviewTask(
  params: ReviewTaskParams
): Promise<ReviewerResult> {
  const dto = await apiClient.post<ReviewerResultDTO>(
    "/api/reviewer/review",
    {
      task_id: Number(params.taskId),
      content: params.content,
      duration_minutes: params.durationMinutes ?? null,
      artifact_url: params.artifactUrl ?? null,
    }
  );
  return toReviewerResult(dto);
}

/** 导出 SkillAssessment 类型供组件使用。 */
export type { SkillAssessment };
