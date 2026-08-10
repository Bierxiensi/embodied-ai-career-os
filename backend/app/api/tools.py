"""工具桥接 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response import ApiResponse, ok
from app.db.base import get_db
from app.models.task import Task
from app.services.tools.prompts import generate_tool_prompt
from app.services.tools.context import generate_context_pack

router = APIRouter(prefix="/tools", tags=["tools"])


class PromptRequest(BaseModel):
    task_id: int
    tool: str  # trae | claude | chatgpt | deepseek | workbuddy


@router.post("/prompt")
def get_prompt(req: PromptRequest, db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """为指定任务和工具生成适配 prompt。"""
    task = db.get(Task, req.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    prompt = generate_tool_prompt(task, req.tool)
    return ok({"tool": req.tool, "task_title": task.title, "prompt": prompt})


@router.get("/context")
def get_context() -> ApiResponse[dict]:
    """获取当前学习上下文恢复包。"""
    pack = generate_context_pack()
    return ok({"context_pack": pack})
