/** 「指定资源」渲染：把惰性资源名变成可点入口。
 *
 * 背景（2026-09-23）：今日页原本把 `day.resources` 直接渲染成 `· 名字` 的纯文本 ——
 * 资源名是有的，但**不可点、也没有 URL**。这正是"不知道去哪里搜集学习资料"的直接原因：
 * 界面上写着「Hugging Face LLM Course」，但你没法从这句话跳到那个课程。
 *
 * 两级策略（宁可不可点，也不编造 URL）：
 *   1. **精确匹配** `RESOURCE_URL` 表 → 整条资源渲染成一个链接
 *   2. **未登记** → 自动识别串里的 arXiv 编号并逐个链接，其余文字保持纯文本
 *      （例：`LoRA (arXiv 2106.09685) + Hugging Face PEFT` → 只有编号变链接）
 *
 * 扩展方式：新资源只需往 `RESOURCE_URL` 加一条。**不要**用猜的 URL 兜底 ——
 * 点开 404 比不可点更差。
 *
 * 🔴 实测可达性（2026-09-23，本机会话）：`docs.vllm.ai` 200、`arxiv.org/abs/*` 200；
 * 但本机走系统代理打 **huggingface.co 是 502**（`Tunnel connection failed`，与安装
 * sentence-transformers 时同一个坑），故两条 HF 链接**当前打不开**。
 * 仍保留官方 URL 而非找替身：查过 `github.com/huggingface/llm-course` —— 它**是个空壳仓**
 * （1 个 commit、只有 LICENSE + README），换过去等于换成一个死路，比不可点更差。
 * 网络侧解决（VPN / 绕过代理）后这两条即可用。
 */

import type { CSSProperties, ReactNode } from "react";

/** 已登记资源名 → 官方入口。键必须与后端 `plan_30d.py:RESOURCE_LOCK` 的字符串**完全一致**。 */
const RESOURCE_URL: Record<string, string> = {
  "Hugging Face LLM Course": "https://huggingface.co/learn/llm-course",
  "Hugging Face Multimodal / LLaVA":
    "https://huggingface.co/docs/transformers/model_doc/llava",
  "vLLM Documentation": "https://docs.vllm.ai",
};

/** arXiv 编号（如 1706.03762）。用于未登记资源的自动链接。 */
const ARXIV_ID = /\b(\d{4}\.\d{4,5})\b/g;

const LINK: CSSProperties = {
  color: "var(--color-primary)",
  textDecoration: "none",
  borderBottom: "1px solid var(--color-primary-soft)",
};

/** 把一段文本里的 arXiv 编号变成链接，其余原样保留。 */
function withArxivLinks(text: string): ReactNode {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let m: RegExpExecArray | null;
  ARXIV_ID.lastIndex = 0;

  while ((m = ARXIV_ID.exec(text)) !== null) {
    if (m.index > cursor) nodes.push(text.slice(cursor, m.index));
    const id = m[1];
    nodes.push(
      <a
        key={`${id}-${m.index}`}
        href={`https://arxiv.org/abs/${id}`}
        target="_blank"
        rel="noopener noreferrer"
        style={LINK}
      >
        {id} ↗
      </a>
    );
    cursor = m.index + id.length;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

/** 渲染一组「指定资源」。 */
export default function ResourceList({ names }: { names: string[] }) {
  if (names.length === 0) {
    return (
      <span className="text-xs" style={{ color: "var(--color-ink-48)" }}>
        今日未指定资源
      </span>
    );
  }

  return (
    <div className="flex flex-col" style={{ gap: 8 }}>
      {names.map((name) => {
        const mapped = RESOURCE_URL[name];
        return (
          <span
            key={name}
            className="text-xs"
            style={{ color: "var(--color-ink-48)", lineHeight: 1.6 }}
          >
            ·{" "}
            {mapped ? (
              <a
                href={mapped}
                target="_blank"
                rel="noopener noreferrer"
                style={LINK}
              >
                {name} ↗
              </a>
            ) : (
              withArxivLinks(name)
            )}
          </span>
        );
      })}
    </div>
  );
}
