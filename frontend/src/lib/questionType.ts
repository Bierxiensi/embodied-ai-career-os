/**
 * 题型展示名的唯一真源。
 *
 * 后端按 ``question_type``（open / choice / judge / fill）聚合，
 * 前端多处要把它翻成中文（学情卡、测验结果）。放在这里避免各写一份而漂移。
 */

import type { QuestionType } from "@/types";

export const QUESTION_TYPE_LABEL: Record<QuestionType, string> = {
  open: "简答",
  choice: "选择",
  judge: "判断",
  fill: "填空",
};

/**
 * 取题型中文名。
 *
 * 入参放宽为 string：聚合结果是 ``Record<string, ...>``，key 由后端决定，
 * 出现未知题型时原样返回，别把界面搞成空白。
 */
export function questionTypeLabel(key: string): string {
  return QUESTION_TYPE_LABEL[key as QuestionType] ?? key;
}
