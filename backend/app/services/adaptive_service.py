from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Exercise,
    InterviewQuestion,
    InterviewQuestionPractice,
    JobPosting,
    NewsItem,
    Project,
    User,
    UserExerciseAttempt,
)
from app.services.learning_service import list_paths

PATH_MASTERY_CONFIG = {
    "python-for-ai-engineers": {
        "exercise_categories": ["python-refresh", "data-transformation", "api-async"],
        "interview_categories": ["python", "backend"],
        "project_categories": ["eval-tooling", "rag-app"],
    },
    "llm-app-foundations": {
        "exercise_categories": ["prompt-formatting", "api-async"],
        "interview_categories": ["backend", "llm-systems", "system-design"],
        "project_categories": ["rag-app", "agent-system"],
    },
    "rag-systems": {
        "exercise_categories": ["retrieval", "evaluation"],
        "interview_categories": ["rag", "evaluation"],
        "project_categories": ["rag-app", "eval-tooling"],
    },
    "ai-agents-and-tools": {
        "exercise_categories": ["prompt-formatting", "api-async"],
        "interview_categories": ["agents", "system-design"],
        "project_categories": ["agent-system"],
    },
    "evaluation-and-observability": {
        "exercise_categories": ["evaluation", "retrieval"],
        "interview_categories": ["evaluation", "deployment"],
        "project_categories": ["eval-tooling", "rag-app"],
    },
    "ai-deployment-and-mlops": {
        "exercise_categories": ["api-async", "evaluation"],
        "interview_categories": ["deployment", "system-design"],
        "project_categories": ["agent-system", "eval-tooling"],
    },
    "ai-safety-and-guardrails": {
        "exercise_categories": ["evaluation", "api-async"],
        "interview_categories": ["evaluation", "deployment"],
        "project_categories": ["eval-tooling", "agent-system"],
    },
}

NEWS_TO_PATH = {
    "model-release": "llm-app-foundations",
    "agents": "ai-agents-and-tools",
    "retrieval": "rag-systems",
    "evaluation": "evaluation-and-observability",
    "open-source": "ai-deployment-and-mlops",
}

JOB_GAP_TO_PATH = {
    "MLOps depth": "ai-deployment-and-mlops",
    "Kubernetes operations": "ai-deployment-and-mlops",
    "Deep learning breadth": "python-for-ai-engineers",
    "PyTorch practice": "python-for-ai-engineers",
    "Workflow orchestration": "ai-agents-and-tools",
    "Distributed systems depth": "ai-deployment-and-mlops",
}


def build_mastery_profile(db: Session) -> list[dict]:
    user = db.scalar(select(User).limit(1))
    if not user:
        return []

    paths = list_paths(db, user.id)
    attempt_rows = db.execute(
        select(
            Exercise.category,
            func.count(UserExerciseAttempt.id),
            func.avg(UserExerciseAttempt.score),
        )
        .select_from(Exercise)
        .outerjoin(
            UserExerciseAttempt,
            (UserExerciseAttempt.exercise_id == Exercise.id) & (UserExerciseAttempt.user_id == user.id),
        )
        .group_by(Exercise.category)
    ).all()
    attempts_by_category = {
        category: {"count": int(count or 0), "avg_score": float(avg_score or 0)}
        for category, count, avg_score in attempt_rows
    }

    interview_rows = db.execute(
        select(
            InterviewQuestion.category,
            func.count(InterviewQuestionPractice.id),
            func.avg(InterviewQuestionPractice.confidence_score),
        )
        .select_from(InterviewQuestion)
        .outerjoin(InterviewQuestionPractice, InterviewQuestionPractice.question_id == InterviewQuestion.id)
        .group_by(InterviewQuestion.category)
    ).all()
    interview_by_category = {
        category: {"count": int(count or 0), "avg_confidence": float(avg_confidence or 0)}
        for category, count, avg_confidence in interview_rows
    }

    projects = list(db.scalars(select(Project).order_by(Project.portfolio_score.desc(), Project.id.asc())).all())
    projects_by_category: dict[str, list[Project]] = defaultdict(list)
    for project in projects:
        projects_by_category[project.category].append(project)

    demand_by_path = _demand_by_path(db)
    profile: list[dict] = []

    for path in paths:
        config = PATH_MASTERY_CONFIG.get(path["slug"], {})
        completion_score = min(45, path["completion_pct"] * 0.45)

        practice_stats = [attempts_by_category.get(category, {"count": 0, "avg_score": 0.0}) for category in config.get("exercise_categories", [])]
        practice_count = sum(item["count"] for item in practice_stats)
        practice_avg = round(
            sum(item["avg_score"] for item in practice_stats if item["count"]) / max(1, len([item for item in practice_stats if item["count"]])),
            1,
        ) if any(item["count"] for item in practice_stats) else 0.0
        practice_score = min(25, practice_count * 4 + practice_avg * 0.08)

        interview_stats = [interview_by_category.get(category, {"count": 0, "avg_confidence": 0.0}) for category in config.get("interview_categories", [])]
        interview_count = sum(item["count"] for item in interview_stats)
        interview_avg = round(
            sum(item["avg_confidence"] for item in interview_stats if item["count"]) / max(1, len([item for item in interview_stats if item["count"]])),
            1,
        ) if any(item["count"] for item in interview_stats) else 0.0
        interview_score = min(15, interview_count * 2 + interview_avg * 1.5)

        related_projects = []
        for category in config.get("project_categories", []):
            related_projects.extend(projects_by_category.get(category, []))
        project_score = _project_score(related_projects)

        demand_score = demand_by_path.get(path["slug"], 0)
        mastery_score = int(round(min(100, completion_score + practice_score + interview_score + project_score + demand_score)))

        weakest_signal, gap_text, next_step = _next_mastery_move(path, config, practice_count, interview_count)
        evidence = (
            f"{path['completion_pct']}% lesson completion, {practice_count} related drill reps, "
            f"{interview_count} interview rep(s), demand score {demand_score}."
        )

        profile.append(
            {
                "area_slug": path["slug"],
                "area_title": path["title"],
                "mastery_score": mastery_score,
                "status": _mastery_status(mastery_score),
                "evidence": evidence,
                "gap": gap_text,
                "weakest_signal": weakest_signal,
                "next_action_path": next_step["action_path"],
                "next_action_label": next_step["label"],
            }
        )

    return sorted(profile, key=lambda item: (item["mastery_score"], item["area_title"]))


