/** 30 天课程脊梁总览页面（Server Component）。 */

import PlanBoard from "@/components/PlanBoard";
import PageShell from "@/ui/page-shell";
import ErrorCard from "@/ui/error-card";
import { getPlanOverview } from "@/services/planService";

export const dynamic = "force-dynamic";

export default async function PlanPage() {
  try {
    const overview = await getPlanOverview();

    return (
      <PageShell
        eyebrow="PLAN · 30 天课程脊梁"
        title="施工总览"
        subtitle="课程进度与日历进度解耦：滑期只提示、不自动顺延，落后日期需手动决策。"
      >
        <PlanBoard overview={overview} />
      </PageShell>
    );
  } catch (err) {
    return <ErrorCard pageName="施工总览" error={err} />;
  }
}
