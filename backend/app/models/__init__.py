"""统一 ORM 模型导出。导入此模块即注册所有模型到 Base.metadata。"""

from app.models.agent_run import AgentRun
from app.models.career import Career
from app.models.commit_suggestion import CommitSuggestion
from app.models.learning_log import LearningLog
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_chunk_embedding import PaperChunkEmbedding
from app.models.skill import Skill
from app.models.skill_assessment import SkillAssessment
from app.models.task import Task

__all__ = [
    "AgentRun",
    "Career",
    "CommitSuggestion",
    "LearningLog",
    "Paper",
    "PaperChunk",
    "PaperChunkEmbedding",
    "Skill",
    "SkillAssessment",
    "Task",
]