def build_adaptive_focus(db: Session) -> dict | None:
    profile = build_mastery_profile(db)
    if not profile:
        return None

    weakest = profile[0]
    return {
        "title": f"Adaptive sprint: {weakest['area_title']}",
        "reason": f"{weakest['gap']} {weakest['evidence']}",
        "action_path": weakest["next_action_path"],
        "target_kind": weakest["weakest_signal"],
        "mastery_score": weakest["mastery_score"],
        "area_slug": weakest["area_slug"],
        "area_title": weakest["area_title"],
        "action_label": weakest["next_action_label"],
    }


def _project_score(projects: list[Project]) -> int:
    if not projects:
        return 0
    complete = [project for project in projects if project.status == "complete"]
    active = [project for project in projects if project.status == "active"]
    score = 0
    if complete:
        score += min(10, int(sum(project.portfolio_score for project in complete) / len(complete) * 0.08))
    elif active:
        score += min(7, int(sum(project.portfolio_score for project in active) / len(active) * 0.05))
    return min(10, score)


def _demand_by_path(db: Session) -> dict[str, int]:
    demand: dict[str, int] = defaultdict(int)
    saved_news = list(db.scalars(select(NewsItem).where(NewsItem.is_saved.is_(True))).all())
    top_news = db.scalar(select(NewsItem).order_by(NewsItem.signal_score.desc(), NewsItem.published_at.desc()))
    for item in saved_news[:3]:
        slug = NEWS_TO_PATH.get(item.category)
        if slug:
            demand[slug] += 8
    if top_news:
        slug = NEWS_TO_PATH.get(top_news.category)
        if slug:
            demand[slug] += 4

    saved_jobs = list(db.scalars(select(JobPosting).where(JobPosting.is_saved.is_(True))).all())
    top_job = db.scalar(select(JobPosting).order_by(JobPosting.fit_score.desc(), JobPosting.published_at.desc()))
    for job in saved_jobs[:3]:
        for gap in job.skill_gaps_json or []:
            slug = JOB_GAP_TO_PATH.get(gap)
            if slug:
                demand[slug] += 6
    if top_job:
        for gap in (top_job.skill_gaps_json or [])[:1]:
            slug = JOB_GAP_TO_PATH.get(gap)
            if slug:
                demand[slug] += 3
    return demand


def _next_mastery_move(path: dict, config: dict, practice_count: int, interview_count: int) -> tuple[str, str, dict]:
    next_lesson = next((lesson for lesson in path["lessons"] if not lesson["is_completed"]), None)
    if path["completion_pct"] < 60 and next_lesson:
        return (
            "lesson",
            f"Curriculum depth in {path['title']} is still incomplete, so the biggest gain is finishing the next unfinished lesson.",
            {"action_path": f"/learn/lesson/{next_lesson['slug']}", "label": f"Open {next_lesson['title']}"},
        )
    if practice_count < 4:
        return (
            "practice",
            f"You have not done enough related drills in {path['title']} to trust the skill under pressure yet.",
            {"action_path": "/practice/python", "label": "Run a related drill"},
        )
    if interview_count < 2:
        return (
            "interview",
            f"You have content and practice here, but not enough spoken reps to explain the skill clearly in interviews.",
            {"action_path": "/interview", "label": "Log an interview rep"},
        )
    return (
        "projects",
        f"The next gain in {path['title']} should come from turning the skill into visible project proof.",
        {"action_path": "/projects", "label": "Strengthen a project proof point"},
    )


def _mastery_status(score: int) -> str:
    if score >= 75:
        return "solid"
    if score >= 45:
        return "developing"
    return "fragile"
