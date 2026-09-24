"""论文语料下载脚本（幂等可重跑）。

把 `core/plan_30d.py:RESOURCE_LOCK` 对应的论文 PDF 拉到 `backend/data/corpus/`，
供 `scripts/rebuild_paper_corpus.py` 灌入知识库。

为什么是脚本而不是手工下载：
    知识库的价值取决于语料，而语料必须**可复现**。`backend/data/` 在 .gitignore 内
    （PDF 不宜入库），所以入库的是"怎么拿到它们"，不是 PDF 本身。
    新环境 clone 后：fetch → rebuild 两步即可重建知识库，与 seed_*.py 同一套约定。

选篇口径：与 RESOURCE_LOCK 对齐（Attention / LoRA / DPO / RLHF / GRPO / Qwen），
    另补 PPO / QLoRA / Qwen2 / Llama2 构成 Post-Training 主线的最小闭环。
    **刻意不选冻结赛道（embodied）的论文** —— 那与本项目当前主轴无关。

文件命名：`<arxivID> <论文标题>.pdf`。
    `parser._parse_pdf` 用**文件名**作标题线索并会剥掉 arxiv id：
        title_hint = stem.replace(arxiv_id, "").strip(" -_")
    所以这种命名能同时得到可追溯的 arxiv_id 与干净标题；
    只写 slug（如 `2305.18290_dpo`）会让论文标题变成 `2305.18290_dpo`。

幂等性：
    - 目标文件已存在且体积合理 → 跳过，不重复下载
    - arXiv 有速率要求，逐篇间隔 3 秒

运行：
    cd backend
    python scripts/fetch_paper_corpus.py              # 下载缺失的
    python scripts/fetch_paper_corpus.py --dry-run    # 只看会下什么
    python scripts/fetch_paper_corpus.py --force      # 全部重下
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
import urllib.error
import urllib.request

_BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUT = _BACKEND_ROOT / "data" / "corpus"

# (arxiv_id, 论文标题) —— 标题会成为文件名的一部分，故保持与论文一致
PAPERS: list[tuple[str, str]] = [
    ("1706.03762", "Attention Is All You Need"),
    ("2203.02155", "InstructGPT - Training language models to follow instructions"),
    ("1707.06347", "Proximal Policy Optimization Algorithms"),
    ("2106.09685", "LoRA - Low-Rank Adaptation of Large Language Models"),
    ("2305.14314", "QLoRA - Efficient Finetuning of Quantized LLMs"),
    ("2305.18290", "Direct Preference Optimization"),
    ("2402.03300", "DeepSeekMath - Pushing the Limits of Mathematical Reasoning"),
    ("2407.10671", "Qwen2 Technical Report"),
    ("2502.13923", "Qwen2.5-VL Technical Report"),
    ("2307.09288", "Llama 2 - Open Foundation and Fine-Tuned Chat Models"),
]

# 低于此体积视为下载不完整（最小的一篇也有 400KB+）
_MIN_BYTES = 50_000
_PDF_MAGIC = b"%PDF"
_DELAY_SECONDS = 3

_UA = {"User-Agent": "Mozilla/5.0 (career-os corpus fetch)"}


def target_path(out_dir: pathlib.Path, arxiv_id: str, title: str) -> pathlib.Path:
    """目标文件路径：`<arxivID> <标题>.pdf`。"""
    return out_dir / f"{arxiv_id} {title}.pdf"


def fetch_one(url: str, dest: pathlib.Path) -> tuple[bool, str]:
    """下载单篇。返回 (是否成功, 说明)。"""
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
        return False, f"{type(e).__name__}: {e}"

    if len(data) < _MIN_BYTES or data[:4] != _PDF_MAGIC:
        return False, f"内容异常 size={len(data)} magic={data[:4]!r}"

    dest.write_bytes(data)
    return True, f"{len(data) // 1024} KB"


def main() -> int:
    parser = argparse.ArgumentParser(description="下载论文语料到 data/corpus/")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true", help="只列出目标，不下载")
    parser.add_argument("--force", action="store_true", help="已存在的也重新下载")
    args = parser.parse_args()

    out_dir: pathlib.Path = args.out
    print(f"语料目录：{out_dir}")

    if args.dry_run:
        for arxiv_id, title in PAPERS:
            dest = target_path(out_dir, arxiv_id, title)
            state = "已存在" if dest.exists() else "待下载"
            print(f"  [{state}] {dest.name}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    ok: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    for i, (arxiv_id, title) in enumerate(PAPERS, 1):
        dest = target_path(out_dir, arxiv_id, title)

        if dest.exists() and not args.force and dest.stat().st_size >= _MIN_BYTES:
            skipped.append(dest.name)
            print(f"  [{i}/{len(PAPERS)}] 跳过（已存在）  {dest.name}")
            continue

        print(f"  [{i}/{len(PAPERS)}] 下载中…  {dest.name}")
        success, note = fetch_one(f"https://arxiv.org/pdf/{arxiv_id}", dest)
        if success:
            ok.append(dest.name)
            print(f"           ✅ {note}")
        else:
            failed.append((dest.name, note))
            print(f"           ❌ {note}")

        # arXiv 速率礼貌；最后一篇后不必等
        if i < len(PAPERS):
            time.sleep(_DELAY_SECONDS)

    total_bytes = sum(p.stat().st_size for p in out_dir.glob("*.pdf"))
    print()
    print(f"成功 {len(ok)} / 跳过 {len(skipped)} / 失败 {len(failed)}")
    print(f"目录现有 {len(list(out_dir.glob('*.pdf')))} 个 PDF，{total_bytes / 1024 / 1024:.1f} MB")

    if failed:
        print("\n失败清单（可重跑本脚本补下）：")
        for name, why in failed:
            print(f"  - {name}：{why}")
        return 1

    print("\n下一步：python scripts/rebuild_paper_corpus.py --yes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
