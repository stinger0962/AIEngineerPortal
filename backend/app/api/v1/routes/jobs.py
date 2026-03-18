from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import FeedRefreshMetaOut, JobFitAnalysisOut, JobPostingOut
from app.services.jobs_service import analyze_job_fit, get_job, get_jobs_refresh_meta, list_jobs, refresh_jobs, set_job_saved

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[JobPostingOut])
def get_jobs(
    search: Optional[str] = Query(default=None),
    saved_only: bool = Query(default=False),
    min_fit_score: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[JobPostingOut]:
    return [JobPostingOut.model_validate(job) for job in list_jobs(db, search, saved_only, min_fit_score)]


@router.post("/refresh", response_model=List[JobPostingOut])
def refresh_jobs_feed(db: Session = Depends(get_db)) -> List[JobPostingOut]:
    return [JobPostingOut.model_validate(job) for job in refresh_jobs(db)]


@router.get("/meta", response_model=FeedRefreshMetaOut)
def get_jobs_meta(db: Session = Depends(get_db)) -> FeedRefreshMetaOut:
    return FeedRefreshMetaOut(**get_jobs_refresh_meta(db))


@router.get("/{job_id}", response_model=JobPostingOut)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)) -> JobPostingOut:
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobPostingOut.model_validate(job)


@router.post("/{job_id}/save", response_model=JobPostingOut)
def save_job(job_id: int, db: Session = Depends(get_db)) -> JobPostingOut:
    job = set_job_saved(db, job_id, True)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobPostingOut.model_validate(job)


@router.post("/{job_id}/analyze-fit", response_model=JobFitAnalysisOut)
def analyze_fit(job_id: int, db: Session = Depends(get_db)) -> JobFitAnalysisOut:
    result = analyze_job_fit(db, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobFitAnalysisOut(**result)
