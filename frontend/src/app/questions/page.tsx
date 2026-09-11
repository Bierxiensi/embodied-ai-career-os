/** 题库页面（Server Component · P3 题库生长）。

 * 对应 docs/platform-direction-30day.md 决策 5「题库要按天生长」与 P3 验收：
 * 「每天录题 ≤ 1 分钟；Day 26 看到的是『缺口在哪』而不是『从零开始』」。
 *
 * 数据流：
 *   page.tsx (server) → listQuestions() + getQuestionCoverage() → FastAPI
 *   ↓
 *   QuestionBoard（客户端）快速录题 + 覆盖率矩阵（红格=缺）+ 抽题模拟
 */

import PageHeader from "@/components/PageHeader";
import QuestionBoard from "@/components/QuestionBoard";
import { ApiError } from "@/lib/apiClient";
import { getQuestionCoverage, listQuestions } from "@/services/interviewService";

export const dynamic = "force-dynamic";

export default async function QuestionsPage() {
  try {
    const [questions, coverage] = await Promise.all([
      listQuestions(),
      getQuestionCoverage(),
    ]);

    return (
      <main className="flex flex-1 flex-col" style={{ background: "var(--color-canvas)" }}>
        <div
          className="mx-auto flex w-full max-w-[1180px] flex-col"
          style={{ padding: "32px 32px 56px", gap: 24 }}
        >
          <PageHeader
            eyebrow="QUESTIONS · 题库生长"
            title="题库与覆盖率"
            subtitle="每天完成任务顺手录题（决策 5）：红格把「缺口在哪」直接显示出来，Day 26 只做查缺补漏，不从零开始整理。"
          />
          <QuestionBoard initialQuestions={questions} initialCoverage={coverage} />
        </div>
      </main>
    );
  } catch (err) {
    const message =
      err instanceof ApiError
        ? err.message
        : "无法连接后端服务，请确认 FastAPI 已启动（127.0.0.1:8000）";

    return (
      <main
        className="flex flex-1 items-center justify-center"
        style={{ background: "var(--color-canvas)" }}
      >
        <div
          className="max-w-md text-center"
          style={{
            padding: 32,
            background: "var(--color-card)",
            border: "1px solid var(--color-rose)",
            borderRadius: "var(--radius-card-lg)",
          }}
        >
          <h1 className="text-lg font-semibold" style={{ color: "var(--color-rose-deep)" }}>
            题库页加载失败
          </h1>
          <p className="mt-2 text-sm" style={{ color: "var(--color-ink-48)" }}>
            {message}
          </p>
        </div>
      </main>
    );
  }
}
