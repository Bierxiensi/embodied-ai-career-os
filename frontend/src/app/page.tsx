import { redirect } from "next/navigation";

/**
 * 根路径重定向到 /dashboard。
 *
 * Day6 起 Dashboard 数据由真实 API 提供，统一入口为 /dashboard。
 * 旧版根路径直接渲染 mock 数据的逻辑已废弃。
 */
export default function Home() {
  redirect("/dashboard");
}
