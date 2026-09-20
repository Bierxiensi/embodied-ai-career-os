"""Migration runner：通过 SQLAlchemy 执行 SQL 迁移脚本。

兼容 SQLite 与 PostgreSQL。
由于项目未引入 Alembic，用此脚本执行 migrations/*.sql，并支持幂等重跑。

用法：
    cd backend
    python migrations/run_migration.py                    # 执行所有未应用的迁移
    python migrations/run_migration.py --only 0001        # 仅执行指定迁移
    python migrations/run_migration.py --list             # 列出所有迁移
    python migrations/run_migration.py --status           # 查看应用状态

================================================================================
方言兼容策略（2026-09-16 补齐）
================================================================================
本文件此前声称「兼容 SQLite 与 PostgreSQL」，但只对 ``_migrations_applied``
的记账语句做了方言分支，**迁移正文原样执行**。而 migrations/*.sql 是按 SQLite
写法撰写的（自增主键、``datetime('now')`` 默认值），在 PostgreSQL 上直接语法
报错 —— 也就是 PG 部署走 ``run_migration.py`` 升级这条路实际上是断的。

为什么必须有方言分支，而不把 .sql 写成「两边都认的通用 SQL」：
    SQL 里不存在这样的主键自增写法。SQLite 不认 ``SERIAL`` / ``IDENTITY``，
    PostgreSQL 不认 ``AUTOINCREMENT``（``INTEGER PRIMARY KEY`` 在 SQLite 会
    自动取 rowid，在 PG 却要求调用方显式给值）。二者不可调和。

分支为什么放在执行器，而不是散落到每个 .sql：
    1. 单一收口 —— 新增迁移自动获得兼容，作者不必记得写两遍；
    2. 可单测 —— 翻译是纯函数，不需要任何数据库即可断言（见
       tests/test_migration_dialect_compat.py）；
    3. 不回改已应用的迁移文件 —— 改名不动内容，避免「记录名相同、内容不同」的漂移。
    代价是：数据库实际执行的 DDL 与文件里的字面文本不逐字相同，所以这里必须
    把翻译规则写清楚、并在翻译不彻底时**报错而不是放行**。

翻译采取「精确短语替换 + 残留检测」：只替换白名单里的确切写法（不做通用正则
改写，避免误伤同名列或字符串字面量）；翻译后若仍存在已知的 SQLite 专属写法，
直接抛 ``UnsupportedSqliteSyntaxError``，绝不把可疑 SQL 交给数据库去执行。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import text

# 允许 `python migrations/run_migration.py` 直接运行：
# 直接执行脚本时 sys.path[0] 是 migrations/ 而不是 backend/，`import app` 会失败
# （文档里写的用法原本跑不通，只有 `python -m migrations.run_migration` 才行）。
# 与 backend/scripts/*.py 保持同一套 sys.path 注入约定。
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.base import SessionLocal, engine  # noqa: E402

# ===== 配置 =====
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
MIGRATIONS_TABLE = "_migrations_applied"


# ===== 方言判定 =====
#
# 以 SQLAlchemy engine 解析出的方言名为准，而不是给 URL 做字符串前缀匹配：
# engine.dialect.name 是对连接串**解析后**的结果，postgresql+psycopg2://、
# postgres:// 等别名写法都能正确识别，且不需要建立连接（建 engine 时已确定）。
# 保留 URL 前缀作为兜底，仅用于 engine 意外不可用的极端情况。

_SQLITE_DIALECT = "sqlite"


def _dialect_name() -> str:
    """当前连接的目标方言名（sqlite / postgresql / ...）。"""
    try:
        return engine.dialect.name
    except Exception:  # pragma: no cover - 兜底分支，正常路径不会走到
        return settings.database_url.split(":", 1)[0].split("+", 1)[0]


def _is_sqlite() -> bool:
    """判断当前是否为 SQLite 连接。"""
    return _dialect_name() == _SQLITE_DIALECT


# ===== 迁移正文的方言翻译 =====


class UnsupportedSqliteSyntaxError(RuntimeError):
    """迁移脚本里出现无法自动翻译成 PostgreSQL 的 SQLite 专属写法。

    刻意抛错而不是原样放行：放行的结果是 PG 在迁移中途失败，且由于
    ``apply_migration`` 逐条执行、失败即回滚，会留下「部分迁移已记录、
    部分表缺失」的静默不一致。宁可在这里明确失败。
    """


# 精确替换表：(SQLite 写法, PostgreSQL 等价写法)。
#
# 只放**确切短语**，不放正则、不放单词级替换 —— 例如不把裸 "AUTOINCREMENT"
# 作为替换目标，因为那会命中注释、或未来某个同名列。这条纪律和项目里
# 「别名匹配不要加宽泛词」是同一类教训（见 skill_profile 别名踩坑记录）。
_PG_TRANSLATIONS: tuple[tuple[str, str], ...] = (
    # 自增主键：PG 用 SERIAL（等价于 integer + 序列 + 默认值）
    ("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY"),
    # 时间戳默认值：CURRENT_TIMESTAMP 在两个方言里都合法，是真正的可移植写法
    ("datetime('now')", "CURRENT_TIMESTAMP"),
    ('datetime("now")', "CURRENT_TIMESTAMP"),
)

# 翻译后仍不允许出现的 SQLite 专属写法（全大写比对，忽略注释行）。
_SQLITE_ONLY_TOKENS: tuple[str, ...] = (
    "AUTOINCREMENT",
    "DATETIME(",
    "STRFTIME(",
    "JULIANDAY(",
    "INSERT OR IGNORE",
    "INSERT OR REPLACE",
    "PRAGMA ",
    "WITHOUT ROWID",
    "SQLITE_",
)


def _strip_line_comments(sql: str) -> str:
    """去掉整行注释。

    残留检测必须忽略注释：注释里写「SQLite 的 AUTOINCREMENT 写法」是正常的
    说明文字，不该被判成不合格的 SQL。
    """
    return "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )


def find_untranslatable_syntax(sql: str) -> list[str]:
    """返回 SQL 中仍存在的 SQLite 专属写法（忽略注释行）。纯函数。"""
    body = _strip_line_comments(sql).upper()
    return [token for token in _SQLITE_ONLY_TOKENS if token in body]


def translate_sql_for_postgres(sql: str) -> str:
    """把 SQLite 写法的迁移正文翻译成 PostgreSQL 等价写法。

    纯函数：不读环境、不碰数据库、无副作用，因此可直接单测。
    """
    translated = sql
    for sqlite_form, pg_form in _PG_TRANSLATIONS:
        translated = translated.replace(sqlite_form, pg_form)

    residue = find_untranslatable_syntax(translated)
    if residue:
        raise UnsupportedSqliteSyntaxError(
            "迁移脚本含无法自动翻译为 PostgreSQL 的 SQLite 专属写法："
            + "、".join(residue)
            + "。请改写为可翻译形式（如用 INTEGER PRIMARY KEY AUTOINCREMENT "
            "表示自增主键、用 datetime('now') 表示时间戳默认值），或为该迁移"
            "显式增加方言分支。"
        )
    return translated


def translate_sql_for_dialect(sql: str, dialect: str) -> str:
    """按目标方言转换迁移正文。

    SQLite 以及未知方言一律原样返回 —— 不认识就不猜，避免把一个方言的
    语法悄悄改写成另一个方言的。
    """
    if dialect.startswith("postgres"):
        return translate_sql_for_postgres(sql)
    return sql


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

    执行前按目标方言转换正文（见 translate_sql_for_dialect）。

    幂等保护：
    - 用 try-except 捕获 PostgreSQL 重复列/表错误
    - SQLite 重复列错误
    - 应用成功后记录到 _migrations_applied 表
    """
    db = SessionLocal()
    name = filename.removesuffix(".sql")
    try:
        # 方言适配：PG 上把 SQLite 写法的迁移正文翻译成等价写法；SQLite 原样执行。
        # 这是本次修复的核心 —— 此前迁移正文未经任何转换就执行，PG 直接语法报错。
        sql = translate_sql_for_dialect(sql, _dialect_name())

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
    print(f"数据库类型: {_dialect_name()}")
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
