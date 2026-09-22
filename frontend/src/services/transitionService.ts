/** 职业转型落地页服务层（Phase 3）。
 *
 * 职责：调用 `/api/transition/dashboard`，把后端的 snake_case 适配成
 * 前端 `TransitionDashboard`（camelCase）。组件只读 camelCase，不感知后端字段形状
 * —— 与 jobHuntService / careerModeService / skillService 同一取向。
 *
 * 设计边界：
 *  - 就绪度字段（matchPct / strictPct / qualifiedCount / requiredCount）**不在这里重算**，
 *    原样搬运。它们的唯一权威是后端 `services/readiness`，与 /jobs 页逐字同源；
 *    前端再算一遍就会出现"同一天两页数字不一样"的老问题。
 *  - 倒计时天数同理：后端算好（`days_left`，负数 = 已过期），前端只做颜色映射。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  AdvisorBrief,
  AcademicProgress,
  CareerMode,
  CareerModeKey,
  CareerProgress,
  CountdownStatus,
  DegreeProgress,
  NearestDeadline,
  PhDProgress,
  Position,
  TrackProgress,
  TransitionDashboard,
  TransitionMilestone,
} from "@/types";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface CareerModeDTO {
  id: number;
  key: string;
  name: string;
  objective: string;
  deadline: string | null;
  days_left: number | null;
  active_track_keys: string[];
  frozen_track_keys: string[];
  is_current: boolean;
}

interface TrackProgressDTO {
  key: string;
  name: string;
  priority: string;
  frozen: boolean;
  match_pct: number;
  strict_pct: number;
  qualified_count: number;
  required_count: number;
  skill_count: number;
  gap_count: number;
}

interface MilestoneDTO {
  key: string;
  label: string;
  deadline: string;
  days_left: number;
  status: string;
  note: string;
}

interface CareerProgressDTO {
  primary_track_key: string | null;
  tracks: TrackProgressDTO[];
  milestones: MilestoneDTO[];
}

interface PositionDTO {
  company: string;
  role: string;
  focus: string;
  since_label: string;
  end_label: string | null;
  status_label: string;
  note: string;
  transition_window_start: string;
  transition_window_end: string;
  transition_window_label: string;
}

interface DegreeDTO {
  label: string;
  deadline: string;
  days_left: number;
  status: string;
  note: string;
}

interface AdvisorBriefDTO {
  id: number;
  name: string;
  institution: string | null;
  tier: string | null;
  contacted: boolean;
  match_overall: number | null;
  match_grade: string | null;
  match_overall_max: number | null;
}

interface NearestDeadlineDTO {
  institution: string;
  deadline: string;
  days_left: number;
}

interface PhDProgressDTO {
  season_label: string;
  window_label: string;
  window_deadline: string;
  window_days_left: number;
  window_status: string;
  target_count: number;
  advisor_count: number;
  contacted_count: number;
  matched_count: number;
  nearest_deadline: NearestDeadlineDTO | null;
  top_advisors: AdvisorBriefDTO[];
}

interface AcademicDTO {
  degree: DegreeDTO;
  phd: PhDProgressDTO;
}

interface TransitionDashboardDTO {
  as_of: string;
  mode: CareerModeDTO;
  career_progress: CareerProgressDTO;
  position: PositionDTO;
  academic: AcademicDTO;
}

/* ───────────────────────── 适配 ───────────────────────── */

/** 后端状态串 → 前端分档联合类型（未知值降级为 ok，避免旧后端让页面崩）。 */
function toStatus(raw: string): CountdownStatus {
  return raw === "overdue" || raw === "urgent" || raw === "soon" ? raw : "ok";
}

function toMilestone(dto: MilestoneDTO): TransitionMilestone {
  return {
    key: dto.key,
    label: dto.label,
    deadline: dto.deadline,
    daysLeft: dto.days_left,
    status: toStatus(dto.status),
    note: dto.note,
  };
}

