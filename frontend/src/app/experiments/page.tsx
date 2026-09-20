/** 实验记录页面（Server Component）。 */

import ExperimentBoard from "@/components/ExperimentBoard";
import PageShell from "@/ui/page-shell";
import ErrorCard from "@/ui/error-card";
import { getExperiments } from "@/services/experimentService";

export const dynamic = "force-dynamic";

export default async function ExperimentsPage() {
  try {
    const experiments = await getExperiments();

    return (
      <PageShell
        eyebrow="EXPERIMENTS · 实验记录"
        title="实验对比"
        subtitle="把训练 / 推理实验落表：面试时直接打开对比表，而不是空口说「我跑了 Qwen」。"
      >
        <ExperimentBoard experiments={experiments} />
      </PageShell>
    );
  } catch (err) {
    return <ErrorCard pageName="实验页" error={err} />;
  }
}
