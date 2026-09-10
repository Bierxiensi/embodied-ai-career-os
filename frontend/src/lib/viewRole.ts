/** 视角角色的共享工具（Server / Client 均可安全引用）。
 *
 * 为什么要单独抽一个模块：
 * - Server Component（app/dashboard/page.tsx）需要读 cookie 名与默认值
 * - Client Component（components/RoleSwitcher.tsx）需要写 cookie 与拼跳转链接
 * 若把常量放在 dashboardService.ts，客户端组件会把整个服务层（含 apiClient）打进
 * 浏览器 bundle；放在 RoleSwitcher 里又会被服务端组件引入客户端模块图。
 * 所以单独放 lib/ —— 零依赖，两个世界都能用。
 */

import type { ViewRole } from "@/types";

/** 记住上次选择的 cookie 名。 */
export const VIEW_ROLE_COOKIE = "view_role";

/** 默认视角：求职冲刺（与 v2.0「求职优先」战略一致）。 */
export const DEFAULT_VIEW_ROLE: ViewRole = "jobhunt";

/** 合法视角白名单 —— 非法值一律回退默认，避免 URL 传入野值。 */
const VALID_ROLES: readonly ViewRole[] = ["jobhunt", "embodied"];

export function normalizeViewRole(raw: string | null | undefined): ViewRole {
  return VALID_ROLES.includes(raw as ViewRole) ? (raw as ViewRole) : DEFAULT_VIEW_ROLE;
}

/** 视角对应的 Dashboard URL（jobhunt 省略参数，保持 URL 干净）。 */
export function viewRoleHref(role: ViewRole): string {
  return role === DEFAULT_VIEW_ROLE ? "/dashboard" : `/dashboard?role=${role}`;
}
