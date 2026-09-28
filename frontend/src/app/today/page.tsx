/** /today 已并入 /learn（2026-09-24 IA 收敛），保留旧链接可达。 */
import { redirect } from "next/navigation";

export default function TodayRedirect() {
  redirect("/learn");
}
