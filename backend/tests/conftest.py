"""pytest 全局夹具：强制全部测试使用隔离的临时数据库。

================================================================================
背景（2026-09-10 系统审计发现，P0 隐患）
================================================================================
本目录长期**缺少 conftest.py**，导致绝大多数测试直接落到开发库
``backend/data/app.db``：

- ``test_report_engine.py`` 等 20+ 个文件用 ``with TestClient(app) as client:``
  → 触发 app 生命周期 → ``init_db()`` → 读写开发库
- ``test_e2e_learning_loop.py`` / ``test_agent_closure.py`` 还硬编码过 Linux 容器
  路径 ``/workspace/embodied-ai-career-os/backend/data/app.db``

后果：**每跑一次 pytest，就往真实数据库里灌一批 "M Test Project"**。
累积结果（审计实测）：214 个项目（真实仅 2 个）、178 个里程碑、
393 条 agent_runs、292 个任务（单个任务最多重复 29 次）。

================================================================================
隔离机制
================================================================================
``app/db/base.py`` 在 **import 时**就调用 ``_build_engine()`` 读取
``settings.database_url``；而 ``settings`` 由 ``Settings.from_env()`` 在 import 时
读 ``os.getenv("DATABASE_URL")``。

因此只要在**本文件模块级**设置 ``DATABASE_URL`` —— conftest.py 的 import 早于
任何 ``test_*.py`` —— 全量测试就会落到临时库。

``app/core/config.py`` 的 ``load_dotenv`` 默认**不覆盖已存在的环境变量**，
所以此处设置的值优先，不会被 ``.env`` 里的 DATABASE_URL 冲掉。

参考实现：``tests/test_paper_agent_e2e.py`` 一直是对的（它的 docstring 明写
"不污染开发态 data/app.db"），本文件把这个范式推广到全量测试。
2026-09-10 起，paper 系列 5 个文件也统一改为依赖本文件，不再各自维护临时库。
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

# ⚠️ 必须在任何 app.* 导入之前执行 —— 这就是它写在模块级而非 fixture 里的原因。
_TMP_ROOT = Path(tempfile.mkdtemp(prefix="career-os-tests-"))
_TEST_DB = _TMP_ROOT / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"

# ── LLM 隔离：钉死为 mock，禁止测试依赖开发者本地 .env 的 LLM_PROVIDER ──────────
#
# 背景（2026-09-23 实测事故）：`.env` 里把 LLM_PROVIDER 从 mock 换成真实 provider
# （小米 MiMo）后，全量测试立刻出现 5 个失败：
#   - tests/test_github_service.py::test_analyze_commit_mock / test_analyze_commit_empty_files
#   - tests/test_quiz_api.py::test_start_degrades_to_open_when_llm_unavailable（名字就写着
#     "llm_unavailable"，前提被打破）
#   - tests/test_quiz_api.py 的另外两例（出题数量/聚合结果随真 LLM 而变）
# 这些用例是按 **mock 语义**写的，一旦真的连上外部 LLM 就既不稳定（模型输出每次不同）、
# 又昂贵（每次 ~5-10s）、还依赖网络与额度。
#
# 与上面 DATABASE_URL 同理：测试的输入必须完全由测试自己决定。
# 需要验证真实 provider 装配的用例，请用 monkeypatch 改 settings（见
# tests/test_llm_factory_providers.py），不要依赖环境变量。
os.environ["LLM_PROVIDER"] = "mock"

# 开发库绝对路径，供守卫断言比对
_DEV_DB = (Path(__file__).resolve().parents[1] / "data" / "app.db").resolve()

# ── 需要「运行中的后端 :8000」的 E2E 脚本，不是单元测试 ─────────────────────
# 它们通过 requests 发真实 HTTP 请求，**conftest 的 DATABASE_URL 隔离管不到它们**
# （请求由另起的外部后端进程处理，写入的是那个进程的库，即开发库 app.db）。
# 因此必须从 pytest 收集里排除；用 `python tests/xxx.py` 手动执行。
#
#   test_agent_closure.py      Day6 Agent 闭环（独立脚本）
#   test_e2e_learning_loop.py  Day7 学习闭环（独立脚本，E2E_RESET_DB 会删库）
#   test_phase2_week1.py       Phase2 W1 集成（有 pytest 风格 test_*，但依赖实时后端；
#                              纯进程内的部分已被其他单测覆盖）
collect_ignore = [
    "test_agent_closure.py",
    "test_e2e_learning_loop.py",
    "test_phase2_week1.py",
]


def pytest_report_header(config: pytest.Config) -> str:
    """在测试输出头部显示默认测试库，便于一眼确认隔离生效。"""
    return f"career-os 默认测试库（隔离）: {_TEST_DB}"


def _sqlite_path(url: str) -> Path | None:
    """从 sqlite URL 解析实际文件路径；非 sqlite / 内存库返回 None。

    相对路径按「从 backend/ 运行」解析（项目约定）。
    """
    if not url.startswith("sqlite"):
        return None
    raw = url.split("sqlite:///", 1)[-1]
    if not raw or raw.startswith(":memory:"):
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[1] / p
    return p.resolve()


@pytest.fixture(scope="session", autouse=True)
def _isolated_db_guard():
    """会话级守卫：确认测试**不会写开发库**，结束后清理 conftest 建的临时库。

    守卫的真实目的只有一个 —— **绝不碰 ``backend/data/app.db``**。
    库路径解析出来后，这里只拒绝「开发库本身」，而允许任何独立的临时库
    （例如某个模块显式指向自己的临时文件），避免把合法隔离误判为违规。
    """

    # 延迟导入：此时 DATABASE_URL 已设置，engine 会指向临时库
    from app.core.config import settings
    from app.db.base import engine

    used = settings.database_url
    used_path = _sqlite_path(used)

    if used_path is not None and used_path == _DEV_DB:
        raise RuntimeError(
            f"测试指向了开发库 {_DEV_DB}，已中止。\n"
            "这会把测试数据写进真实数据库。请检查 conftest.py 是否在 app 导入前"
            "设置了 DATABASE_URL，或某个测试模块是否覆盖成了开发库路径。"
        )

    # 建表 + 种子，**不依赖 TestClient 的 lifespan**。
    #
    # 为什么必须在这里做：大量测试在**模块级**写 `client = TestClient(app)`（不进 `with`），
    # 这样 Starlette 的 lifespan 不会触发，`init_db()` 也就永不执行。
    # 它们此前能跑通，是因为开发库里**已经存在表结构**（真实服务器建的）——
    # 换句话说，这些测试一直在悄悄依赖开发库。换到空库后立刻
    # `sqlite3.OperationalError: no such table: projects`。
    #
    # init_db() 自带 `count() == 0` 守卫，重复调用幂等，不会重复灌种子。
    from app.db.base import init_db

    init_db()

    yield

    # 先释放连接再删文件（Windows 下句柄未释放会删除失败）
    engine.dispose()
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)
