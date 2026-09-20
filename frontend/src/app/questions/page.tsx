/** 题库页面（Server Component）。 */

import QuestionBoard from "@/components/QuestionBoard";
import PageShell from "@/ui/page-shell";
import ErrorCard from "@/ui/error-card";
import { getQuestionCoverage, listQuestions } from "@/services/interviewService";

export const dynamic = "force-dynamic";

export default async function QuestionsPage() {
  try {
    const [questions, coverage] = await Promise.all([
      listQuestions(),
      getQuestionCoverage(),
    ]);

    return (
      <PageShell
        eyebrow="QUESTIONS · 题库生长"
        title="题库与覆盖率"
        subtitle="每天完成任务顺手录题：红格把「缺口在哪」直接显示出来，后期只做查缺补漏。"
      >
        <QuestionBoard initialQuestions={questions} initialCoverage={coverage} />
      </PageShell>
    );
  } catch (err) {
    return <ErrorCard pageName="题库页" error={err} />;
  }
}
