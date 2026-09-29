/** 作品集与证据门服务（计划 3）。 */

import { apiClient } from "@/lib/apiClient";

export type EvidenceRow = { skill: string; gate: number; refs: string[] };
export type PortfolioSection = { name: string; content: string };
export type Portfolio = {
  sections: PortfolioSection[];
  evidenceCount: number;
  readySkills: string[];
};

export async function getEvidenceList(): Promise<EvidenceRow[]> {
  const rows = await apiClient.get<
    {
      id: number;
      name: string;
      level: number;
      target_level: number;
      evidence_gate: number;
      evidence: { level: number; kind: string; label: string; ref: string }[];
    }[]
  >("/api/skills/evidence");
  // 字段以 backend/app/api/skills.py list_evidence 实际输出为准：
  // {id, name, level, target_level, evidence_gate, evidence:[{level,kind,label,ref}]}
  return rows.map((r) => ({
    skill: r.name,
    gate: r.evidence_gate,
    refs: (r.evidence ?? []).map((e) => e.ref),
  }));
}

export async function assemblePortfolio(): Promise<Portfolio> {
  const d = await apiClient.get<{
    sections: PortfolioSection[]; evidence_count: number; ready_skills: string[];
  }>("/api/portfolio/assemble");
  return { sections: d.sections, evidenceCount: d.evidence_count, readySkills: d.ready_skills };
}
