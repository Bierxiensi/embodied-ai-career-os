"""迁移路径的方言兼容性测试（SQLite 实测 + PostgreSQL 分支验证）。

================================================================================
本次修复的背景
================================================================================
``migrations/run_migration.py`` 的 docstring 一直声称「兼容 SQLite 与 PostgreSQL」，
但迁移**正文**此前未经任何方言转换就直接送给数据库执行。migrations/*.sql 是按
SQLite 写法撰写的（``INTEGER PRIMARY KEY AUTOINCREMENT``、``DEFAULT (datetime('now'))``），
在 PostgreSQL 上直接语法报错 —— 也就是说「PG 部署经 run_migration.py 升级」
这条路实际上是断的。

0016 / 0017 只是恰好被引用到的两个例子：0002、0009、0010、0012、0013 同样含
SQLite 专属写法。所以修复落在执行器（单一收口），而不是逐个改写 .sql ——
改文件只能治标，下一个新增迁移还会踩同一个坑。

================================================================================
本文件证明什么、不证明什么（请如实理解覆盖强度）
================================================================================
证明（无需 PostgreSQL 即可客观复现）：
  1. 翻译是纯函数 —— SQLite 写法被换成 PG 等价写法；无法翻译的写法**抛错**
     而不是被静默放行（静默放行会让 PG 在迁移中途失败，由于逐条执行 + 失败即
     回滚，会留下「部分迁移已记录、部分表缺失」的静默不一致）。
  2. migrations/*.sql 全目录扫描后无 SQLite 残留 —— 未来新增迁移若埋回同一个
     坑，这里会变红。
  3. 迁移建表在真实 SQLite 上可执行、可重复执行（幂等），且产出的表**能被 ORM
     正常读写**、唯一索引真的拦得住第二个当前模式。
  4. PG 分支下发给数据库的 SQL 确实是翻译后的版本（记录型假会话断言），
     并有反证：SQLite 分支不翻译 —— 证明方言分支真的存在。
  5. （可选，需 pglast）翻译后的 SQL 被 **PostgreSQL 官方语法解析器**接受。
     实测：修复前有 7 个迁移文件被拒（0002/0009/0010/0012/0013/0016/0017，
     全部是 ``syntax error at or near "AUTOINCREMENT"``），修复后 0 个。

**不证明**：开发机没有可用的 PostgreSQL 服务、也没有 Docker，因此**没有做真实
PG 执行**。上述第 5 条证明的是「语法合法」（libpg_query 只做语法解析，不做
目录/类型等语义检查），仍不等于「在真实 PG 上建表成功」。要闭合这一点，需在
有 PG 的环境执行：

    cd backend && python migrations/run_migration.py --status   # 方言应识别为 postgresql
    cd backend && python migrations/run_migration.py            # 实际升级
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import CareerMode, ModeTransition
from migrations import run_migration as rm

# 本次修复直接涉及的三条迁移：建表 → 建历史表 → 建唯一索引
CAREER_MODE_MIGRATIONS = (
    "0016_career_modes.sql",
    "0017_mode_transitions.sql",
    "0018_career_modes_current_unique.sql",
)

# career_mode 模块的两张表，用于结构一致性比对
CAREER_MODE_TABLES = ("career_modes", "mode_transitions")


def _read_migration(filename: str) -> str:
    """读取迁移文件正文。"""
    return (rm.MIGRATIONS_DIR / filename).read_text(encoding="utf-8")


# ==============================================================================
# 1. 翻译器是纯函数：SQLite 写法 → PG 等价写法
# ==============================================================================


def test_translate_autoincrement_to_serial():
    sql = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL);"
    out = rm.translate_sql_for_postgres(sql)
    assert "SERIAL PRIMARY KEY" in out
    assert "AUTOINCREMENT" not in out.upper()


def test_translate_datetime_now_default_to_current_timestamp():
    sql = "CREATE TABLE t (created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')));"
    out = rm.translate_sql_for_postgres(sql)
    assert "DEFAULT (CURRENT_TIMESTAMP)" in out
    assert "DATETIME(" not in out.upper()


def test_translate_double_quoted_datetime_now():
    """SQLite 允许双引号包字符串，PG 侧同样要能翻译。"""
    sql = 'CREATE TABLE t (created_at TIMESTAMP DEFAULT (datetime("now")));'
    out = rm.translate_sql_for_postgres(sql)
    assert "DATETIME(" not in out.upper()
    assert "CURRENT_TIMESTAMP" in out


def test_translate_is_idempotent():
    """翻译两次等于翻译一次 —— 否则重复执行会累积污染。"""
    once = rm.translate_sql_for_postgres(_read_migration("0016_career_modes.sql"))
    assert rm.translate_sql_for_postgres(once) == once


def test_translate_leaves_already_portable_sql_untouched():
    """0018 本来就只用可移植语法（部分索引两方言都支持），不应被改动。"""
    sql = _read_migration("0018_career_modes_current_unique.sql")
    assert rm.translate_sql_for_postgres(sql) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "PRAGMA journal_mode = WAL",
        "INSERT OR IGNORE INTO t (a) VALUES (1)",
        "INSERT OR REPLACE INTO t (a) VALUES (1)",
        "CREATE TABLE t (a TEXT) WITHOUT ROWID",
        "CREATE TABLE t (a TEXT DEFAULT (strftime('%s', 'now')))",
        "CREATE TABLE t (a TEXT DEFAULT (julianday('now')))",
    ],
)
def test_translate_raises_on_untranslatable_sqlite_syntax(sql):
    """翻译不彻底必须报错，不能放行 —— 放行等于把失败推迟到 PG 上。"""
    with pytest.raises(rm.UnsupportedSqliteSyntaxError):
        rm.translate_sql_for_postgres(sql)


def test_translate_does_not_raise_on_sqlite_tokens_inside_comments():
    """注释里提到 SQLite 写法是正常说明文字，不该被判成不合格的 SQL。"""
    sql = (
        "-- 本表沿用 INTEGER PRIMARY KEY AUTOINCREMENT 与 datetime('now') 的写法\n"
        "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT);"
    )
    out = rm.translate_sql_for_postgres(sql)  # 不应抛错
    assert "SERIAL PRIMARY KEY" in out


def test_residue_check_ignores_comments():
    assert rm.find_untranslatable_syntax("-- 用 AUTOINCREMENT 自增\nSELECT 1") == []
    assert rm.find_untranslatable_syntax("SELECT 1") == []
    assert rm.find_untranslatable_syntax("CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT)") == [
        "AUTOINCREMENT"
    ]


def test_dialect_dispatcher_only_translates_postgres():
    """SQLite 与未知方言一律原样返回 —— 不认识就不猜。"""
    sql = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT);"
    assert rm.translate_sql_for_dialect(sql, "sqlite") == sql
    assert rm.translate_sql_for_dialect(sql, "mysql") == sql
    assert "SERIAL PRIMARY KEY" in rm.translate_sql_for_dialect(sql, "postgresql")


def test_dialect_detection_reflects_actual_engine():
    """方言判定取自 SQLAlchemy engine，而非给 URL 做前缀匹配。"""
    assert rm._dialect_name() == "sqlite"
    assert rm._is_sqlite() is True


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg2://u:p@127.0.0.1:5432/db",
        "postgresql://u:p@127.0.0.1:5432/db",
    ],
)
def test_dialect_detection_recognizes_postgresql_urls(url):
    """真实 PG 连接串（含 +driver 与裸写两种）必须被识别为 postgresql。

    上面的 PG 断言都靠 monkeypatch 方言名，这一条补上「真实 engine 解析」的
    那一环，否则整条链路的起点是假的。不建立连接，因此无需 PG 服务。
    """
    probe = create_engine(url)
    try:
        assert probe.dialect.name == "postgresql"
        # 用真实解析出的方言名走一遍分发，确认确实触发翻译
        assert "SERIAL PRIMARY KEY" in rm.translate_sql_for_dialect(
            "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT)",
            probe.dialect.name,
        )
    finally:
        probe.dispose()


# ==============================================================================
# 2. 全目录扫描：每一条迁移都必须能翻译成无残留的 PG SQL
# ==============================================================================


@pytest.mark.parametrize("filename", rm.list_migration_files())
def test_every_migration_translates_without_sqlite_residue(filename):
    out = rm.translate_sql_for_postgres(_read_migration(filename))
    assert rm.find_untranslatable_syntax(out) == [], f"{filename} 翻译后仍含 SQLite 专属写法"


def test_career_mode_migrations_are_actually_swept():
    """防止上面的全目录扫描退化成空集合的假绿。"""
    assert set(CAREER_MODE_MIGRATIONS) <= set(rm.list_migration_files())


# ==============================================================================
# 3. 方言分支实测：断言「实际下发给数据库的 SQL」
# ==============================================================================


class _RecordingSession:
    """只记录下发的 SQL，不连数据库。

    用途：在不具备 PostgreSQL 服务的情况下，验证 PG 分支实际发出的是翻译后的
    DDL，而不是原样透传。
    """

    def __init__(self, log: list[str]) -> None:
        self._log = log

    def execute(self, statement, params=None):  # noqa: ANN001, ARG002
        self._log.append(str(statement))
        return None

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass


def _capture_dispatched_sql(monkeypatch, dialect: str, filename: str) -> str:
    """在指定方言下执行迁移，返回其下发给数据库的全部 SQL。"""
    log: list[str] = []
    monkeypatch.setattr(rm, "_dialect_name", lambda: dialect)
    monkeypatch.setattr(rm, "SessionLocal", lambda: _RecordingSession(log))
    rm.apply_migration(filename, _read_migration(filename))
    return "\n".join(log)


def test_postgres_branch_dispatches_translated_ddl(monkeypatch):
    ddl = _capture_dispatched_sql(monkeypatch, "postgresql", "0016_career_modes.sql")
    assert "SERIAL PRIMARY KEY" in ddl
    assert "DEFAULT (CURRENT_TIMESTAMP)" in ddl
    assert "AUTOINCREMENT" not in ddl.upper()
    assert "DATETIME(" not in ddl.upper()


def test_postgres_branch_translates_transitions_table(monkeypatch):
    ddl = _capture_dispatched_sql(monkeypatch, "postgresql", "0017_mode_transitions.sql")
    assert "SERIAL PRIMARY KEY" in ddl
    assert "CURRENT_TIMESTAMP" in ddl
    assert "AUTOINCREMENT" not in ddl.upper()


def test_sqlite_branch_dispatches_original_ddl(monkeypatch):
    """反证：SQLite 分支不翻译。

    没有这一条，上面的 PG 断言无法区分「方言分支生效」与「永远翻译」——
    后者在 SQLite 上会直接建表失败（SERIAL 不是合法 SQLite 类型）。
    """
    ddl = _capture_dispatched_sql(monkeypatch, "sqlite", "0016_career_modes.sql")
    assert "AUTOINCREMENT" in ddl.upper()
    assert "SERIAL PRIMARY KEY" not in ddl


# ==============================================================================
# 4. 迁移路径在真实 SQLite 上跑通 + 与 ORM 路径功能等价
# ==============================================================================


def _temp_sqlite_engine(tmp_path, name: str):
    return create_engine(f"sqlite:///{(tmp_path / name).as_posix()}")


def _apply_career_mode_migrations(engine, monkeypatch) -> None:
    """把 career_mode 的三条迁移应用到指定引擎（会话与方言一并重定向）。"""
    monkeypatch.setattr(
        rm, "SessionLocal", sessionmaker(bind=engine, autoflush=False, autocommit=False)
    )
    monkeypatch.setattr(rm, "_dialect_name", lambda: "sqlite")
    rm.ensure_migrations_table()
    for filename in CAREER_MODE_MIGRATIONS:
        rm.apply_migration(filename, _read_migration(filename))


def _index_names(inspector, table: str) -> set[str]:
    """表上的索引名（排除 SQLite 内部自动索引，避免方言版本差异干扰）。"""
    return {
        i["name"]
        for i in inspector.get_indexes(table)
        if not str(i["name"]).startswith("sqlite_autoindex")
    }


def test_career_mode_migrations_run_on_sqlite_and_are_idempotent(tmp_path, monkeypatch):
    """迁移在 SQLite 上可执行，且重复执行无副作用（全部语句带 IF NOT EXISTS）。"""
    engine = _temp_sqlite_engine(tmp_path, "mig.db")
    try:
        _apply_career_mode_migrations(engine, monkeypatch)
        _apply_career_mode_migrations(engine, monkeypatch)  # 第二遍：幂等

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "career_modes" in tables
        assert "mode_transitions" in tables
        assert "ux_career_modes_current" in _index_names(inspector, "career_modes")
    finally:
        engine.dispose()


def test_migration_built_schema_is_orm_usable_and_enforces_single_current(tmp_path, monkeypatch):
    """迁移建出的表必须能被 ORM 正常读写，且唯一索引真拦得住第二个当前模式。

    这一条比「比对 inspector 文本」更有意义：后者只说明结构相似，而这里验证的是
    迁移路径产出的库在**功能上**与 ORM 路径等价。顺带实证 0018 那句
    ``WHERE is_current = TRUE`` 在 SQLite 上确实生效（TRUE 自 3.23 起是 1 的别名）。
    """
    engine = _temp_sqlite_engine(tmp_path, "mig_orm.db")
    try:
        _apply_career_mode_migrations(engine, monkeypatch)

        session = sessionmaker(bind=engine)()
        try:
            session.add(
                CareerMode(
                    key="a",
                    name="模式 A",
                    objective="目标 A",
                    active_track_keys=["llm"],
                    frozen_track_keys=[],
                    is_current=True,
                )
            )
            session.add(ModeTransition(from_mode=None, to_mode="a", note="初始化"))
            session.commit()

            assert session.query(CareerMode).count() == 1
            assert session.query(CareerMode).one().active_track_keys == ["llm"]
            assert session.query(ModeTransition).one().note == "初始化"

            # 第二个当前模式必须被数据库拒绝（不变量由 DB 保证，而非调用方自觉）
            session.add(
                CareerMode(
                    key="b",
                    name="模式 B",
                    objective="目标 B",
                    active_track_keys=[],
                    frozen_track_keys=[],
                    is_current=True,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
        finally:
            session.close()
    finally:
        engine.dispose()


def test_migration_schema_columns_and_indexes_match_orm(tmp_path, monkeypatch):
    """两条建表路径（迁移 / create_all）产出相同的列与索引。

    只比对列名与索引名，不比对类型字符串：SQLite 里 ``TIMESTAMP`` 与 ORM 渲染的
    ``DATETIME`` 类型名不同但亲和性一致，且 ORM 的 bind/result 处理器不依赖列声明
    类型，因此字符串差异不构成行为差异。真正重要的是「列有没有、索引在不在」。
    """
    mig_engine = _temp_sqlite_engine(tmp_path, "mig_schema.db")
    orm_engine = _temp_sqlite_engine(tmp_path, "orm_schema.db")
    try:
        _apply_career_mode_migrations(mig_engine, monkeypatch)

        from app.db.base import Base

        Base.metadata.create_all(bind=orm_engine)

        mig_inspector, orm_inspector = inspect(mig_engine), inspect(orm_engine)
        for table in CAREER_MODE_TABLES:
            assert [c["name"] for c in mig_inspector.get_columns(table)] == [
                c["name"] for c in orm_inspector.get_columns(table)
            ], f"{table} 的列不一致"
            assert _index_names(mig_inspector, table) == _index_names(
                orm_inspector, table
            ), f"{table} 的索引不一致"
    finally:
        mig_engine.dispose()
        orm_engine.dispose()


# ==============================================================================
# 5. 可选加强层：用真实 PostgreSQL 语法解析器校验（依赖 pglast，缺失则跳过）
# ==============================================================================
#
# pglast 绑定 PostgreSQL 官方语法（libpg_query），装了它就能把「PG 侧可执行」
# 从「语法等价 + 人工核对」升级为「真实 PG 语法解析接受」。
#
# 刻意用 importorskip 而不是把它写成项目依赖：本仓库的运行时依赖应保持精简，
# 这一层是**可选加强**而非准入条件。装了（或用 PYTHONPATH 指向它）即生效：
#     pip install pglast
# 实测结果见交付说明 —— 修复前有 7 个迁移文件（0002/0009/0010/0012/0013/0016/0017）
# 被 PG 拒绝，修复后 0 个。


def _pg_parser():
    """返回 PostgreSQL 语法解析函数；未安装 pglast 时跳过当前测试。"""
    return pytest.importorskip(
        "pglast", reason="未安装 pglast（可选加强层，非项目依赖）"
    ).parse_sql


def test_pg_grammar_rejects_sqlite_only_syntax():
    """反证：解析器确实能识别 SQLite 专属写法，不是「什么都收」。

    用合成语句而非具体迁移文件，避免测试与某个文件的内容绑定。
    """
    parse_sql = _pg_parser()

    sqlite_only = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT)"
    translated = rm.translate_sql_for_postgres(sqlite_only)

    rejected = False
    try:
        parse_sql(sqlite_only)
    except Exception:  # noqa: BLE001 - 只关心「被拒绝」这件事本身
        rejected = True
    assert rejected, "PostgreSQL 语法解析器竟然接受了 AUTOINCREMENT，测试前提失效"

    # 同一条语句翻译后必须被接受 —— 翻译是有效的
    parse_sql(translated)
    assert "SERIAL PRIMARY KEY" in translated


def test_translated_migrations_are_accepted_by_pg_grammar():
    """全部迁移翻译后，逐条语句交给 PostgreSQL 官方语法解析器。"""
    parse_sql = _pg_parser()

    failures: list[str] = []
    for filename in rm.list_migration_files():
        sql = rm.translate_sql_for_postgres(_read_migration(filename))
        for stmt in (s.strip() for s in sql.split(";") if s.strip()):
            try:
                parse_sql(stmt)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{filename}: {exc}")

    assert failures == [], "翻译后的 SQL 被 PostgreSQL 语法解析器拒绝：" + " | ".join(failures)
