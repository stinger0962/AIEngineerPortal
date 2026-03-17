from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class PortalBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DashboardStat(BaseModel):
    label: str
    value: str
    tone: str


class DashboardSummary(BaseModel):
    user_name: str
    headline: str
    learning_streak: int
    stats: List[DashboardStat]
    next_lesson: Optional[Dict[str, Any]]
    recommended_exercise: Optional[Dict[str, Any]]
    active_projects: List[Dict[str, Any]]
    recommendation_panel: List[Dict[str, str]]


class DashboardToday(BaseModel):
    focus: List[str]
    highlights: List[str]
    blockers: List[str]


class LessonOut(PortalBase):
    id: int
    learning_path_id: int
    title: str
    slug: str
    summary: str
    content_md: str
    prerequisites_json: List[str]
    estimated_minutes: int
    order_index: int
    tags_json: List[str]
    is_completed: bool = False


class LearningPathOut(PortalBase):
    id: int
    title: str
    slug: str
    description: str
    level: str
    estimated_hours: int
    order_index: int
    is_active: bool
    tags_json: List[str]
    completion_pct: float = 0
    lessons: List[LessonOut] = []


class LessonCompletionResponse(BaseModel):
    lesson_id: int
    completed: bool
    learning_completion_pct: float


class CourseOut(PortalBase):
    id: int
    title: str
    slug: str
    description: str
    difficulty: str
    estimated_hours: int
    milestones_json: List[Dict[str, Any]]
    status: str
    track_focus: str


class CourseProgressIn(BaseModel):
    status: str


class ExerciseOut(PortalBase):
    id: int
    title: str
    slug: str
    category: str
    difficulty: str
    prompt_md: str
    starter_code: str
    solution_code: str
    explanation_md: str
    tags_json: List[str]


class ExerciseAttemptIn(BaseModel):
    submitted_code: str
    notes: str = ""


class ExerciseAttemptOut(PortalBase):
    id: int
    exercise_id: int
    submitted_code: str
    notes: str
    status: str
    score: float
    attempted_at: datetime


class ExerciseDetail(BaseModel):
    exercise: ExerciseOut
    attempts: List[ExerciseAttemptOut]


class KnowledgeArticleOut(PortalBase):
    id: int
    title: str
    slug: str
    category: str
    summary: str
    content_md: str
    source_links_json: List[str]
    tags_json: List[str]
    last_reviewed_at: datetime


class ProjectOut(PortalBase):
    id: int
    title: str
    slug: str
    summary: str
    status: str
    category: str
    stack_json: List[str]
    architecture_md: str
    repo_url: Optional[str]
    demo_url: Optional[str]
    lessons_learned_md: str
    portfolio_score: int


class ProjectIn(BaseModel):
    title: str
    summary: str
    status: str
    category: str
    stack_json: List[str]
    architecture_md: str
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    lessons_learned_md: str = ""
    portfolio_score: int = 0


class InterviewQuestionOut(PortalBase):
    id: int
    category: str
    role_type: str
    difficulty: str
    question_text: str
    answer_outline_md: str
    tags_json: List[str]


class InterviewRoadmap(BaseModel):
    focus_areas: List[str]
    weekly_plan: List[str]


class RecommendationOut(BaseModel):
    title: str
    reason: str
    action_path: str


class ProgressSnapshotOut(PortalBase):
    id: int
    user_id: int
    date: date
    learning_completion_pct: float
    python_practice_count: int
    projects_completed_count: int
    interview_readiness_score: int
    notes: str
