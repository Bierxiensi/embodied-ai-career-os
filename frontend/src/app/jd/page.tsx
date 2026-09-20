/** /jd → /jobs/pool 兼容重定向。

 * 旧书签 / 外部链接仍可访问 /jd，自动跳转到新路径。
 */

import { redirect } from "next/navigation";

export default function JdRedirectPage() {
  redirect("/jobs/pool");
}
