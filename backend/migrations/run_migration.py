"""Migration runner：执行 SQL 迁移脚本。

由于项目未引入 Alembic（SQLite 开发态，schema 简单），
用此脚本执行 migrations/*.sql，并支持幂等重跑。

用法：
    cd backend
    python migrations/run_migration.py                    # 执行所有未应用的迁移
    python migrations/run_migration.py --only 0001        # 仅执行指定迁移
    python migrations/run_migration.py --list             # 列出所有迁移
    python migrations/run_migration.py --status           # 查看应用状态
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# ===== 配置 =====
BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "data" / "app.db"
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
MIGRATIONS_TABLE = "_migrations_applied"


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    """创建迁移记录表（如不存在）。"""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def list_applied(conn: sqlite3.Connection) -> set[str]:
    """返回已应用的迁移名集合。"""
    ensure_migrations_table(conn)
    rows = conn.execute(
        f"SELECT name FROM {MIGRATIONS_TABLE}"
    ).fetchall()
    return {r[0] for r in rows}


def list_migration_files() -> list[str]:
    """列出 migrations 目录下所有 .sql 文件（按文件名排序）。"""
    if not MIGRATIONS_DIR.exists():
        return []
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [f.name for f in files]


def apply_migration(conn: sqlite3.Connection, filename: str, sql: str) -> None:
    """执行单个迁移脚本。

    幂等保护：
    - SQLite 不支持"ADD COLUMN IF NOT EXISTS"，重复执行会报错
    - 用 try-except 捕获 duplicate column 错误，视为已应用
    - 应用成功后记录到 _migrations_applied 表
    """
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    name = filename.removesuffix(".sql")

    try:
        for stmt in statements:
            if stmt:
                conn.execute(stmt)
        conn.execute(
            f"INSERT INTO {MIGRATIONS_TABLE} (name) VALUES (?) "
            f"ON CONFLICT(name) DO NOTHING",
            (name,),
        )
        conn.commit()
        print(f"  ✓ 应用迁移: {filename}")
    except sqlite3.OperationalError as e:
        # 重复列错误视为已应用（幂等）
        if "duplicate column" in str(e).lower():
            print(f"  - 跳过迁移（已应用）: {filename}")
            conn.rollback()
            # 确保记录存在
            conn.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (name) VALUES (?) "
                f"ON CONFLICT(name) DO NOTHING",
                (name,),
            )
            conn.commit()
        else:
            print(f"  ✗ 迁移失败: {filename} — {e}")
            conn.rollback()
            raise


def run_all(only: str | None = None) -> None:
    """执行迁移。"""
    if not DB_PATH.exists():
        print(f"✗ 数据库不存在: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        applied = list_applied(conn)
        files = list_migration_files()

        if not files:
            print("（无迁移脚本）")
            return

        for filename in files:
            if only and not filename.startswith(only):
                continue
            name = filename.removesuffix(".sql")
            if name in applied and not only:
                continue  # 跳过已应用（除非 --only 强制）

            sql = (MIGRATIONS_DIR / filename).read_text(encoding="utf-8")
            apply_migration(conn, filename, sql)
    finally:
        conn.close()


def show_status() -> None:
    """显示迁移应用状态。"""
    if not DB_PATH.exists():
        print(f"✗ 数据库不存在: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        applied = list_applied(conn)
        files = list_migration_files()

        print(f"迁移目录: {MIGRATIONS_DIR}")
        print(f"数据库: {DB_PATH}")
        print()
        print(f"{'迁移文件':<50} {'状态':<10}")
        print("-" * 60)
        for f in files:
            name = f.removesuffix(".sql")
            status = "✓ 已应用" if name in applied else "○ 未应用"
            print(f"{f:<50} {status}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="数据库迁移工具")
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
