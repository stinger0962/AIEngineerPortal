from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class UserExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    submitted_code: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50))
    score: Mapped[float] = mapped_column(Float)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    category: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    content_md: Mapped[str] = mapped_column(Text)
    source_links_json: Mapped[List] = mapped_column(JSON, default=list)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(120))
    role_type: Mapped[str] = mapped_column(String(120))
    difficulty: Mapped[str] = mapped_column(String(50))
    question_text: Mapped[str] = mapped_column(Text)
    answer_outline_md: Mapped[str] = mapped_column(Text)
    tags_json: Mapped[List] = mapped_column(JSON, default=list)


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
