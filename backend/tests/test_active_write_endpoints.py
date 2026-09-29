# backend/tests/test_active_write_endpoints.py
"""STYLE.md 不变量 3：活跃写端点预算 ≤25（口径=OpenAPI 文档面）（spec §5.3）。

计数口径（与断言严格一致）：OpenAPI 文档面中 POST/PATCH/PUT/DELETE 路径，
剔除带 deprecated 标记（include_in_schema=False）的路由。

另一半账：**隐藏但 UI 仍调用**（hidden-but-live）的写端点不进预算口径——
它们藏在 schema 外、前端还在打。2026-09-29「撤表单」后不再挂「支线清偿」的账，
改为本文件的 ``HIDDEN_BUT_LIVE`` 显式清单登记（端点 → 一行保留理由），
并由 ``test_hidden_but_live_allowlist_exact_key_set`` 钉死键集字面量：
往清单加一条（= 承认又多一个 schema 外且活的写口）必须同步改该测试，否则它红。

反向不在此列：**schema 可见**且前端仍在打的写端点（如
``POST /api/projects/{project_id}/readme`` 保存 README）本来就计入 ≤25 预算，
由 ``test_active_write_endpoints_within_budget`` 守，不进本清单。

撤表单 / 新增写表单 UI 后的刷新配方（人工重跑，核对后同时改清单与键集字面量）：

1. 隐藏写端点全集（后端口径）::

     cd backend && .venv/Scripts/python.exe -c "from app.main import app; from fastapi.routing import APIRoute; print('\\n'.join(sorted(f'{m.upper()} {r.path}' for r in app.routes if isinstance(r, APIRoute) and not r.include_in_schema for m in r.methods if m in {'POST', 'PATCH', 'PUT', 'DELETE'})))"

2. 前端写口调用点（前端口径；GET 不算写口）::

     grep -rnE 'apiClient\\.(post|patch|put|delete)' frontend/src/services

3. 逐条把 (2) 的调用点追到 importer：service 函数有**组件 / 页面**在用 = 活；
   只有 service 文件里的定义、零 importer = 死（撤 UI 留数据，不算 live）。

4. (1) ∩ (3) = ``HIDDEN_BUT_LIVE`` 应有键集；对不上先改清单，再改键集断言。
"""

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MAX_ACTIVE_WRITE_ENDPOINTS = 25
WRITE_METHODS = {"post", "patch", "put", "delete"}

#: 隐藏（include_in_schema=False）但前端仍有活调用方的写端点 → 一行为什么留着。
#: 键格式 "METHOD /api/path"，与 FastAPI 路由表同形；2026-09-29 撤表单后重算。
HIDDEN_BUT_LIVE: dict[str, str] = {
    "PATCH /api/milestones/{milestone_id}":
        "MilestoneTimeline 状态流转（/projects/[id] 证据线，未归档）",
    "POST /api/milestones/{milestone_id}/tasks":
        "MilestoneTimeline 生成任务（/projects/[id] 证据线，未归档）",
    "POST /api/phd/advisors/match-all":
        "PhDAdvisorBoard「重算全部匹配」——重算 match_json 缓存的重算工具，非登记表单",
    "POST /api/resume/diagnose":
        "ResumeBoard 防虚构诊断——只读计算不写库，撤表单时显式保留",
}


def _hidden_write_routes() -> set[str]:
    """后端真实的隐藏写路由全集（METHOD /path）。"""
    return {
        f"{m.upper()} {r.path}"
        for r in app.routes
        if isinstance(r, APIRoute) and not r.include_in_schema
        for m in r.methods
        if m.lower() in WRITE_METHODS
    }


def test_active_write_endpoints_within_budget():
    schema = client.get("/openapi.json").json()
    active = {
        f"{m.upper()} {p}"
        for p, ops in schema["paths"].items()
        for m in ops
        if m in WRITE_METHODS
    }
    assert len(active) <= MAX_ACTIVE_WRITE_ENDPOINTS, sorted(active)


def test_hidden_but_live_allowlist_exact_key_set():
    """HIDDEN_BUT_LIVE 的键集必须与本测试内的字面量逐字一致。

    纪律：新增一个「schema 隐藏但前端还在打」的写端点，必须同时改这里——
    清单是数据，本测试是闸门，两处不一致即红。撤表单后按模块 docstring 的
    刷新配方重算键集（撤 UI 的 service 函数留着但零 importer，不算 live）。
    """
    expected = {
        "PATCH /api/milestones/{milestone_id}",
        "POST /api/milestones/{milestone_id}/tasks",
        "POST /api/phd/advisors/match-all",
        "POST /api/resume/diagnose",
    }
    assert set(HIDDEN_BUT_LIVE) == expected, sorted(set(HIDDEN_BUT_LIVE) ^ expected)

    # 清单里的每个键必须真的是「隐藏写路由」——防键集与路由表漂移
    hidden = _hidden_write_routes()
    assert set(HIDDEN_BUT_LIVE) <= hidden, sorted(set(HIDDEN_BUT_LIVE) - hidden)

    # 理由一行一条（清单可读性纪律）
    assert all(why and "\n" not in why for why in HIDDEN_BUT_LIVE.values())
