from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models import (
    InterviewQuestion,
    InterviewQuestionPractice,
    JobPosting,
    LessonCompletion,
    LearningPath,
    NewsItem,
    ProgressSnapshot,
    Project,
    User,
    UserExerciseAttempt,
)


def list_questions(db: Session, category: str | None = None) -> list[dict]:
    user = _default_user(db)
    query = select(InterviewQuestion)
    if category:
        query = query.where(InterviewQuestion.category == category)
    questions = list(db.scalars(query.order_by(InterviewQuestion.category.asc(), InterviewQuestion.id.asc())).all())
    if not user:
        return [{**question.__dict__, "practice_count": 0, "last_practiced_at": None, "average_confidence": None} for question in questions]

    practice_rows = db.execute(
        select(
            InterviewQuestionPractice.question_id,
            func.count(InterviewQuestionPractice.id),
            func.max(InterviewQuestionPractice.practiced_at),
            func.avg(InterviewQuestionPractice.confidence_score),
        )
        .where(InterviewQuestionPractice.user_id == user.id)
        .group_by(InterviewQuestionPractice.question_id)
    ).all()
    practice_map = {
        row[0]: {"practice_count": row[1], "last_practiced_at": row[2], "average_confidence": round(float(row[3]), 1)}
        for row in practice_rows
    }
    return [{**question.__dict__, **practice_map.get(question.id, {"practice_count": 0, "last_practiced_at": None, "average_confidence": None})} for question in questions]


def record_question_practice(db: Session, question_id: int, confidence_score: int, notes: str) -> dict | None:
    user = _default_user(db)
    question = db.scalar(select(InterviewQuestion).where(InterviewQuestion.id == question_id))
    if not user or not question:
        return None
    practice = InterviewQuestionPractice(
        user_id=user.id,
        question_id=question_id,
        confidence_score=max(1, min(confidence_score, 5)),
        notes=notes,
    )
    db.add(practice)
    db.commit()
    stats = db.execute(
        select(
            func.count(InterviewQuestionPractice.id),
            func.max(InterviewQuestionPractice.practiced_at),
            func.avg(InterviewQuestionPractice.confidence_score),
        ).where(
            InterviewQuestionPractice.user_id == user.id,
            InterviewQuestionPractice.question_id == question_id,
        )
    ).one()
    return {
        "question_id": question_id,
        "practice_count": stats[0],
        "last_practiced_at": stats[1],
        "average_confidence": round(float(stats[2]), 1),
    }


def build_roadmap(db: Session) -> dict:
    snapshot = _latest_snapshot(db)
    top_job = _top_job_signal(db)
    top_news = _top_news_signal(db)
    completed_projects = _completed_projects_count(db)
    practice_count = snapshot.python_practice_count if snapshot else 0
    readiness = snapshot.interview_readiness_score if snapshot else 0
    interview_practice_count = _interview_practice_count(db)

    focus_areas: list[str] = []
    rationale: list[str] = []

    if practice_count < 3:
        focus_areas.append("Python fluency under interview pressure")
        rationale.append("Practice volume is still low, so implementation confidence needs more reps.")

    if completed_projects < 1:
        focus_areas.append("Project proof that can survive interview scrutiny")
        rationale.append("You need at least one clearly finished project story to anchor system design and behavioral answers.")

    if readiness < 55 or interview_practice_count < 3:
        focus_areas.append("Transition narrative and behavioral story structure")
        rationale.append("Interview reps are still sparse, so spoken explanation quality matters more than adding breadth.")

    if top_job and top_job.skill_gaps_json:
        focus_areas.append(f"Role-aligned gap: {top_job.skill_gaps_json[0]}")
        rationale.append(f"The strongest live role signal currently points to {top_job.skill_gaps_json[0]}.")

    if top_news:
        focus_areas.append(_news_focus_area(top_news.category))
        rationale.append(f"Current market movement is strongest around {top_news.category.replace('-', ' ')}.")

    if not focus_areas:
        focus_areas = [
            "LLM system design and tradeoffs",
            "RAG retrieval and evaluation debugging",
            "Behavioral stories for the transition narrative",
        ]
        rationale = [
            "Your baseline is strong enough that the next gains come from sharper explanation and tradeoff clarity."
        ]

    weekly_plan = [
        _python_day(plan_needed=practice_count < 3),
        _system_day(top_news.category if top_news else None),
        _interview_day(readiness, completed_projects, interview_practice_count),
    ]

    return {
        "focus_areas": _dedupe_keep_order(focus_areas)[:4],
        "weekly_plan": weekly_plan,
        "rationale": _dedupe_keep_order(rationale)[:4],
    }


