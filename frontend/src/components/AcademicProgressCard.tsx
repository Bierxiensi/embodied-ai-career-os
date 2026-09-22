import { COUNTDOWN_COLOR, COUNTDOWN_LABEL, daysText } from "@/lib/countdown";
import type { AcademicProgress, AdvisorBrief, DegreeProgress } from "@/types";

type Props = {
  /** 学术区（来自 /api/transition/dashboard）。 */
  academic: AcademicProgress;
};

/** 一个带倒计时的节点（答辩 / 导师联系窗口共用）。 */
function CountdownRow({
  title,
  deadline,
  daysLeft,
  status,
  note,
}: {
  title: string;
  deadline: string;
  daysLeft: number;
  status: DegreeProgress["status"];
  note: string;
}) {
  return (
    <div className="flex flex-col" style={{ gap: 6 }}>
      <div className="flex items-center justify-between" style={{ gap: 10 }}>
        <span className="text-[13px] font-semibold" style={{ color: "var(--color-ink)" }}>
          {title}
        </span>
        <span
          className="text-[11px] font-semibold shrink-0"
          style={{
            color: COUNTDOWN_COLOR[status],
            background: "var(--color-canvas)",
            border: `1px solid ${COUNTDOWN_COLOR[status]}`,
            borderRadius: "var(--radius-pill)",
            padding: "1px 8px",
          }}
        >
          {COUNTDOWN_LABEL[status]}
        </span>
      </div>
      <div className="flex items-baseline" style={{ gap: 10 }}>
        <span className="text-[22px] font-semibold" style={{ color: "var(--color-ink)" }}>
          {daysLeft}
        </span>
        <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
          天 · {daysText(daysLeft)} · 截止 {deadline}
        </span>
      </div>
      <span className="text-xs" style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}>
        {note}
      </span>
    </div>
  );
}

/** 一项计数（院校 / 导师 / 已联系 / 已匹配）。 */
function Stat({ label, value, accent }: { label: string; value: number; accent?: boolean }) {
  return (
    <div
      className="flex flex-col items-center"
      style={{
        flex: "1 1 0",
        gap: 2,
        padding: "8px 4px",
        background: "var(--color-canvas)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-item-md)",
      }}
    >
      <span
        className="text-[17px] font-semibold"
        style={{ color: accent ? "var(--color-primary)" : "var(--color-ink)" }}
      >
        {value}
      </span>
      <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
        {label}
      </span>
    </div>
  );
}

/** 一位导师摘要（明细去 /phd 页，这里最多 Top3）。 */
function AdvisorRow({ advisor }: { advisor: AdvisorBrief }) {
  const hasMatch = advisor.matchOverall !== null && advisor.matchOverallMax !== null;
  return (
    <div className="flex items-center justify-between" style={{ gap: 10 }}>
      <div className="flex items-center" style={{ gap: 8, minWidth: 0 }}>
        <span className="text-[13px] font-medium" style={{ color: "var(--color-ink)" }}>
          {advisor.name}
        </span>
        <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
          {advisor.institution ?? "院校待补"}
        </span>
        {advisor.tier ? (
          <span
            className="text-[11px] shrink-0"
            style={{
              color: "var(--color-ink-48)",
              border: "1px solid var(--color-hairline)",
              borderRadius: "var(--radius-pill)",
              padding: "0 6px",
            }}
          >
            {advisor.tier}
          </span>
        ) : null}
      </div>
      <div className="flex items-center shrink-0" style={{ gap: 8 }}>
        {advisor.contacted ? (
          <span className="text-[11px] font-semibold" style={{ color: "var(--color-emerald-deep)" }}>
            已联系
          </span>
        ) : (
          <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
            未联系
          </span>
        )}
        {hasMatch ? (
          <span className="text-xs" style={{ color: "var(--color-ink-80)" }}>
            六维 {advisor.matchOverall}/{advisor.matchOverallMax}
            {advisor.matchGrade ? ` · ${advisor.matchGrade}` : ""}
          </span>
        ) : (
          <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
            未匹配
          </span>
        )}
      </div>
    </div>
  );
}

