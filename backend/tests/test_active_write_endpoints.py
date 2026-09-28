# backend/tests/test_active_write_endpoints.py
"""STYLE.md 不变量：活跃写端点预算 ≤25（口径=OpenAPI 文档面）（spec §5.3）。

计数口径（与断言严格一致）：OpenAPI 文档面中 POST/PATCH/PUT/DELETE 路径，
剔除带 deprecated 标记（include_in_schema=False）的路由。
本测试只钉 ≤25 的预算：**隐藏但 UI 仍调用**的写端点不在本口径内，
由「撤表单」支线清偿（见 superpowers 台账）——所以这里不断言「总数不增反减」。
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
