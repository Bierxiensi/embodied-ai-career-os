"""Services —— 业务服务层。

与 agents/ 的区别：
- agents/ 是 LangGraph 驱动的智能决策单元（LLM 推理）
- services/ 是确定性业务逻辑（定时任务 / 外部 API / 文件处理）
"""