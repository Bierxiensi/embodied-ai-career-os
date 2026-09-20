/** 技能证据链页面（Server Component）。 */

import EvidenceBoard from "@/components/EvidenceBoard";
import PageShell from "@/ui/page-shell";
import ErrorCard from "@/ui/error-card";
import { getSkillEvidenceList } from "@/services/experimentService";

export const dynamic = "force-dynamic";

export default async function EvidencePage() {
  try {
    const skills = await getSkillEvidenceList();

    return (
      <PageShell
        eyebrow="EVIDENCE · 技能证据链"
        title="证据可信度"
        subtitle="技能等级不再靠自评：每条晋级都附带「因为这份代码 / 笔记 / 实验」的可信证据，面试时直接打开对照。"
      >
        <EvidenceBoard skills={skills} />
      </PageShell>
    );
  } catch (err) {
    return <ErrorCard pageName="证据页" error={err} />;
  }
}
