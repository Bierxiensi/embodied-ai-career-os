/** 导航单一真源（2026-09-24 IA 收敛：11 入口 → 三问三入口）。
 *
 * IA 口径（诚实版）：3 主入口（PRIMARY_NAV：学/习/证）+ 命令面板（PALETTE_ITEMS）
 * + 低频侧栏（由 PALETTE_ITEMS 按 group 分组渲染，同源于 PALETTE_ITEMS）
 * + /stages 归档收纳。
 * STYLE.md 不变量：新增入口先问能否并入 PALETTE_ITEMS，PRIMARY_NAV 永远只回答三问。 */

export type NavItem = { href: string; label: string; hint: string };

/** 低频侧栏分组 —— 只有 PALETTE_ITEMS 需要带（PRIMARY_NAV 不进侧栏）。 */
export type PaletteGroup = "常用" | "求职（归档）" | "学术（归档）" | "系统";

export type PaletteItem = NavItem & { group: PaletteGroup };

export const PRIMARY_NAV: NavItem[] = [
  { href: "/learn", label: "学", hint: "今天学什么" },
  { href: "/review", label: "习", hint: "复习与复盘" },
  { href: "/progress", label: "证", hint: "能力真提升吗" },
];

export const PALETTE_ITEMS: PaletteItem[] = [
  { href: "/stages", label: "阶段", hint: "归档线与阶段切换", group: "系统" },
  { href: "/knowledge", label: "知识库", hint: "论文检索与问答（单元内也可问）", group: "常用" },
  { href: "/projects", label: "项目", hint: "项目与证据流", group: "常用" },
  { href: "/questions", label: "题库", hint: "面试题与小测", group: "常用" },
  { href: "/interview", label: "面试", hint: "面试日志与复盘", group: "常用" },
  { href: "/jd", label: "JD", hint: "岗位分析（归档线）", group: "求职（归档）" },
  { href: "/jobs", label: "求职", hint: "投递看板（归档线）", group: "求职（归档）" },
  { href: "/resume", label: "简历", hint: "版本与防虚构诊断（归档线）", group: "求职（归档）" },
  { href: "/phd", label: "博士", hint: "申请线（归档线）", group: "学术（归档）" },
  { href: "/plan", label: "计划", hint: "30 天课程脊梁", group: "常用" },
  { href: "/agents", label: "Agents", hint: "编排调试", group: "系统" },
  { href: "/ui-test", label: "UI 测试", hint: "组件验收页", group: "系统" },
];

/** 侧栏分组顺序（layout.tsx 按此渲染；未列出的分组不显示）。 */
export const SIDEBAR_GROUP_ORDER: PaletteGroup[] = [
  "常用",
  "求职（归档）",
  "学术（归档）",
  "系统",
];
