"""论文语料重建脚本（**破坏性**：清空并重灌知识库）。

    data/corpus/*.pdf  →  解析 → 分块 → 摘要 → 落库 → 建向量索引

为什么需要它：
    知识库的语料来自 `scripts/fetch_paper_corpus.py`。两者合起来构成"可复现的语料管线"——
    新环境 clone 后不必手工点 API 就能重建知识库。

⚠️ 这是**破坏性操作**：会清空 papers / paper_chunks / paper_chunk_embeddings 三张表。
    因此默认只做**预演**（列出将发生什么），必须显式加 `--yes` 才真正写库。
    写库前**强制备份** app.db（文件名带时间戳），并在结束时打印前后指纹。

向量库按 `model_name` 隔离（见 rag/vector_store.py），换嵌入模型时配合
    POST /api/paper/index {"force_rebuild": true}
或直接重跑本脚本即可。

前置：若要用真语义嵌入（推荐），先装 sentence-transformers 并在 .env 设 HF_ENDPOINT，
    否则 embedder 工厂会**静默退回 HashEmbedder**（伪嵌入，检索会"看起来能用但不准"）。

运行：
    cd backend
    python scripts/rebuild_paper_corpus.py            # 预演：只报告，不写库
    python scripts/rebuild_paper_corpus.py --yes      # 真正执行（会先备份）
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import sys
import time
from datetime import datetime

_BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy import text  # noqa: E402

from app.db.base import SessionLocal  # noqa: E402

DEFAULT_CORPUS = _BACKEND_ROOT / "data" / "corpus"
DB_PATH = _BACKEND_ROOT / "data" / "app.db"

# 清空顺序：先子表后主表
_TABLES_IN_ORDER = ("paper_chunk_embeddings", "paper_chunks", "papers")


def _md5(path: pathlib.Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="重建论文语料（破坏性）")
    parser.add_argument("--corpus", type=pathlib.Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--yes", action="store_true",
        help="确认执行（不加则只预演，不写库）",
    )
    args = parser.parse_args()

    corpus: pathlib.Path = args.corpus
    pdfs = sorted(corpus.glob("*.pdf"))

    print("=" * 64)
    print("论文语料重建")
    print("=" * 64)
    print(f"语料目录：{corpus}")
    print(f"数据库　：{DB_PATH}")

    if not pdfs:
        print("\n❌ 语料目录里没有 PDF。先跑：python scripts/fetch_paper_corpus.py")
        return 1

    print(f"\n将灌入 {len(pdfs)} 篇：")
    for p in pdfs:
        print(f"  - {p.name}  ({p.stat().st_size // 1024} KB)")

    if not DB_PATH.exists():
        print(f"\n❌ 找不到数据库：{DB_PATH}")
        return 1

    session = SessionLocal()
    counts = {
        t: session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        for t in _TABLES_IN_ORDER
    }
    print("\n当前库内：")
    for t, n in counts.items():
        print(f"  {t}: {n} 行")

    if not args.yes:
        print("\n" + "-" * 64)
        print("【预演】未写库。将执行：")
        print(f"  1. 备份 {DB_PATH.name} → app.db.bak-<时间戳>-corpus")
        print("  2. 清空三张语料表：")
        for t in _TABLES_IN_ORDER:
            print(f"       - {t}（{counts[t]} 行）")
        print(f"  3. 逐篇 ingest（解析→分块→摘要→落库→建索引），共 {len(pdfs)} 篇")
        print("\n确认无误后加 --yes 重跑。")
        session.close()
        return 0

    # ---------- 真正执行 ----------
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB_PATH.with_name(f"app.db.bak-{stamp}-corpus")
    before = _md5(DB_PATH)
    shutil.copy2(DB_PATH, backup)
    print(f"\n✅ 已备份 → {backup.name}")
    print(f"   原库指纹 {before}")

    print("\n清空旧语料…")
    session.execute(text("DELETE FROM paper_chunk_embeddings"))
    session.execute(text("DELETE FROM paper_chunks"))
    session.execute(text("DELETE FROM papers"))
    session.commit()
    print("   已清空")

    from app.research.paper_agent.agent import build_paper_graph  # noqa: E402

    graph = build_paper_graph()
    ok: list[str] = []
    failed: list[tuple[str, str]] = []
    t_all = time.time()

    print("\n灌入中（每篇含 LLM 摘要与索引，耗时与语料长度相关）…")
    for i, pdf in enumerate(pdfs, 1):
        t0 = time.time()
        try:
            out = graph.invoke({"file_path": str(pdf), "auto_index": True, "db": session})
            summary = out.get("summary", {}) or {}
            print(
                f"  [{i}/{len(pdfs)}] {pdf.stem[:56]}\n"
                f"        chunks={len(out.get('chunks', []) or [])} "
                f"indexed={out.get('indexed_count', 0)} "
                f"conf={summary.get('confidence')} ({time.time() - t0:.1f}s)"
            )
            ok.append(pdf.name)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(pdfs)}] ❌ {pdf.name} → {type(e).__name__}: {str(e)[:150]}")
            failed.append((pdf.name, f"{type(e).__name__}: {e}"))
            session.rollback()

    print(f"\n总耗时 {time.time() - t_all:.1f}s　成功 {len(ok)} / 失败 {len(failed)}")

    print("\n" + "=" * 64)
    print("结果核对")
    print("=" * 64)
    paper_count = session.execute(text("SELECT COUNT(*) FROM papers")).scalar()
    distinct = session.execute(
        text("SELECT COUNT(DISTINCT title) FROM papers")
    ).scalar()
    chunks = session.execute(text("SELECT COUNT(*) FROM paper_chunks")).scalar()
    print(f"papers {paper_count} 行 / distinct title {distinct} / chunks {chunks}")

    print("\n章节分布：")
    for row in session.execute(
        text("SELECT section, COUNT(*) c FROM paper_chunks GROUP BY section ORDER BY c DESC")
    ):
        print(f"  {row[0]}: {row[1]}")

    print("\n按嵌入模型统计向量：")
    for row in session.execute(
        text("SELECT model_name, COUNT(*) FROM paper_chunk_embeddings GROUP BY model_name")
    ):
        print(f"  {row[0]}: {row[1]}")

    session.close()

    after = _md5(DB_PATH)
    print(f"\n新库指纹 {after}")
    print(f"备份保留：{backup.name}（要回滚直接覆盖 app.db）")

    if paper_count != distinct:
        print("\n⚠️ distinct title < 总行数 → 存在重复论文，检查 http 重试或重复 ingest")
    if failed:
        print("\n失败清单：")
        for name, why in failed:
            print(f"  - {name}：{why}")
        return 1

    print("\n完成。验证：GET /api/paper/stats 的 model_name 不应是 hash-384。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
