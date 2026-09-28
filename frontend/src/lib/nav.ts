/** 导航单一真源（2026-09-24 IA 收敛：11 入口 → 三问三入口 + 命令面板）。
 * STYLE.md 不变量：新增入口先问能否并入 PALETTE_ITEMS，PRIMARY_NAV 永远只回答三问。 */

export type NavItem = { href: string; label: string; hint: string };

export const PRIMARY_NAV: NavItem[] = [
  { href: "/learn", label: "学", hint: "今天学什么" },
  { href: "/review", label: "习", hint: "复习与复盘" },
  { href: "/progress", label: "证", hint: "能力真提升吗" },
];

export const PALETTE_ITEMS: NavItem[] = [
  { href: "/stages", label: "阶段", hint: "归档线与阶段切换" },
  { href: "/knowledge", label: "知识库", hint: "论文检索与问答（单元内也可问）" },
  { href: "/projects", label: "项目", hint: "项目与证据流" },
  { href: "/questions", label: "题库", hint: "面试题与小测" },
  { href: "/interview", label: "面试", hint: "面试日志与复盘" },
  { href: "/jd", label: "JD", hint: "岗位分析（归档线）" },
  { href: "/jobs", label: "求职", hint: "投递看板（归档线）" },
  { href: "/resume", label: "简历", hint: "版本与防虚构诊断（归档线）" },
  { href: "/phd", label: "博士", hint: "申请线（归档线）" },
  { href: "/plan", label: "计划", hint: "30 天课程脊梁" },
  { href: "/agents", label: "Agents", hint: "编排调试" },
  { href: "/ui-test", label: "UI 测试", hint: "组件验收页" },
];