function toTrack(dto: TrackProgressDTO): TrackProgress {
  return {
    key: dto.key,
    name: dto.name,
    priority: dto.priority,
    frozen: dto.frozen,
    matchPct: dto.match_pct,
    strictPct: dto.strict_pct,
    qualifiedCount: dto.qualified_count,
    requiredCount: dto.required_count,
    skillCount: dto.skill_count,
    gapCount: dto.gap_count,
  };
}

function toPosition(dto: PositionDTO): Position {
  return {
    company: dto.company,
    role: dto.role,
    focus: dto.focus,
    sinceLabel: dto.since_label,
    endLabel: dto.end_label,
    statusLabel: dto.status_label,
    note: dto.note,
    transitionWindowStart: dto.transition_window_start,
    transitionWindowEnd: dto.transition_window_end,
    transitionWindowLabel: dto.transition_window_label,
  };
}

function toDegree(dto: DegreeDTO): DegreeProgress {
  return {
    label: dto.label,
    deadline: dto.deadline,
    daysLeft: dto.days_left,
    status: toStatus(dto.status),
    note: dto.note,
  };
}

function toAdvisor(dto: AdvisorBriefDTO): AdvisorBrief {
  return {
    id: String(dto.id),
    name: dto.name,
    institution: dto.institution,
    tier: dto.tier,
    contacted: dto.contacted,
    matchOverall: dto.match_overall,
    matchGrade: dto.match_grade,
    matchOverallMax: dto.match_overall_max,
  };
}

function toNearestDeadline(dto: NearestDeadlineDTO): NearestDeadline {
  return {
    institution: dto.institution,
    deadline: dto.deadline,
    daysLeft: dto.days_left,
  };
}

function toPhD(dto: PhDProgressDTO): PhDProgress {
  return {
    seasonLabel: dto.season_label,
    windowLabel: dto.window_label,
    windowDeadline: dto.window_deadline,
    windowDaysLeft: dto.window_days_left,
    windowStatus: toStatus(dto.window_status),
    targetCount: dto.target_count,
    advisorCount: dto.advisor_count,
    contactedCount: dto.contacted_count,
    matchedCount: dto.matched_count,
    nearestDeadline: dto.nearest_deadline
      ? toNearestDeadline(dto.nearest_deadline)
      : null,
    topAdvisors: (dto.top_advisors ?? []).map(toAdvisor),
  };
}

function toCareerMode(dto: CareerModeDTO): CareerMode {
  return {
    id: String(dto.id),
    key: dto.key as CareerModeKey,
    name: dto.name,
    objective: dto.objective,
    deadline: dto.deadline,
    daysLeft: dto.days_left,
    activeTrackKeys: dto.active_track_keys ?? [],
    frozenTrackKeys: dto.frozen_track_keys ?? [],
    isCurrent: dto.is_current,
  };
}

function toAcademic(dto: AcademicDTO): AcademicProgress {
  return { degree: toDegree(dto.degree), phd: toPhD(dto.phd) };
}

function toCareerProgress(dto: CareerProgressDTO): CareerProgress {
  return {
    primaryTrackKey: dto.primary_track_key,
    tracks: (dto.tracks ?? []).map(toTrack),
    milestones: (dto.milestones ?? []).map(toMilestone),
  };
}

/* ───────────────────────── 对外接口 ───────────────────────── */

/** 获取统一落地页的三区数据（职业进度 / 当前工作 / 学术·博士）。
 *
 * 第 4、5 区（ROI 任务、风险雷达）不在此端点，页面另行调用 `getToday()`。
 */
export async function getTransitionDashboard(): Promise<TransitionDashboard> {
  const dto = await apiClient.get<TransitionDashboardDTO>("/api/transition/dashboard");
  return {
    asOf: dto.as_of,
    mode: toCareerMode(dto.mode),
    careerProgress: toCareerProgress(dto.career_progress),
    position: toPosition(dto.position),
    academic: toAcademic(dto.academic),
  };
}
