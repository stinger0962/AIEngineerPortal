from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import adaptive, ai_feedback, courses, dashboard, deep_dives, exercise_variations, exercises, interview, jobs, knowledge, learning, news, projects, recommendations

api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(learning.router)
api_router.include_router(courses.router)
api_router.include_router(exercises.router)
api_router.include_router(knowledge.router)
api_router.include_router(news.router)
api_router.include_router(jobs.router)
api_router.include_router(projects.router)
api_router.include_router(interview.router)
api_router.include_router(recommendations.router)
api_router.include_router(adaptive.router)
api_router.include_router(deep_dives.router)
api_router.include_router(exercise_variations.router)
api_router.include_router(ai_feedback.router)
