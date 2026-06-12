from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    target_role: Mapped[str] = mapped_column(String(120))
    skill_profile_json: Mapped[Dict] = mapped_column(JSON, default=dict)
    preferences_json: Mapped[Dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(50))
    estimated_hours: Mapped[int] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)

    lessons: Mapped[List["Lesson"]] = relationship(back_populates="learning_path", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        Index("ix_lessons_slug", "slug", unique=True),
        Index("ix_lessons_path_id", "learning_path_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learning_path_id: Mapped[int] = mapped_column(ForeignKey("learning_paths.id"))
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    content_md: Mapped[str] = mapped_column(Text)
    prerequisites_json: Mapped[List] = mapped_column(JSON, default=list)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)

    learning_path: Mapped[LearningPath] = relationship(back_populates="lessons")


class LessonCompletion(Base):
    __tablename__ = "lesson_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"))
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(50))
    estimated_hours: Mapped[int] = mapped_column(Integer)
    milestones_json: Mapped[List] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(50), default="planned")
    track_focus: Mapped[str] = mapped_column(String(120), default="ai-engineering")


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        Index("ix_exercises_category", "category"),
        Index("ix_exercises_slug", "slug", unique=True),
        Index("ix_exercises_is_generated", "is_generated"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    category: Mapped[str] = mapped_column(String(120))
    difficulty: Mapped[str] = mapped_column(String(50))
    prompt_md: Mapped[str] = mapped_column(Text)
    starter_code: Mapped[str] = mapped_column(Text)
    solution_code: Mapped[str] = mapped_column(Text)
    explanation_md: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_exercise_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("exercises.id"), nullable=True
    )


class UserExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"
    __table_args__ = (
        Index("ix_attempts_user_exercise", "user_id", "exercise_id"),
        Index("ix_attempts_attempted_at", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    submitted_code: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50))
    score: Mapped[float] = mapped_column(Float)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ai_feedback_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ai_feedback.id"), nullable=True
    )


class AIFeedbackFeature(str, enum.Enum):
    """Discriminator for polymorphic reference_id mapping."""
    exercise_grade = "exercise_grade"
    deep_dive = "deep_dive"
    variation = "variation"
    interview_coach = "interview_coach"


class AIFeedback(Base):
    __tablename__ = "ai_feedback"
    __table_args__ = (
        Index("ix_ai_feedback_feature_ref", "feature", "reference_id"),
        Index("ix_ai_feedback_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    feature: Mapped[str] = mapped_column(String(30), nullable=False)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_input_hash: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_json: Mapped[Optional[Dict]] = mapped_column(JSONB, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"
    __table_args__ = (
        Index("ix_knowledge_articles_slug", "slug", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    category: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    content_md: Mapped[str] = mapped_column(Text)
    source_links_json: Mapped[List] = mapped_column(JSON, default=list)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), unique=True)
    category: Mapped[str] = mapped_column(String(120), default="ai-news")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    signal_score: Mapped[int] = mapped_column(Integer, default=50)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(120))
    stack_json: Mapped[List] = mapped_column(JSON, default=list)
    architecture_md: Mapped[str] = mapped_column(Text)
    repo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    demo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lessons_learned_md: Mapped[str] = mapped_column(Text, default="")
    portfolio_score: Mapped[int] = mapped_column(Integer, default=0)


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    company_name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200), default="Remote")
    employment_type: Mapped[str] = mapped_column(String(120), default="unknown")
    summary: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), unique=True)
    description_md: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)
    skill_gaps_json: Mapped[List] = mapped_column(JSON, default=list)
    fit_score: Mapped[int] = mapped_column(Integer, default=0)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        Index("ix_interview_questions_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(120))
    role_type: Mapped[str] = mapped_column(String(120))
    difficulty: Mapped[str] = mapped_column(String(50))
    question_text: Mapped[str] = mapped_column(Text)
    answer_outline_md: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)


class InterviewQuestionPractice(Base):
    __tablename__ = "interview_question_practice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("interview_questions.id"))
    confidence_score: Mapped[int] = mapped_column(Integer, default=3)
    notes: Mapped[str] = mapped_column(Text, default="")
    practiced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProgressSnapshot(Base):
    __tablename__ = "progress_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[date] = mapped_column(Date, default=date.today)
    learning_completion_pct: Mapped[float] = mapped_column(Float, default=0.0)
    python_practice_count: Mapped[int] = mapped_column(Integer, default=0)
    projects_completed_count: Mapped[int] = mapped_column(Integer, default=0)
    interview_readiness_score: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")


class MemoryCard(Base):
    __tablename__ = "memory_cards"
    __table_args__ = (
        Index("ix_memory_cards_category", "category"),
        Index("ix_memory_cards_next_review", "next_review_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    front_md: Mapped[str] = mapped_column(Text, nullable=False)
    back_md: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(50), nullable=False)  # lesson, exercise, interview, knowledge
    source_title: Mapped[str] = mapped_column(String(500), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="intermediate")
    tags_json: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class PodcastEpisode(Base):
    __tablename__ = "podcast_episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    youtube_url: Mapped[str] = mapped_column(Text, nullable=False)
    video_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    digest_length_mins: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="single")
    script_zh: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_path: Mapped[str] = mapped_column(Text, nullable=False)
    duration_secs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text|web|youtube
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    tldr: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[List] = mapped_column(JSON, default=list)
    takeaways: Mapped[List] = mapped_column(JSON, default=list)
    sections: Mapped[List] = mapped_column(JSON, default=list)  # [{"heading": str, "points": [str]}]
    output_type: Mapped[str] = mapped_column(String(20), nullable=False, default="summary")  # summary | mindmap
    mindmap_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ZiweiProfile(Base):
    __tablename__ = "ziwei_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    relation: Mapped[str] = mapped_column(String(20), default="self")  # self, family, friend
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # male, female
    birth_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD（农历输入时为农历 Y-M-D）
    birth_time_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 时辰 0-12（0=早子时, 12=晚子时）
    is_lunar_input: Mapped[bool] = mapped_column(Boolean, default=False)
    is_leap_month: Mapped[bool] = mapped_column(Boolean, default=False)
    chart_json: Mapped[Dict] = mapped_column(JSON, default=dict)  # 归一化 ZiweiChart（前端 iztro 排盘结果）
    persona: Mapped[str] = mapped_column(String(20), default="sage")  # sage, taoist, analyst
    portrait_json: Mapped[Dict] = mapped_column(JSON, default=dict)  # AI 蒸馏画像（Phase 4 使用）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ZiweiConversation(Base):
    __tablename__ = "ziwei_conversations"
    __table_args__ = (Index("ix_ziwei_conv_profile", "profile_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ZiweiProfile.id
    scenario: Mapped[str] = mapped_column(String(20), default="natal")  # natal, horoscope, synastry, report
    title: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ZiweiMessage(Base):
    __tablename__ = "ziwei_messages"
    __table_args__ = (Index("ix_ziwei_msg_conv", "conversation_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chart_context_json: Mapped[Dict] = mapped_column(JSON, default=dict)  # 当时盘面上下文：focus宫位、流年年份等
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ScribeTranscript(Base):
    __tablename__ = "scribe_transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    youtube_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
