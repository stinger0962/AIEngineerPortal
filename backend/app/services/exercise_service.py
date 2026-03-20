from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Exercise, Lesson, UserExerciseAttempt
from app.services.progress_service import refresh_progress_snapshot

PRACTICE_PLAYBOOK = {
    "python-refresh": {
        "practice_stage": "Core runtime habits",
        "hint_md": "Normalize the boundary first, keep return shapes stable, and make the middle of the function boring on purpose.",
        "review_checklist_json": [
            "Did I make the input and output shapes explicit?",
            "Would a teammate know where validation happens?",
            "Did I avoid silent mutation or vague branching?",
        ],
        "success_criteria_json": [
            "Returns one stable shape across branches",
            "Makes failure handling obvious",
            "Keeps the core logic readable in under a minute",
        ],
        "related_lesson_slugs": [
            "python-for-ai-engineers-1",
            "python-for-ai-engineers-2",
        ],
    },
    "data-transformation": {
        "practice_stage": "Transform and summarize data safely",
        "hint_md": "Think like an evaluation or trace pipeline: group clearly, preserve the data story, and make edge cases visible instead of clever.",
        "review_checklist_json": [
            "Do grouped metrics stay readable?",
            "Would malformed rows be debuggable?",
            "Did I choose names that explain the transformation?",
        ],
        "success_criteria_json": [
            "Handles missing or noisy records predictably",
            "Produces summary output that is easy to inspect",
            "Would be safe to rerun in a script workflow",
        ],
        "related_lesson_slugs": [
            "python-for-ai-engineers-4",
            "evaluation-and-observability-1",
        ],
    },
    "api-async": {
        "practice_stage": "Async and provider control",
        "hint_md": "Make waiting behavior explicit. Timeouts, retries, and concurrency limits matter more than squeezing everything into one helper.",
        "review_checklist_json": [
            "Is timeout behavior explicit?",
            "Is retryable failure separate from terminal failure?",
            "Would logs reveal what actually timed out?",
        ],
        "success_criteria_json": [
            "Uses async boundaries coherently",
            "Makes timeout and retry decisions legible",
            "Would be maintainable under provider instability",
        ],
        "related_lesson_slugs": [
            "python-for-ai-engineers-3",
            "ai-deployment-and-mlops-4",
        ],
    },
    "prompt-formatting": {
        "practice_stage": "Prompt boundary discipline",
        "hint_md": "Treat prompt construction like request composition: trusted instructions, untrusted user input, and context blocks should stay separate.",
        "review_checklist_json": [
            "Did I preserve trusted versus untrusted boundaries?",
            "Would this format survive longer prompts and more context?",
            "Can another engineer review the structure quickly?",
        ],
        "success_criteria_json": [
            "Separates system, user, and context cleanly",
            "Avoids string chaos and hidden assumptions",
            "Would scale to a real LLM feature",
        ],
        "related_lesson_slugs": [
            "llm-app-foundations-1",
            "llm-app-foundations-3",
        ],
    },
    "retrieval": {
        "practice_stage": "Retrieval quality and ranking",
        "hint_md": "Do not trust a single score blindly. Combine ranking logic with metadata and think about why a candidate deserves to rise.",
        "review_checklist_json": [
            "Did I account for both relevance and metadata?",
            "Would I be able to explain the ranking rule in an interview?",
            "Does the code make future tuning easy?",
        ],
        "success_criteria_json": [
            "Ranking rule is explainable",
            "Supports future iteration without rewriting everything",
            "Feels tied to product trust rather than pure math trivia",
        ],
        "related_lesson_slugs": [
            "rag-systems-2",
            "rag-systems-3",
        ],
    },
    "evaluation": {
        "practice_stage": "Evaluation and review loops",
        "hint_md": "Separate the scoring logic from the interpretation logic. Your goal is not just a number; it is a useful next action.",
        "review_checklist_json": [
            "Would this output help decide what to fix next?",
            "Are important failure modes visible?",
            "Does the score hide any ambiguity I should record?",
        ],
        "success_criteria_json": [
            "Produces a useful signal, not decorative output",
            "Makes regression review easier",
            "Would support a benchmark or observability loop",
        ],
        "related_lesson_slugs": [
            "evaluation-and-observability-1",
            "evaluation-and-observability-2",
        ],
    },
}


def _score_attempt(exercise: Exercise, submitted_code: str) -> tuple[float, str]:
    code = submitted_code.lower()
    score = 58.0

    if "def " in code:
        score += 12
    if "return" in code:
        score += 16

    category_expectations = {
        "python-refresh": ["payload", "status", "content"],
        "data-transformation": ["for ", "append", "count"],
        "api-async": ["async ", "await", "timeout"],
        "prompt-formatting": ["system", "user", "context"],
        "retrieval": ["score", "sorted", "reverse"],
        "evaluation": ["score", "coverage", "faithfulness"],
    }

    for token in category_expectations.get(exercise.category, []):
        if token in code:
            score += 4

    score = min(score, 96.0)
    status = "solid" if score >= 85 else "needs-review" if score >= 72 else "retry"
    return score, status


