from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import adaptive, ai_feedback, copilot, courses, critique, dashboard, deep_dives, dub, exercise_variations, exercises, interview, interview_coaching, jobs, knowledge, learning, live_jobs, memory, news, podcast, projects, qian, recommendations, resume, scribe, streaks, summary, ziwei

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
api_router.include_router(interview_coaching.router)
api_router.include_router(recommendations.router)
api_router.include_router(adaptive.router)
api_router.include_router(deep_dives.router)
api_router.include_router(exercise_variations.router)
api_router.include_router(ai_feedback.router)
api_router.include_router(copilot.router)
api_router.include_router(memory.router)
api_router.include_router(resume.router)
api_router.include_router(streaks.router)
api_router.include_router(live_jobs.router)
api_router.include_router(podcast.router)
api_router.include_router(dub.router)
api_router.include_router(summary.router)
api_router.include_router(scribe.router)
api_router.include_router(ziwei.router)
api_router.include_router(qian.router)
api_router.include_router(critique.router)
