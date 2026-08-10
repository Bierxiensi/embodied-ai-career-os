"""LLM Commit 分析器 —— 生成技能关联建议。"""

from __future__ import annotations

from app.llm import ChatMessage, get_llm

# 系统中已有的技能名（供 LLM 参考）
KNOWN_SKILLS = [
    "Python", "Frontend", "Web Engineering", "Agent Application",
    "PyTorch", "Deep Learning", "ROS2", "Isaac", "Robot Learning", "VLA", "C++",
]


def analyze_commit(commit: dict) -> dict | None:
    """LLM 分析单条 commit，生成技能关联建议。

    Args:
        commit: {sha, message, files, additions, deletions}

    Returns:
        {suggestions: [...], suggest_ignore: bool, summary: str} 或 None（失败时）
    """
    files_str = "\n".join(
        f"  - {f.get('filename', '')} (+{f.get('additions', 0)} -{f.get('deletions', 0)})"
        for f in commit.get("files", [])[:10]
    )
    skills_str = ", ".join(KNOWN_SKILLS)

    prompt = f"""分析以下 Git commit 关联的学习技能。

Commit Message: {commit.get('message', '')}
文件变更:
{files_str or '（无文件信息）'}
统计: +{commit.get('additions', 0)} -{commit.get('deletions', 0)} 行

已知技能: {skills_str}

返回 JSON：
{{
  "suggestions": [
    {{"skill": "技能名", "reason": "一句话理由", "confidence": 0.0-1.0}}
  ],
  "suggest_ignore": true/false,
  "summary": "一句话总结这个 commit 做了什么"
}}

规则：
- 如果只改了依赖/格式/README小修 → suggest_ignore=true
- 每个 commit 最多关联 3 个技能
- confidence > 0.6 才是可信建议
直接输出 JSON。"""

    try:
        llm = get_llm()
        result = llm.chat_json([
            ChatMessage(role="system", content="你是代码活动分析器。只输出 JSON。"),
            ChatMessage(role="user", content=prompt),
        ])
        if result.get("_parse_error"):
            return None
        return result
    except Exception:
        return None
