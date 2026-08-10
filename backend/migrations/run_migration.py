"""Migration runner：通过 SQLAlchemy 执行 SQL 迁移脚本。

兼容 SQLite 与 PostgreSQL。
由于项目未引入 Alembic，用此脚本执行 migrations/*.sql，并支持幂等重跑。

用法：
    cd backend
    python migrations/run_migration.py                    # 执行所有未应用的迁移
    python migrations/run_migration.py --only 0001        # 仅执行指定迁移
    python migrations/run_migration.py --list             # 列出所有迁移
    python migrations/run_migration.py --status           # 查看应用状态
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.db.base import SessionLocal, engine

# ===== 配置 =====
BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
MIGRATIONS_TABLE = "_migrations_applied"


def _is_sqlite() -> bool:
    """判断当前是否为 SQLite 连接。"""
    return settings.database_url.startswith("sqlite")


def ensure_migrations_table() -> None:
    """创建迁移记录表（如不存在）。兼容 SQLite 与 PG。"""
    db = SessionLocal()
    try:
        if _is_sqlite():
            db.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                        name TEXT PRIMARY KEY,
                        applied_at TEXT NOT NULL DEFAULT (datetime('now'))
                    )
                    """
                )
            )
        else:
            db.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                        name VARCHAR(200) PRIMARY KEY,
                        applied_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
        db.commit()
    finally:
        db.close()


def list_applied() -> set[str]:
    """返回已应用的迁移名集合。"""
    ensure_migrations_table()
    db = SessionLocal()
    try:
        rows = db.execute(
            text(f"SELECT name FROM {MIGRATIONS_TABLE}")
        ).fetchall()
        return {r[0] for r in rows}
    finally:
        db.close()


def list_migration_files() -> list[str]:
    """列出 migrations 目录下所有 .sql 文件（按文件名排序）。"""
    if not MIGRATIONS_DIR.exists():
        return []
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [f.name for f in files]


def apply_migration(filename: str, sql: str) -> None:
    """执行单个迁移脚本。

    幂等保护：
    - 用 try-except 捕获 PostgreSQL 重复列/表错误
    - SQLite 重复列错误
    - 应用成功后记录到 _migrations_applied 表
    """
    db = SessionLocal()
    name = filename.removesuffix(".sql")
    try:
        # 逐条执行 SQL 语句
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            db.execute(text(stmt))

        # 记录迁移
        if _is_sqlite():
            db.execute(
                text(
                    f"INSERT OR IGNORE INTO {MIGRATIONS_TABLE} (name) VALUES (:name)"
                ),
                {"name": name},
            )
        else:
            db.execute(
                text(
                    f"INSERT INTO {MIGRATIONS_TABLE} (name) VALUES (:name) "
                    f"ON CONFLICT (name) DO NOTHING"
                ),
                {"name": name},
            )
        db.commit()
        print(f"  ✓ 应用迁移: {filename}")
    except Exception as e:
        err_msg = str(e).lower()
        # 重复列/表 → 视为已应用（幂等）
        if any(kw in err_msg for kw in [
            "duplicate column", "duplicate table",
            "already exists", "duplicate key",
        ]):
            print(f"  - 跳过迁移（已应用）: {filename}")
            db.rollback()
            # 确保记录存在
            try:
                if _is_sqlite():
                    db.execute(
                        text(
                            f"INSERT OR IGNORE INTO {MIGRATIONS_TABLE} (name) VALUES (:name)"
                        ),
                        {"name": name},
                    )
                else:
                    db.execute(
                        text(
                            f"INSERT INTO {MIGRATIONS_TABLE} (name) VALUES (:name) "
                            f"ON CONFLICT (name) DO NOTHING"
                        ),
                        {"name": name},
                    )
                db.commit()
            except Exception:
                db.rollback()
        else:
            print(f"  ✗ 迁移失败: {filename} — {e}")
            db.rollback()
            raise
    finally:
        db.close()


def run_all(only: str | None = None) -> None:
    """执行迁移。"""
    # 确保数据库表存在（首次执行时 _migrations_applied 不存在）
    ensure_migrations_table()

    files = list_migration_files()
    if not files:
        print("（无迁移脚本）")
        return

    applied = list_applied()

    for filename in files:
        if only and not filename.startswith(only):
            continue
        name = filename.removesuffix(".sql")
        if name in applied and not only:
            continue  # 跳过已应用（除非 --only 强制）

        sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
        apply_migration(filename, sql)


def show_status() -> None:
    """显示迁移应用状态。"""
    ensure_migrations_table()

    applied = list_applied()
    files = list_migration_files()

    print(f"迁移目录: {MIGRATIONS_DIR}")
    print(f"数据库 URL: {settings.database_url}")
    print(f"数据库类型: {'SQLite' if _is_sqlite() else 'PostgreSQL'}")
    print()
    print(f"{'迁移文件':<50} {'状态':<10}")
    print("-" * 60)
    for f in files:
        name = f.removesuffix(".sql")
        status = "✓ 已应用" if name in applied else "○ 未应用"
        print(f"{f:<50} {status}")


def main() -> None:
    parser = argparse.ArgumentParser(description="数据库迁移工具（SQLite + PG 兼容）")
    parser.add_argument("--only", type=str, help="仅执行指定迁移（前缀匹配）")
    parser.add_argument("--list", action="store_true", help="列出所有迁移文件")
    parser.add_argument("--status", action="store_true", help="查看迁移应用状态")
    args = parser.parse_args()

    if args.list:
        files = list_migration_files()
        print("迁移文件列表:")
        for f in files:
            print(f"  - {f}")
        return

    if args.status:
        show_status()
        return

    run_all(args.only)


if __name__ == "__main__":
    main()
