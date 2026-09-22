/** 技能雷达数据源适配（Phase 3）。
 *
 * 一句话：**模式决定雷达轴是什么**。
 *
 *  - `job_hunt`（求职期）→ **R1 岗位对齐**：轴 = 主攻赛道的硬性要求技能（13 项）。
 *    含义是"离目标岗位的技能形状还差多少"，与 /jobs 页同一份数字。
 *  - `long_term_transition`（在职转型期）→ **R2 域聚合**：轴 = 能力六域。
 *    求职期看单项技能缺口是对的；转型期先看"哪个能力域整体薄"
 *    ——13 项技能里哪项差 1 级，不如"推理工程整体差 2.4 级"有决策价值。
 *
 * 为什么单独成文件：
 *    variant 的取舍（模式 → 轴来源）与 DTO 适配都不该长在组件里。
 *    SkillRadarCard 因此退化成纯渲染器（收 `SkillRadarData`，不判断模式）。
 *
 * 口径纪律：
 *    就绪度一律**搬运后端数字**，不在这里重算逐项技能的对齐情况 ——
 *    唯一权威是后端 `services/readiness`（岗位）与 `services/skill_graph`（域）。
 *    R2 的"六域整体达成度"是**跨域展示聚合**，按覆盖技能数加权，公式见
 *    `overallReadinessPct()`；后端目前不提供该数，故在适配层算一次并集中在此。
 */

import type {
  RadarAxis,
  RadarGapRow,
  SkillDomain,
  SkillDomainGap,
  SkillDomainOverview,
  SkillRadarData,
  TargetRole,
} from "@/types";

/** 域均值保留一位小数，避免 1.7000000000000002 之类浮点噪声进图。 */
function round1(n: number): number {
  return Math.round(n * 10) / 10;
}

/** 六域整体达成度（展示聚合）。
 *
 * 公式：`Σ(域均值 × 域内技能数) / Σ(域内技能数)` 求加权等级均值，
 * 再除以加权目标均值。按技能数加权而非对六域取平均 —— 否则
 * "科研底座"(3 项) 与 "LLM 基础"(11 项) 等权，会失真。
 *
 * 上限 100：某项技能超过目标等级时不计负缺口（与后端 `min(level, required)` 同向）。
 */
function overallReadinessPct(domains: SkillDomain[]): number {
  const total = domains.reduce((acc, d) => acc + d.skillCount, 0);
  if (total === 0) return 0;
  const cur = domains.reduce((acc, d) => acc + d.currentAvg * d.skillCount, 0) / total;
  const tgt = domains.reduce((acc, d) => acc + d.targetAvg * d.skillCount, 0) / total;
  if (tgt <= 0) return 0;
  return Math.min(100, Math.round((cur / tgt) * 100));
}

/** 未达标的先修项 → "先修 X（L3）未达标"。
 *
 * 没有未达标先修时返回 null（不显示提示行，而不是显示一行"无"）。
 */
function prereqHint(gap: SkillDomainGap, satisfiedLevel: number): string | null {
  const unmet = gap.prerequisites.filter((p) => !p.met);
  if (unmet.length === 0) return null;
  const names = unmet.map((p) => p.name).join(" / ");
  return `先修 ${names}（L${satisfiedLevel}）未达标`;
}

/* ───────────────────────── R1：岗位对齐 ───────────────────────── */

/** 由一条赛道（target_roles[i]）构造 R1 雷达数据。 */
export function jobRadar(track: TargetRole): SkillRadarData {
  const axes: RadarAxis[] = track.skills.map((s) => ({
    name: s.name,
    current: s.level,
    required: s.required,
    gap: s.gap,
  }));

  const gaps: RadarGapRow[] = track.skills
    .filter((s) => s.gap > 0)
    .sort((a, b) => b.gap - a.gap)
    .map((s) => ({
      name: s.name,
      current: s.level,
      target: s.required,
      gap: s.gap,
      // 岗位轴是整数等级，不补小数位 —— "1/4" 比 "1.0/4.0" 更像等级
      ratioLabel: `${s.level}/${s.required}`,
      hint: s.missing ? "技能表里暂无此项" : null,
    }));

  return {
    variant: "job",
    title: "岗位对齐雷达",
    axisCaption: `轴 = ${track.name} 的 ${axes.length} 项硬性要求技能`,
    axes,
    readiness: track.matchPct,
    readinessCaption: "岗位要求达成度",
    readinessNote:
      `严格达标 ${track.strictPct}%（${track.qualifiedCount}/${track.requiredCount} 项 level≥4）` +
      `；推进度按线性推进计`,
    gaps,
    emptyHint: "该赛道没有硬性要求技能（后端 target_roles 配置为空）",
  };
}

