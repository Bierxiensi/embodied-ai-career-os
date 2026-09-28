"use client";

/** 全局命令面板挂载器（layout.tsx 挂一次，全站生效）：Ctrl/Cmd+K 开关。
 *
 * ui/CommandPalette 的 Props 契约是 { open, onClose, groups }（受控组件），
 * 故在此按契约机械适配 nav.ts 数据（内容不改，仅对号入座）：
 *   NavItem { href, label, hint } → CommandItem { id=href, label, icon=hint, action=router.push }。
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import CommandPalette from "@/components/ui/CommandPalette";
import type { NavItem } from "@/lib/nav";

type Props = {
  /** 三问三入口（PRIMARY_NAV）。 */
  primary: NavItem[];
  /** 低频入口（PALETTE_ITEMS）。 */
  palette: NavItem[];
};

export default function CommandPaletteMount({ primary, palette }: Props) {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const toCommand = (n: NavItem) => ({
    id: n.href,
    label: n.label,
    icon: n.hint,
    action: () => void router.push(n.href),
  });

  return (
    <CommandPalette
      open={open}
      onClose={() => setOpen(false)}
      groups={[
        { label: "三问", items: primary.map(toCommand) },
        { label: "全部入口", items: palette.map(toCommand) },
      ]}
    />
  );
}
