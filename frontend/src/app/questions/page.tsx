/** 题库页面（Server Component）。
 *
 * 定位（2026-09-22 用户裁决）：留任之后题库**不再作为求职 KPI**，
 * 只作"需要时拿出来练手、检验学习效果"的存档 —— 所以页面主体是
 * 「我的练习（正确率 / 薄弱点）」而不是「离目标还差多少题」。
 */

import QuestionBoard from "@/components/QuestionBoard";
import PageShell from "@/ui/page-shell";
import ErrorCard from "@/ui/error-card";
import {
  getPracticeStats,
  getQuestionCoverage,
  listQuestions,
} from "@/services/interviewService";

export const dynamic = "force-dynamic";

export default async function QuestionsPage() {
  try {
    const [questions, coverage, stats] = await Promise.all([
      listQuestions(),
      getQuestionCoverage(),
      getPracticeStats(),
    ]);

    return (
      <PageShell
        eyebrow="QUESTIONS · 题库存档"
        title="题库与自测"
        subtitle="题库不再按目标题数考核。它是一份存档：需要时抽题练手，用正确率和薄弱点看自己学得怎么样。"
      >
        <QuestionBoard
          initialQuestions={questions}
          initialCoverage={coverage}
          initialStats={stats}
        />
      </PageShell>
    );
  } catch (err) {
    return <ErrorCard pageName="题库页" error={err} />;
  }
}
