/** 统一 API 客户端封装。
 *
 * 职责：
 * - 封装 fetch，统一处理 ApiResponse<T> 包结构
 * - 业务组件只读 data，不感知 success/message 包装
 * - 统一错误处理（遵循 ExperienceRecall 教训：固化契约 + 单点解包）
 *
 * URL 解析：
 * - 浏览器端：相对路径 /api/*，由 Next.js rewrites 代理到后端 8000
 * - Server Component：必须用绝对 URL（Next.js 限制），读 BACKEND_URL 环境变量
 *   services 层无需感知运行环境，由 baseUrl() 自动适配
 */

/** 后端统一响应结构（对齐 backend/app/core/response.py）。 */
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  message: string | null;
}

/** 业务错误：success=false 时抛出，携带 message。 */
export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/** 根据运行环境返回 API base URL。
 *
 * - 浏览器：空串（走相对路径，由 Next rewrites 代理）
 * - 服务端：后端绝对 URL（server component fetch 必须绝对路径）
 */
function baseUrl(): string {
  if (typeof window !== "undefined") {
    return ""; // 客户端：相对路径，由 Next.js rewrites 代理
  }
  // 服务端：server component 必须用绝对 URL
  return process.env.BACKEND_URL || "http://localhost:8000";
}

/** 通用请求方法：解包 ApiResponse，失败抛 ApiError。 */
async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  // 服务端运行时需拼接绝对 URL；客户端直接用相对路径
  const fullUrl = url.startsWith("http") ? url : `${baseUrl()}${url}`;

  const res = await fetch(fullUrl, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    throw new ApiError(`HTTP ${res.status}: ${res.statusText}`);
  }

  const body: ApiResponse<T> = await res.json();

  // 统一解包：失败时抛错，成功时返回 data
  if (!body.success) {
    throw new ApiError(body.message || "Request failed");
  }

  return body.data as T;
}

export const apiClient = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: "POST",
      body: data !== undefined ? JSON.stringify(data) : undefined,
    }),
  patch: <T>(url: string, data: unknown) =>
    request<T>(url, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  put: <T>(url: string, data: unknown) =>
    request<T>(url, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};