def build_portfolio_readiness(db: Session) -> dict:
    snapshot = _latest_snapshot(db)
    completed_projects = list(
        db.scalars(select(Project).where(Project.status == "complete").order_by(desc(Project.portfolio_score), Project.id.asc())).all()
    )
    active_projects = list(
        db.scalars(select(Project).where(Project.status.in_(["active", "planned"])).order_by(desc(Project.portfolio_score), Project.id.asc())).all()
    )
    saved_jobs = list(db.scalars(select(JobPosting).where(JobPosting.is_saved.is_(True)).order_by(desc(JobPosting.fit_score))).all())
    saved_news = list(db.scalars(select(NewsItem).where(NewsItem.is_saved.is_(True)).order_by(desc(NewsItem.signal_score))).all())
    interview_practice = _interview_practice_count(db)

    strongest_signals: list[str] = []
    gaps_to_close: list[str] = []
    next_best_moves: list[str] = []

    avg_completed_score = int(sum(project.portfolio_score for project in completed_projects) / len(completed_projects)) if completed_projects else 0
    avg_active_score = int(sum(project.portfolio_score for project in active_projects) / len(active_projects)) if active_projects else 0
    readiness = snapshot.interview_readiness_score if snapshot else 0
    learning = snapshot.learning_completion_pct if snapshot else 0.0
    practice = snapshot.python_practice_count if snapshot else 0

    score = min(
        100,
        int(
            min(30, avg_completed_score * 0.3)
            + min(15, avg_active_score * 0.15)
            + min(18, len(completed_projects) * 9)
            + min(12, len(saved_jobs) * 4)
            + min(10, len(saved_news) * 3)
            + min(8, interview_practice * 2)
            + min(12, readiness * 0.12)
            + min(10, learning * 0.2)
            + min(8, practice * 1.5)
        ),
    )

    if completed_projects:
        strongest_signals.append(f"{len(completed_projects)} completed project artifact(s) with an average portfolio score of {avg_completed_score}.")
    elif active_projects:
        strongest_signals.append(f"{len(active_projects)} active or planned project(s) are in flight with an average portfolio score of {avg_active_score}.")
    if saved_jobs:
        strongest_signals.append(f"You are calibrating against {len(saved_jobs)} saved role(s) from the live job market.")
    if saved_news:
        strongest_signals.append(f"You are tracking {len(saved_news)} saved market signal(s) and feeding them back into learning decisions.")
    if interview_practice:
        strongest_signals.append(f"You have already logged {interview_practice} interview practice rep(s).")

    if not completed_projects:
        gaps_to_close.append("Finish one project so it becomes a concrete interview proof point.")
        target = active_projects[0].title if active_projects else "your strongest active project"
        next_best_moves.append(f"Move {target} to complete status with tighter architecture notes and clearer outcomes.")
    if readiness < 55:
        gaps_to_close.append("Interview explanation quality still trails your raw implementation progress.")
        next_best_moves.append("Practice one system design and one behavioral answer each week using your actual project evidence.")
    if practice < 4:
        gaps_to_close.append("Python implementation fluency still needs more live reps under light time pressure.")
        next_best_moves.append("Rotate through Python, async, retrieval, and evaluation drills instead of repeating only one category.")
    if saved_jobs and saved_jobs[0].skill_gaps_json:
        gap = saved_jobs[0].skill_gaps_json[0]
        gaps_to_close.append(f"Top saved-role gap: {gap}.")
        next_best_moves.append(f"Use the saved-role gap '{gap}' to choose the next lesson, drill, or project refinement.")
    if interview_practice < 3:
        gaps_to_close.append("Interview practice volume is still too low to trust answer structure under pressure.")
        next_best_moves.append("Mark practiced questions in the interview center and push average confidence upward over time.")

    if not strongest_signals:
        strongest_signals.append("The portal foundation is in place, but Phase 3 needs more shipped proof and repeated interview reps.")
    if not gaps_to_close:
        gaps_to_close.append("The remaining gains are mostly about sharper positioning, not missing fundamentals.")
    if not next_best_moves:
        next_best_moves.append("Keep tightening finished projects, saved-role alignment, and interview story clarity.")

    return {
        "overall_score": score,
        "strongest_signals": strongest_signals[:4],
        "gaps_to_close": gaps_to_close[:4],
        "next_best_moves": next_best_moves[:4],
    }


