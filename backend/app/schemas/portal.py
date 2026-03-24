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
    adaptive_focus: Optional[Dict[str, Any]] = None


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
    progression_label: Optional[str] = None
    practice_stage: Optional[str] = None
    hint_md: Optional[str] = None
    review_checklist_json: List[str] = []
    success_criteria_json: List[str] = []
    related_lesson_slugs: List[str] = []
    related_lesson_titles: List[str] = []
    next_exercise_id: Optional[int] = None
    next_exercise_slug: Optional[str] = None
    next_exercise_title: Optional[str] = None


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
    review_prompt: Optional[str] = None


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


class NewsItemOut(PortalBase):
    id: int
    source_name: str
    title: str
    slug: str
    summary: str
    source_url: str
    category: str
    published_at: datetime
    signal_score: int
    tags_json: List[str]
    is_saved: bool
    is_seeded: bool
    last_synced_at: datetime
    why_it_matters: str
    suggested_action: str
    focus_area: str
    recommended_path_slug: Optional[str] = None
    recommended_path_title: Optional[str] = None
    recommended_exercise_category: Optional[str] = None


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


class JobPostingOut(PortalBase):
    id: int
    source_name: str
    title: str
    slug: str
    company_name: str
    location: str
    employment_type: str
    summary: str
    source_url: str
    description_md: str
    published_at: datetime
    tags_json: List[str]
    skill_gaps_json: List[str]
    fit_score: int
    is_saved: bool
    is_seeded: bool
    last_synced_at: datetime
    fit_summary: str
    suggested_action: str
    primary_gap: Optional[str] = None
    focus_area: str
    recommended_path_slug: Optional[str] = None
    recommended_path_title: Optional[str] = None
    recommended_exercise_category: Optional[str] = None


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
    practice_count: int = 0
    last_practiced_at: Optional[datetime] = None
    average_confidence: Optional[float] = None


class InterviewPracticeIn(BaseModel):
    confidence_score: int = 3
    notes: str = ""


class InterviewPracticeOut(BaseModel):
    question_id: int
    practice_count: int
    last_practiced_at: datetime
    average_confidence: float


class InterviewRoadmap(BaseModel):
    focus_areas: List[str]
    weekly_plan: List[str]
    rationale: List[str] = []


class PortfolioReadiness(BaseModel):
    overall_score: int
    strongest_signals: List[str]
    gaps_to_close: List[str]
    next_best_moves: List[str]


class SkillGapInsight(BaseModel):
    title: str
    urgency: str
    evidence: str
    action_path: str


class MasteryAreaOut(BaseModel):
    area_slug: str
    area_title: str
    mastery_score: int
    status: str
    evidence: str
    gap: str
    weakest_signal: str
    next_action_path: str
    next_action_label: str


class AdaptiveFocusOut(BaseModel):
    title: str
    reason: str
    action_path: str
    target_kind: str
    mastery_score: int
    area_slug: str
    area_title: str
    action_label: str


class RecommendationOut(BaseModel):
    title: str
    reason: str
    action_path: str
    source_kind: str = "internal"


class JobFitAnalysisOut(BaseModel):
    job_id: int
    fit_score: int
    strengths: List[str]
    gaps: List[str]
    rationale: str


class FeedRefreshMetaOut(BaseModel):
    source: str
    item_count: int
    live_item_count: int
    seeded_item_count: int
    refreshed_at: datetime
    is_stale: bool
    refresh_window_hours: int
    auto_refresh_enabled: bool


class ProgressSnapshotOut(PortalBase):
    id: int
    user_id: int
    date: date
    learning_completion_pct: float
    python_practice_count: int
    projects_completed_count: int
    interview_readiness_score: int
    notes: str
