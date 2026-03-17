from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Course,
    Exercise,
    InterviewQuestion,
    KnowledgeArticle,
    LearningPath,
    Lesson,
    LessonCompletion,
    ProgressSnapshot,
    Project,
    User,
    UserExerciseAttempt,
)
from app.seed.data import (
    DEFAULT_USER,
    INITIAL_PROGRESS,
    PATHS,
    PROJECTS,
    build_articles,
    build_courses,
    build_exercises,
    build_interview_questions,
    build_lessons,
)


def seed_database(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        return

    user = User(**DEFAULT_USER)
    db.add(user)
    db.flush()

    path_map: dict[str, LearningPath] = {}
    for order_index, (title, slug, description, level, estimated_hours) in enumerate(PATHS, start=1):
        path = LearningPath(
            title=title,
            slug=slug,
            description=description,
            level=level,
            estimated_hours=estimated_hours,
            order_index=order_index,
            tags_json=[slug, "phase-1"],
        )
        db.add(path)
        path_map[slug] = path
    db.flush()

    lessons: list[Lesson] = []
    for lesson_payload in build_lessons():
        lesson = Lesson(
            learning_path_id=path_map[lesson_payload["path_slug"]].id,
            title=lesson_payload["title"],
            slug=lesson_payload["slug"],
            summary=lesson_payload["summary"],
            content_md=lesson_payload["content_md"],
            prerequisites_json=lesson_payload["prerequisites_json"],
            estimated_minutes=lesson_payload["estimated_minutes"],
            order_index=lesson_payload["order_index"],
            tags_json=lesson_payload["tags_json"],
        )
        db.add(lesson)
        lessons.append(lesson)
    db.flush()

    for payload in build_courses():
        db.add(Course(**payload))

    exercises: list[Exercise] = []
    for payload in build_exercises():
        exercise = Exercise(**payload)
        db.add(exercise)
        exercises.append(exercise)
    db.flush()

    for payload in build_articles():
        db.add(KnowledgeArticle(**payload))

    for payload in PROJECTS:
        db.add(Project(**payload))

    for payload in build_interview_questions():
        db.add(InterviewQuestion(**payload))

    db.add(ProgressSnapshot(user_id=user.id, **INITIAL_PROGRESS))
    db.commit()
