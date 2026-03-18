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
    user = db.scalar(select(User).limit(1))
    if not user:
        user = User(**DEFAULT_USER)
        db.add(user)
        db.flush()

    sync_learning_content(db)
    sync_courses(db)
    sync_exercises(db)
    sync_knowledge_articles(db)
    sync_interview_questions(db)
    seed_project_templates(db)

    snapshot = db.scalar(
        select(ProgressSnapshot).where(ProgressSnapshot.user_id == user.id).order_by(ProgressSnapshot.id.asc())
    )
    if not snapshot:
        db.add(ProgressSnapshot(user_id=user.id, **INITIAL_PROGRESS))
    db.commit()


def sync_learning_content(db: Session) -> None:
    existing_paths = {path.slug: path for path in db.scalars(select(LearningPath)).all()}
    path_map: dict[str, LearningPath] = {}
    for order_index, (title, slug, description, level, estimated_hours) in enumerate(PATHS, start=1):
        path = existing_paths.get(slug)
        if not path:
            path = LearningPath(slug=slug)
            db.add(path)
        path.title = title
        path.description = description
        path.level = level
        path.estimated_hours = estimated_hours
        path.order_index = order_index
        path.is_active = True
        path.tags_json = [slug, "phase-1"]
        path_map[slug] = path
    db.flush()

    existing_lessons = {lesson.slug: lesson for lesson in db.scalars(select(Lesson)).all()}
    for payload in build_lessons():
        lesson = existing_lessons.get(payload["slug"])
        if not lesson:
            lesson = Lesson(slug=payload["slug"])
            db.add(lesson)
        lesson.learning_path_id = path_map[payload["path_slug"]].id
        lesson.title = payload["title"]
        lesson.summary = payload["summary"]
        lesson.content_md = payload["content_md"]
        lesson.prerequisites_json = payload["prerequisites_json"]
        lesson.estimated_minutes = payload["estimated_minutes"]
        lesson.order_index = payload["order_index"]
        lesson.tags_json = payload["tags_json"]


def sync_courses(db: Session) -> None:
    existing_courses = {course.slug: course for course in db.scalars(select(Course)).all()}
    for payload in build_courses():
        course = existing_courses.get(payload["slug"])
        if not course:
            course = Course(slug=payload["slug"])
            db.add(course)
        course.title = payload["title"]
        course.description = payload["description"]
        course.difficulty = payload["difficulty"]
        course.estimated_hours = payload["estimated_hours"]
        course.milestones_json = payload["milestones_json"]
        course.status = payload["status"]
        course.track_focus = payload["track_focus"]


def sync_exercises(db: Session) -> None:
    existing_exercises = {exercise.slug: exercise for exercise in db.scalars(select(Exercise)).all()}
    for payload in build_exercises():
        exercise = existing_exercises.get(payload["slug"])
        if not exercise:
            exercise = Exercise(slug=payload["slug"])
            db.add(exercise)
        exercise.title = payload["title"]
        exercise.category = payload["category"]
        exercise.difficulty = payload["difficulty"]
        exercise.prompt_md = payload["prompt_md"]
        exercise.starter_code = payload["starter_code"]
        exercise.solution_code = payload["solution_code"]
        exercise.explanation_md = payload["explanation_md"]
        exercise.tags_json = payload["tags_json"]


def sync_knowledge_articles(db: Session) -> None:
    existing_articles = {article.slug: article for article in db.scalars(select(KnowledgeArticle)).all()}
    for payload in build_articles():
        article = existing_articles.get(payload["slug"])
        if not article:
            article = KnowledgeArticle(slug=payload["slug"])
            db.add(article)
        article.title = payload["title"]
        article.category = payload["category"]
        article.summary = payload["summary"]
        article.content_md = payload["content_md"]
        article.source_links_json = payload["source_links_json"]
        article.tags_json = payload["tags_json"]


def sync_interview_questions(db: Session) -> None:
    existing_questions = {
        question.question_text: question for question in db.scalars(select(InterviewQuestion)).all()
    }
    for payload in build_interview_questions():
        question = existing_questions.get(payload["question_text"])
        if not question:
            question = InterviewQuestion(question_text=payload["question_text"])
            db.add(question)
        question.category = payload["category"]
        question.role_type = payload["role_type"]
        question.difficulty = payload["difficulty"]
        question.answer_outline_md = payload["answer_outline_md"]
        question.tags_json = payload["tags_json"]


def seed_project_templates(db: Session) -> None:
    if db.scalar(select(Project).limit(1)):
        return

    for payload in PROJECTS:
        db.add(Project(**payload))
