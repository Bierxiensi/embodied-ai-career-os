# backend/tests/test_active_write_endpoints.py
"""STYLE.md 不变量：活跃写端点 ≤25 且总数不增反减（spec §5.3）。

计数口径：OpenAPI 中 POST/PATCH/PUT/DELETE 路径，剔除带
deprecated 标记（include_in_schema=False）的路由。
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MAX_ACTIVE_WRITE_ENDPOINTS = 25


def test_active_write_endpoints_within_budget():
    schema = client.get("/openapi.json").json()
    write_ops = {"post", "patch", "put", "delete"}
    active = {
        f"{m.upper()} {p}"
        for p, ops in schema["paths"].items()
        for m in ops
        if m in write_ops
    }
    assert len(active) <= MAX_ACTIVE_WRITE_ENDPOINTS, sorted(active)
