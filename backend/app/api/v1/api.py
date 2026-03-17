from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import courses, dashboard, exercises, interview, knowledge, learning, projects, recommendations

api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(learning.router)
api_router.include_router(courses.router)
api_router.include_router(exercises.router)
api_router.include_router(knowledge.router)
api_router.include_router(projects.router)
api_router.include_router(interview.router)
api_router.include_router(recommendations.router)
