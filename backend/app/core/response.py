"""统一响应包。

简化版（Day6）：{success, data, message}
未来 Phase3 可升级为含 trace_id / agent_execution_id / token_usage 的结构，
用于 Agent 链路追踪。
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应结构。所有 CRUD 端点返回此结构，前端 apiClient 一次性解包。"""

    success: bool
    data: T | None = None
    message: str | None = None


def ok(data: T = None, message: str | None = None) -> ApiResponse[T]:
    """成功响应工厂。"""

    return ApiResponse(success=True, data=data, message=message)


def fail(message: str, data: T = None) -> ApiResponse[T]:
    """失败响应工厂。data 可携带部分信息便于前端定位。"""

    return ApiResponse(success=False, data=data, message=message)
