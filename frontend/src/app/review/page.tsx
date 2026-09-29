/** /review —— 三问之二「复习什么」：今日复盘 + 学习日志沉淀。
 * SM-2 复习队列由计划 2（掌握单元）接入，本页先承载复盘闭环。 */

import PageHeader from "@/components/PageHeader";
import ReviewBoard from "@/components/ReviewBoard";
import ReviewQueue from "@/components/ReviewQueue";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  return (
    <main className="flex flex-1 flex-col" style={{ background: "var(--surface-canvas)" }}>
      <div
        className="mx-auto flex w-full max-w-[1180px] flex-col"
        style={{ padding: "32px 32px 56px", gap: 24 }}
      >
        <PageHeader
          eyebrow="REVIEW · 复习与复盘"
          title="今日复盘"
          subtitle="写清「今天到底做了什么」——这是证据链的第一环，也是复习队列的来源。"
        />
        <ReviewQueue />
        <ReviewBoard />
      </div>
    </main>
  );
}
