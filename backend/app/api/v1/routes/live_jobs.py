"""Live job search endpoint using Himalayas API."""
import asyncio
from fastapi import APIRouter, Query

from app.services.job_search_service import search_jobs

router = APIRouter(prefix="/jobs", tags=["live-jobs"])


@router.get("/live")
async def get_live_jobs(
    query: str = Query(default="ai engineer", max_length=100),
    limit: int = Query(default=20, le=50),
):
    """Search real AI engineer jobs via Himalayas API."""
    jobs = await search_jobs(query=query, limit=limit)
    return {"jobs": jobs, "total": len(jobs), "source": "himalayas.app"}