def _progression_label(exercises: list[Exercise], exercise: Exercise) -> str:
    total = len(exercises)
    index = next((position for position, item in enumerate(exercises, start=1) if item.id == exercise.id), 1)
    return f"Step {index} of {total}"


def _related_lesson_titles(db: Session, slugs: list[str]) -> list[str]:
    if not slugs:
        return []
    lessons = db.scalars(select(Lesson).where(Lesson.slug.in_(slugs))).all()
    title_map = {lesson.slug: lesson.title for lesson in lessons}
    return [title_map[slug] for slug in slugs if slug in title_map]


def _enrich_exercise(db: Session, exercise: Exercise, sibling_exercises: list[Exercise]) -> dict:
    playbook = PRACTICE_PLAYBOOK.get(exercise.category, {})
    next_exercise = None
    for index, candidate in enumerate(sibling_exercises):
        if candidate.id == exercise.id and index + 1 < len(sibling_exercises):
            next_exercise = sibling_exercises[index + 1]
            break

    related_slugs = list(playbook.get("related_lesson_slugs", []))
    return {
        **exercise.__dict__,
        "progression_label": _progression_label(sibling_exercises, exercise),
        "practice_stage": playbook.get("practice_stage"),
        "hint_md": playbook.get("hint_md"),
        "review_checklist_json": list(playbook.get("review_checklist_json", [])),
        "success_criteria_json": list(playbook.get("success_criteria_json", [])),
        "related_lesson_slugs": related_slugs,
        "related_lesson_titles": _related_lesson_titles(db, related_slugs),
        "next_exercise_id": next_exercise.id if next_exercise else None,
        "next_exercise_slug": next_exercise.slug if next_exercise else None,
        "next_exercise_title": next_exercise.title if next_exercise else None,
    }


def list_exercises(db: Session, category: str | None = None, difficulty: str | None = None, search: str | None = None) -> list[Exercise]:
    query = select(Exercise)
    if category:
        query = query.where(Exercise.category == category)
    if difficulty:
        query = query.where(Exercise.difficulty == difficulty)
    if search:
        query = query.where(Exercise.title.ilike(f"%{search}%"))
    exercises = list(db.scalars(query.order_by(Exercise.category.asc(), Exercise.id.asc())).all())
    grouped: dict[str, list[Exercise]] = {}
    for exercise in exercises:
        grouped.setdefault(exercise.category, []).append(exercise)
    return [_enrich_exercise(db, exercise, grouped[exercise.category]) for exercise in exercises]


def get_exercise_detail(db: Session, exercise_id: int, user_id: int) -> dict | None:
    exercise = db.scalar(select(Exercise).where(Exercise.id == exercise_id))
    if not exercise:
        return None
    sibling_exercises = list(
        db.scalars(select(Exercise).where(Exercise.category == exercise.category).order_by(Exercise.id.asc())).all()
    )
    attempts = list(
        db.scalars(
            select(UserExerciseAttempt)
            .where(UserExerciseAttempt.user_id == user_id, UserExerciseAttempt.exercise_id == exercise_id)
            .order_by(desc(UserExerciseAttempt.attempted_at))
        ).all()
    )
    review_prompt = (
        "What part of this implementation felt least trustworthy, and what will you change on the next rep?"
        if attempts
        else "Before you submit, decide what a strong answer should make obvious to the reviewer."
    )
    return {"exercise": _enrich_exercise(db, exercise, sibling_exercises), "attempts": attempts, "review_prompt": review_prompt}


def create_attempt(db: Session, exercise_id: int, user_id: int, submitted_code: str, notes: str) -> UserExerciseAttempt:
    exercise = db.scalar(select(Exercise).where(Exercise.id == exercise_id))
    score, status = _score_attempt(exercise, submitted_code)
    attempt = UserExerciseAttempt(
        user_id=user_id,
        exercise_id=exercise_id,
        submitted_code=submitted_code,
        notes=notes,
        status=status,
        score=score,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    refresh_progress_snapshot(db, user_id)
    return attempt


def recommended_exercises(db: Session) -> list[Exercise]:
    exercises = list(
        db.scalars(
            select(Exercise)
            .where(Exercise.category.in_(["python-refresh", "evaluation", "retrieval"]))
            .order_by(Exercise.category.asc(), Exercise.id.asc())
            .limit(6)
        ).all()
    )
    grouped: dict[str, list[Exercise]] = {}
    for exercise in exercises:
        grouped.setdefault(exercise.category, []).append(exercise)
    return [_enrich_exercise(db, exercise, grouped[exercise.category]) for exercise in exercises]
