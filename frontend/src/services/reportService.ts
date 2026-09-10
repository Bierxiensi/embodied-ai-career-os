/** 日报 / 周报服务层（Batch 4）。
 *
 * 职责：封装 /api/reports 的构建 / 推送 / 历史 / 跟进接口，
 * 并把后端 snake_case 适配为前端 camelCase 类型。
 */

import { apiClient } from "@/lib/apiClient";
import type {
  Followup,
  FollowupResult,
  Report,
  ReportKind,
  ReportLog,
  ReportSchedule,
  ReportSection,
  SchedulerJob,
  SendResult,
} from "@/types";

/* ───────────────────────── 后端原始结构（snake_case） ───────────────────────── */

interface ReportSectionDTO {
  key: string;
  title: string;
  lines: string[];
}

interface ReportDTO {
  kind: string;
  period_key: string;
  title: string;
  sections: ReportSectionDTO[];
  metrics: Record<string, unknown>;
  generated_at: string;
}

interface ReportLogDTO {
  id: number;
  kind: string;
  period_key: string;
  title: string;
  body: string;
  sections: ReportSectionDTO[] | null;
  metrics: Record<string, unknown> | null;
  sent: boolean;
  sent_at: string | null;
  generated_at: string | null;
}

interface FollowupDTO {
  id: number;
  company: string;
  role: string;
  status: string;
  next_action: string | null;
  reason: string;
  days: number;
  overdue: boolean;
}

interface FollowupResultDTO {
  stale_days: number;
  count: number;
  items: FollowupDTO[];
}

interface SchedulerJobDTO {
  id: string;
  trigger: string;
  next_run: string | null;
}

interface ScheduleDTO {
  enabled: boolean;
  daily_time: string;
  weekly_day: string;
  weekly_time: string;
  followup_time: string;
  followup_stale_days: number;
  channel: string;
  jobs: SchedulerJobDTO[];
}

interface SendResultDTO {
  kind: string;
  period_key: string;
  sent: boolean;
  skipped: boolean;
  reason: string | null;
  title: string | null;
}

/* ───────────────────────── 适配函数 ───────────────────────── */

function toSections(dtos: ReportSectionDTO[] | null): ReportSection[] {
  return (dtos || []).map((s) => ({ key: s.key, title: s.title, lines: s.lines || [] }));
}

function toReport(dto: ReportDTO): Report {
  return {
    kind: dto.kind as ReportKind,
    periodKey: dto.period_key,
    title: dto.title,
    sections: toSections(dto.sections),
    metrics: dto.metrics || {},
    generatedAt: dto.generated_at,
  };
}

function toReportLog(dto: ReportLogDTO): ReportLog {
  return {
    id: String(dto.id),
    kind: dto.kind as ReportKind,
    periodKey: dto.period_key,
    title: dto.title,
    body: dto.body,
    sections: dto.sections ? toSections(dto.sections) : null,
    metrics: dto.metrics,
    sent: dto.sent,
    sentAt: dto.sent_at,
    generatedAt: dto.generated_at,
  };
}

function toFollowup(dto: FollowupDTO): Followup {
  return {
    id: String(dto.id),
    company: dto.company,
    role: dto.role,
    status: dto.status,
    nextAction: dto.next_action,
    reason: dto.reason,
    days: dto.days,
    overdue: dto.overdue,
  };
}

function toJob(dto: SchedulerJobDTO): SchedulerJob {
  return { id: dto.id, trigger: dto.trigger, nextRun: dto.next_run };
}

function toSendResult(dto: SendResultDTO): SendResult {
  return {
    kind: dto.kind as ReportKind,
    periodKey: dto.period_key,
    sent: dto.sent,
    skipped: dto.skipped,
    reason: dto.reason,
    title: dto.title,
  };
}

/* ───────────────────────── API ───────────────────────── */

/** 即时构建一份报告（不落库、不推送）。 */
export async function getReport(kind: ReportKind): Promise<Report> {
  const dto = await apiClient.get<ReportDTO>(`/api/reports/${kind}`);
  return toReport(dto);
}

/** 归档报告历史。 */
export async function getHistory(kind?: ReportKind, limit = 20): Promise<ReportLog[]> {
  const qs = new URLSearchParams();
  if (kind) qs.set("kind", kind);
  qs.set("limit", String(limit));
  const dtos = await apiClient.get<ReportLogDTO[]>(`/api/reports/history?${qs.toString()}`);
  return dtos.map(toReportLog);
}

/** 待跟进投递（next_action 到期 / 停滞超期）。 */
export async function getFollowups(): Promise<FollowupResult> {
  const dto = await apiClient.get<FollowupResultDTO>("/api/reports/followups");
  return {
    staleDays: dto.stale_days,
    count: dto.count,
    items: (dto.items || []).map(toFollowup),
  };
}

/** 报告调度配置与已注册 job。 */
export async function getSchedule(): Promise<ReportSchedule> {
  const dto = await apiClient.get<ScheduleDTO>("/api/reports/schedule");
  return {
    enabled: dto.enabled,
    dailyTime: dto.daily_time,
    weeklyDay: dto.weekly_day,
    weeklyTime: dto.weekly_time,
    followupTime: dto.followup_time,
    followupStaleDays: dto.followup_stale_days,
    channel: dto.channel,
    jobs: (dto.jobs || []).map(toJob),
  };
}

/** 生成并推送一份报告（幂等：已发送则跳过，除非 force）。 */
export async function sendReport(kind: ReportKind, force = false): Promise<SendResult> {
  const dto = await apiClient.post<SendResultDTO>(
    `/api/reports/${kind}/send${force ? "?force=true" : ""}`
  );
  return toSendResult(dto);
}
