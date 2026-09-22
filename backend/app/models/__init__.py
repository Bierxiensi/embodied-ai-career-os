"""统一 ORM 模型导出。导入此模块即注册所有模型到 Base.metadata。"""

from app.models.activity_draft import ActivityDraft
from app.models.agent_run import AgentRun
from app.models.career import Career
from app.models.career_mode import CareerMode, ModeTransition
from app.models.commit_suggestion import CommitSuggestion
from app.models.day_artifact import DayArtifact
from app.models.day_progress import DayProgress
from app.models.experiment import Experiment
from app.models.interview_log import InterviewLog
from app.models.interview_question import InterviewQuestion
from app.models.job_application import JobApplication
from app.models.job_match import JobMatch
from app.models.job_posting import JobPosting
from app.models.learning_log import LearningLog
from app.models.report_log import ReportLog
from app.models.resume_fact import ResumeFact
from app.models.resume_version import ResumeVersion
from app.models.milestone import Milestone
from app.models.paper import Paper
from app.models.paper_chunk import PaperChunk
from app.models.paper_chunk_embedding import PaperChunkEmbedding
from app.models.phd import PhDAdvisor, PhDTarget, ResearchDirection
from app.models.plan_day import PlanDay
from app.models.practice_record import PracticeRecord
from app.models.project import Project
from app.models.skill import Skill
from app.models.skill_assessment import SkillAssessment
from app.models.task import Task

__all__ = [
    "ActivityDraft",
    "AgentRun",
    "Career",
    "CareerMode",
    "CommitSuggestion",
    "DayArtifact",
    "DayProgress",
    "Experiment",
    "InterviewLog",
    "InterviewQuestion",
    "JobApplication",
    "JobMatch",
    "JobPosting",
    "LearningLog",
    "ReportLog",
    "ResumeFact",
    "ResumeVersion",
    "Milestone",
    "ModeTransition",
    "Paper",
    "PaperChunk",
    "PaperChunkEmbedding",
    "PhDAdvisor",
    "PhDTarget",
    "ResearchDirection",
    "PlanDay",
    "PracticeRecord",
    "Project",
    "Skill",
    "SkillAssessment",
    "Task",
]