def build_skill_gap_summary(db: Session) -> list[dict]:
    snapshot = _latest_snapshot(db)
    completed_lesson_ids = set(db.scalars(select(LessonCompletion.lesson_id)).all())
    low_progress_path = None
    for path in db.scalars(select(LearningPath).order_by(LearningPath.order_index.asc())).all():
        total = len(path.lessons)
        completed = len([lesson for lesson in path.lessons if lesson.id in completed_lesson_ids])
        completion_pct = round((completed / (total or 1)) * 100, 1)
        if completion_pct < 40:
            low_progress_path = (path, completion_pct)
            break

    saved_job = _top_job_signal(db)
    gaps: list[dict] = []

    if saved_job and saved_job.skill_gaps_json:
        gap = saved_job.skill_gaps_json[0]
        gaps.append(
            {
                "title": gap,
                "urgency": "high",
                "evidence": f"Top role signal from {saved_job.company_name} is still exposing this gap.",
                "action_path": "/jobs",
            }
        )

    readiness = snapshot.interview_readiness_score if snapshot else 0
    if readiness < 55:
        gaps.append(
            {
                "title": "Interview communication",
                "urgency": "high" if readiness < 35 else "medium",
                "evidence": f"Interview readiness is currently {readiness}/100.",
                "action_path": "/interview",
            }
        )

    if low_progress_path:
        path, completion_pct = low_progress_path
        gaps.append(
            {
                "title": path.title,
                "urgency": "medium",
                "evidence": f"Learning progress in this path is only {completion_pct}%, so it is still underdeveloped.",
                "action_path": f"/learn/{path.slug}",
            }
        )

    practice_count = snapshot.python_practice_count if snapshot else 0
    if practice_count < 4:
        gaps.append(
            {
                "title": "Practice repetition",
                "urgency": "medium",
                "evidence": f"Only {practice_count} coding practice attempt(s) have been logged so far.",
                "action_path": "/practice/python",
            }
        )

    return gaps[:4]


def _default_user(db: Session) -> User | None:
    return db.scalar(select(User).limit(1))


def _latest_snapshot(db: Session) -> ProgressSnapshot | None:
    return db.scalar(
        select(ProgressSnapshot).order_by(ProgressSnapshot.date.desc(), ProgressSnapshot.id.desc())
    )


def _completed_projects_count(db: Session) -> int:
    return db.scalar(select(func.count(Project.id)).where(Project.status == "complete")) or 0


def _interview_practice_count(db: Session) -> int:
    return db.scalar(select(func.count(InterviewQuestionPractice.id))) or 0


def _top_job_signal(db: Session) -> JobPosting | None:
    saved = db.scalar(select(JobPosting).where(JobPosting.is_saved.is_(True)).order_by(desc(JobPosting.fit_score)))
    if saved:
        return saved
    return db.scalar(select(JobPosting).order_by(desc(JobPosting.fit_score), desc(JobPosting.published_at)))


def _top_news_signal(db: Session) -> NewsItem | None:
    saved = db.scalar(select(NewsItem).where(NewsItem.is_saved.is_(True)).order_by(desc(NewsItem.signal_score)))
    if saved:
        return saved
    return db.scalar(select(NewsItem).order_by(desc(NewsItem.signal_score), desc(NewsItem.published_at)))


def _python_day(plan_needed: bool) -> str:
    if plan_needed:
        return "Monday: two short Python drills, one async and one data-modeling, then explain the tradeoffs out loud."
    return "Monday: one timed Python or evaluation drill and a quick self-review on what still feels slow."


def _system_day(news_category: str | None) -> str:
    if news_category == "agents":
        return "Wednesday: one agent-system design answer plus one workflow orchestration note tied to a saved signal."
    if news_category == "retrieval":
        return "Wednesday: one RAG debugging answer and one retrieval-evaluation note tied to a live signal."
    return "Wednesday: one LLM system design answer tied to your strongest live market signal."


def _interview_day(readiness: int, completed_projects: int, interview_practice_count: int) -> str:
    if completed_projects < 1:
        return "Friday: refine one project story so you can explain scope, architecture, metrics, and tradeoffs clearly."
    if readiness < 55 or interview_practice_count < 3:
        return "Friday: rehearse one behavioral answer and one system design answer using your strongest completed project."
    return "Friday: run a full mock loop with one coding, one system design, and one behavioral answer."


def _news_focus_area(category: str) -> str:
    return {
        "model-release": "Model and API tradeoff awareness",
        "agents": "Agent control flow and tool orchestration",
        "retrieval": "RAG architecture and retrieval debugging",
        "evaluation": "Evaluation design and observability",
        "open-source": "Tooling decisions and deployment shape",
    }.get(category, "External signal translation")


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered
