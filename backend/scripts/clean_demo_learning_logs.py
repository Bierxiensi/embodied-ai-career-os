# backend/scripts/clean_demo_learning_logs.py
"""Y7：清理 learning_logs 中 2026-09-10 的演示数据（14 条重复 "ROS2 publisher"）。

2026-09-24 前置裁决：清（先备份）。谓词刻意保守 —— 必须同时满足
「2026-09-10 当天」且「内容含演示指纹」才删，宁可漏删不可错删。

用法：
    python scripts/clean_demo_learning_logs.py --dry-run   # 只看将删几条
    python scripts/clean_demo_learning_logs.py --yes       # 备份后删除
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.models.learning_log import LearningLog  # noqa: E402

DEMO_DAY = date(2026, 9, 10)
DEMO_FINGERPRINT = "ROS2 publisher"


def is_demo_log(content: str, created_at: datetime) -> bool:
    """演示日志谓词：演示日 + 演示指纹，双条件缺一不可。"""
    return created_at.date() == DEMO_DAY and DEMO_FINGERPRINT in (content or "")


def _db_path_from_url(url: str) -> Path:
    """从 settings.database_url 解析 sqlite 文件路径（与会话实际写入的库一致）。

    解析规则对齐 backend/tests/conftest.py::_sqlite_path：剥离 `sqlite:///` 前缀，
    相对路径按 backend/ 解析。非 sqlite 或 :memory: 直接报错 —— 此时无法安全备份，
    宁可中止也不猜路径。
    """
    if not url.startswith("sqlite"):
        raise SystemExit(f"DATABASE_URL 非 sqlite，无法定位库文件备份：{url!r}")
    raw = url.split("sqlite:///", 1)[-1]
    if not raw or raw.startswith(":memory:"):
        raise SystemExit(f"DATABASE_URL 为内存库，无库文件可备份：{url!r}")
    p = Path(raw)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    return p.resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="确认删除（先备份库文件）")
    parser.add_argument("--dry-run", action="store_true", help="只统计不删除")
    args = parser.parse_args()

    db_path = _db_path_from_url(settings.database_url)
    db = SessionLocal()
    try:
        rows = db.query(LearningLog).all()
        victims = [r for r in rows if is_demo_log(r.content, r.created_at)]
        print(f"learning_logs 总数={len(rows)}，命中演示谓词={len(victims)}")
        for r in victims:
            print(f"  [del] id={r.id} {r.created_at.isoformat()} {r.content[:30]}")

        if args.dry_run or not args.yes:
            print("未删除（--dry-run 或缺 --yes）。")
            return 0

        backup = db_path.with_name(f"{db_path.name}.bak-{datetime.now():%Y%m%d-%H%M%S}-learnlogs")
        shutil.copy2(db_path, backup)
        print(f"已备份：{backup}")

        for r in victims:
            db.delete(r)
        db.commit()
        remaining = db.query(LearningLog).count()
        print(f"删除 {len(victims)} 条，剩余 {remaining} 条。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
