import Link from "next/link";
import GenerateTaskButton from "./GenerateTaskButton";
import type { ActiveTrack, Skill } from "@/types";

type Props = {
  skills: Skill[];
  /** 当前视角赛道：用于把「技能图谱」磁贴的计数收敛到本视角口径 */
  activeTrack?: ActiveTrack | null;
};

/** 快捷操作卡片 — 2x2 网格的操作磁贴。所有磁贴均为真实可交互入口。 */
export default function QuickActions({ skills, activeTrack }: Props) {
  // 计数由真实数据得出，避免硬编码数字过期
  const allGapCount = skills.filter((s) => s.targetLevel - s.level > 0).length;

  return (
    <div
      className="flex flex-col"
      style={{
        gap: "var(--spacing-md)",
        padding: "var(--spacing-lg)",
        background: "var(--color-card)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-card-lg)",
      }}
    >
      <span className="text-[17px] font-semibold" style={{ color: "var(--color-ink)" }}>
        快捷操作
      </span>
      <div className="flex flex-wrap" style={{ gap: "var(--spacing-sm)" }}>
        {/* Tile 1: Generate Tasks (primary, real action) */}
        <GenerateTaskButton
          skills={skills}
          variant="tile"
          trackKey={activeTrack?.key ?? null}
        />

        {/* Tile 2: Projects (link to existing route) */}
        <Link
          href="/projects"
          className="flex flex-col no-underline"
          style={{
            width: "calc(50% - 6px)",
            gap: 8,
            padding: "var(--spacing-md)",
            borderRadius: "var(--radius-item-md)",
            background: "var(--color-zinc-100)",
            height: 110,
            cursor: "pointer",
          }}
        >
          <div
            className="flex items-center justify-center"
            style={{
              width: 30,
              height: 30,
              borderRadius: "var(--radius-item-sm)",
              background: "var(--color-primary-soft)",
            }}
          >
            <svg viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M5 10L15 5L25 10L15 15L5 10Z" stroke="#0066CC" strokeWidth="1.5" fill="none" strokeLinejoin="round" />
              <path d="M5 15L15 20L25 15" stroke="#0066CC" strokeWidth="1.5" fill="none" strokeLinejoin="round" />
              <path d="M5 20L15 25L25 20" stroke="#0066CC" strokeWidth="1.5" fill="none" strokeLinejoin="round" />
            </svg>
          </div>
          <span className="text-sm font-semibold" style={{ color: "var(--color-ink)" }}>
            项目管理
          </span>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            查看项目与里程碑
          </span>
        </Link>

        {/* Tile 3: 技能缺口 —— 口径收敛到「当前视角赛道」，
            不再用全量 48 技能报「34 项待补」（与雷达 8 轴自相矛盾，审计问题之一） */}
        <Link
          href="/jobs"
          className="flex flex-col no-underline"
          style={{
            width: "calc(50% - 6px)",
            gap: 8,
            padding: "var(--spacing-md)",
            borderRadius: "var(--radius-item-md)",
            background: "var(--color-zinc-100)",
            height: 72,
            cursor: "pointer",
          }}
        >
          <span className="text-sm font-semibold" style={{ color: "var(--color-ink)" }}>
            技能缺口
          </span>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            {activeTrack
              ? `本视角 ${activeTrack.skillCount} 项要求 · 缺 ${activeTrack.gapCount} 项`
              : `全量 ${skills.length} 项 · 缺 ${allGapCount} 项`}
          </span>
        </Link>

        {/* Tile 4: Journal (not yet built — honest "coming soon" state) */}
        <div
          className="flex flex-col"
          style={{
            width: "calc(50% - 6px)",
            gap: 8,
            padding: "var(--spacing-md)",
            borderRadius: "var(--radius-item-md)",
            background: "var(--color-zinc-100)",
            height: 72,
            opacity: 0.6,
          }}
          title="复盘日志模块即将上线"
        >
          <span className="text-sm font-semibold" style={{ color: "var(--color-ink-48)" }}>
            复盘日志
          </span>
          <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
            即将上线 · Reviewer 评估
          </span>
        </div>
      </div>
    </div>
  );
}
