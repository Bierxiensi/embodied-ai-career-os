import { redirect } from "next/navigation";

/**
 * 根路径重定向到 /today（今日施工单）。
 *
 * 2026-09-10 变更（见 docs/platform-direction-30day.md §六）：
 *   原本重定向到 /dashboard —— 那是一块「我现在什么水平」的能力盘点看板，
 *   回答的是"状态"；而学习平台的第一个入口必须回答"我今天该做什么"。
 *   顶栏如果有 9 个入口却一个都不叫「今天」，平台就只是一面镜子、不是施工图。
 *
 *   /dashboard 未删除，降为二级页「概览」保留。
 */
export default function Home() {
  redirect("/today");
}