/* ───────────────────────── R2：域聚合 ───────────────────────── */

/** 由六域聚合（/api/skills/domains）构造 R2 雷达数据。 */
export function domainRadar(overview: SkillDomainOverview): SkillRadarData {
  const domains = overview.domains;

  const axes: RadarAxis[] = domains.map((d) => ({
    name: d.label,
    current: round1(d.currentAvg),
    required: round1(d.targetAvg),
    gap: round1(d.gapAvg),
  }));

  // 跨域展开缺口技能：先按缺口降序，同缺口时域内顺序不变（稳定排序）
  const gaps: RadarGapRow[] = domains
    .flatMap((d) => d.gapSkills)
    .sort((a, b) => b.gap - a.gap)
    .map((g) => ({
      name: g.name,
      current: g.level,
      target: g.targetLevel,
      gap: g.gap,
      ratioLabel: `${g.level}/${g.targetLevel}`,
      hint: prereqHint(g, overview.prereqSatisfiedLevel),
    }));

  return {
    variant: "domain",
    title: "能力域雷达",
    axisCaption: `轴 = 能力六域（域内技能等级均值，共 ${overview.mappedCount} 项技能）`,
    axes,
    readiness: overallReadinessPct(domains),
    readinessCaption: "六域整体达成度",
    readinessNote:
      `按域内技能数加权；另有 ${overview.unmappedCount} 项冻结/旁证技能不计入` +
      `；先修达标线 L${overview.prereqSatisfiedLevel}`,
    gaps,
    emptyHint: "六域暂无数据（后端 skill_profile 未标注 domain）",
  };
}

/* ───────────────────────── 模式 → variant ───────────────────────── */

/** 空数据兜底：保持卡片结构完整，只提示数据缺失。 */
function emptyRadar(variant: "job" | "domain", hint: string): SkillRadarData {
  const isJob = variant === "job";
  return {
    variant,
    title: isJob ? "岗位对齐雷达" : "能力域雷达",
    axisCaption: isJob ? "轴 = 主攻岗位的硬性要求技能" : "轴 = 能力六域",
    axes: [],
    readiness: 0,
    readinessCaption: isJob ? "岗位要求达成度" : "六域整体达成度",
    readinessNote: null,
    gaps: [],
    emptyHint: hint,
  };
}

export type SkillRadarSource = {
  /** 当前职业阶段 key；决定用 R1 还是 R2。 */
  modeKey: string | null;
  /** R1 数据源：/api/job-hunt 的 target_roles（可能不可用）。 */
  targetRoles: TargetRole[] | null;
  /** R2 数据源：/api/skills/domains（可能不可用）。 */
  domains: SkillDomainOverview | null;
};

/** 挑出 R1 用的赛道：优先"主攻"，其次是第一条未冻结赛道。 */
function pickTrack(roles: TargetRole[]): TargetRole | null {
  return (
    roles.find((r) => r.priority === "主攻") ??
    roles.find((r) => !r.frozen) ??
    roles[0] ??
    null
  );
}

/** 按当前模式构造雷达数据。
 *
 * 主选来源不可用时**退到另一条来源**并如实说明 —— 页面宁可给出"另一种视图"，
 * 也不要因为 job-hunt 短暂不可用就整块空白（转型期页面长期只跑 R2，
 * 求职期切回去时 /api/job-hunt 若报错，用户至少还能看到域视图）。
 */
export function buildSkillRadar(src: SkillRadarSource): SkillRadarData {
  const wantsJob = src.modeKey === "job_hunt";

  const jobTrack = src.targetRoles ? pickTrack(src.targetRoles) : null;
  const domains = src.domains && src.domains.domains.length > 0 ? src.domains : null;

  if (wantsJob) {
    if (jobTrack) return jobRadar(jobTrack);
    if (domains) return domainRadar(domains);
    return emptyRadar("job", "暂无赛道数据（后端 target_roles 为空，或 /api/job-hunt 暂不可用）");
  }

  if (domains) return domainRadar(domains);
  if (jobTrack) return jobRadar(jobTrack);
  return emptyRadar("domain", "暂无六域数据（/api/skills/domains 不可用，且无赛道兜底）");
}