/** 第 3 区：学术与博士 —— 硕士答辩倒计时 + 博士申请进度。
 *
 * 为什么合成一区：
 *   两者共用同一个约束 —— **时间**。答辩（2026-12）是转型窗口的硬边界，
 *   博士申请季（26 秋–27 春）与导师联系窗口（2026-11）压在同一个季度。
 *   分开两区会让人以为可以分别安排，实际必须一起排。
 *
 * 截止日一律来自后端 `core/transition_context`（答辩 / 导师窗口单点定义），
 * 与七维风险雷达的 academic 维度同源 —— 见 tests/test_transition_dashboard.py。
 * 博士明细（13 所院校、8 位导师）在 /phd 页，这里只做摘要。
 */
export default function AcademicProgressCard({ academic }: Props) {
  const { degree, phd } = academic;

  return (
    <div
      className="flex flex-col"
      style={{
        flex: "1 1 420px",
        maxWidth: 690,
        minWidth: 0,
        gap: "var(--spacing-md)",
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <div className="flex flex-col" style={{ gap: 4 }}>
        <span className="text-[17px] font-semibold" style={{ color: "var(--color-ink)" }}>
          学术与博士
        </span>
        <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
          答辩是转型窗口的硬边界；博士申请季与导师联系窗口压在同一季度
        </span>
      </div>

      <CountdownRow
        title={degree.label}
        deadline={degree.deadline}
        daysLeft={degree.daysLeft}
        status={degree.status}
        note={degree.note}
      />

      <div
        className="flex flex-col"
        style={{ gap: 12, paddingTop: 12, borderTop: "1px solid var(--color-hairline)" }}
      >
        <div className="flex items-center justify-between" style={{ gap: 10 }}>
          <span className="text-[13px] font-semibold" style={{ color: "var(--color-ink)" }}>
            博士申请
          </span>
          <span className="text-[11px]" style={{ color: "var(--color-ink-48)" }}>
            {phd.seasonLabel}
          </span>
        </div>

        <CountdownRow
          title={phd.windowLabel}
          deadline={phd.windowDeadline}
          daysLeft={phd.windowDaysLeft}
          status={phd.windowStatus}
          note={`申请季 ${phd.seasonLabel}；导师名单与六维匹配明细见 /phd 页`}
        />

        <div className="flex" style={{ gap: 8 }}>
          <Stat label="目标院校" value={phd.targetCount} />
          <Stat label="导师" value={phd.advisorCount} />
          <Stat label="已联系" value={phd.contactedCount} accent={phd.contactedCount > 0} />
          <Stat label="已匹配" value={phd.matchedCount} accent={phd.matchedCount > 0} />
        </div>

        {phd.nearestDeadline ? (
          <span className="text-xs" style={{ color: "var(--color-ink-80)" }}>
            最近截止：{phd.nearestDeadline.institution} · {phd.nearestDeadline.deadline}
            {" "}({daysText(phd.nearestDeadline.daysLeft)})
          </span>
        ) : (
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            暂无院校截止日（/phd 页补录 13 所院校的 deadline 后显示）
          </span>
        )}

        {phd.topAdvisors.length > 0 ? (
          <div className="flex flex-col" style={{ gap: 8 }}>
            <span className="text-[13px] font-semibold" style={{ color: "var(--color-ink-80)" }}>
              重点导师
            </span>
            {phd.topAdvisors.map((a) => (
              <AdvisorRow key={a.id} advisor={a} />
            ))}
          </div>
        ) : (
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            导师库为空 —— 在 /phd 页录入院校与导师后，这里显示六维匹配 Top3
          </span>
        )}
      </div>
    </div>
  );
}
