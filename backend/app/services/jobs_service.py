from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models import JobPosting, User
from app.seed.data import JOB_POSTINGS

JOB_SOURCES = [
    {"source_name": "Remotive", "url": "https://remotive.com/api/remote-jobs?search=ai%20engineer"},
    {"source_name": "Arbeitnow", "url": "https://www.arbeitnow.com/api/job-board-api"},
]
JOBS_AUTO_REFRESH_HOURS = 12


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "job"


def list_jobs(
    db: Session,
    search: str | None = None,
    saved_only: bool = False,
    min_fit_score: int | None = None,
) -> list[JobPosting]:
    query = select(JobPosting)
    if search:
        query = query.where(
            or_(
                JobPosting.title.ilike(f"%{search}%"),
                JobPosting.company_name.ilike(f"%{search}%"),
                JobPosting.summary.ilike(f"%{search}%"),
            )
        )
    if saved_only:
        query = query.where(JobPosting.is_saved.is_(True))
    if min_fit_score is not None:
        query = query.where(JobPosting.fit_score >= min_fit_score)
    return list(db.scalars(query.order_by(desc(JobPosting.fit_score), desc(JobPosting.published_at))).all())


def get_jobs_refresh_meta(db: Session) -> dict:
    items = list_jobs(db)
    latest_sync = max((item.last_synced_at for item in items), default=datetime.utcnow())
    live_count = sum(1 for item in items if not item.is_seeded)
    seeded_count = sum(1 for item in items if item.is_seeded)
    return {
        "source": "live" if live_count else "seeded",
        "item_count": len(items),
        "live_item_count": live_count,
        "seeded_item_count": seeded_count,
        "refreshed_at": latest_sync,
        "is_stale": _is_refresh_stale(latest_sync, JOBS_AUTO_REFRESH_HOURS),
        "refresh_window_hours": JOBS_AUTO_REFRESH_HOURS,
        "auto_refresh_enabled": True,
    }


def get_job(db: Session, job_id: int) -> JobPosting | None:
    return db.scalar(select(JobPosting).where(JobPosting.id == job_id))


def set_job_saved(db: Session, job_id: int, saved: bool = True) -> JobPosting | None:
    job = get_job(db, job_id)
    if not job:
        return None
    job.is_saved = saved
    db.commit()
    db.refresh(job)
    return job


def ensure_seed_jobs(db: Session) -> None:
    if db.scalar(select(JobPosting.id).limit(1)):
        return
    user = db.scalar(select(User).limit(1))
    now = datetime.utcnow()
    for payload in JOB_POSTINGS:
        job = JobPosting(published_at=now, is_seeded=True, last_synced_at=now, **payload)
        strengths, gaps, rationale, fit_score = analyze_fit_for_text(
            user,
            f"{job.title} {job.summary}",
            f"{job.description_md} {' '.join(job.tags_json)}",
        )
        job.skill_gaps_json = gaps
        job.fit_score = fit_score
        db.add(job)
    db.flush()


def refresh_jobs(db: Session) -> list[JobPosting]:
    fetched = _fetch_remote_jobs()
    if not fetched:
        return list_jobs(db)

    user = db.scalar(select(User).limit(1))
    sync_time = datetime.utcnow()
    existing = {item.source_url: item for item in db.scalars(select(JobPosting)).all()}
    for payload in fetched:
        job = existing.get(payload["source_url"])
        if not job:
            job = JobPosting(source_url=payload["source_url"], slug=payload["slug"])
            db.add(job)
        job.source_name = payload["source_name"]
        job.title = payload["title"]
        job.slug = payload["slug"]
        job.company_name = payload["company_name"]
        job.location = payload["location"]
        job.employment_type = payload["employment_type"]
        job.summary = payload["summary"]
        job.description_md = payload["description_md"]
        job.published_at = payload["published_at"]
        job.tags_json = payload["tags_json"]
        job.is_seeded = False
        job.last_synced_at = sync_time
        _, gaps, _, fit_score = analyze_fit_for_text(user, f"{job.title} {job.summary}", job.description_md)
        job.skill_gaps_json = gaps
        job.fit_score = fit_score
    db.commit()
    return list_jobs(db)


def refresh_jobs_if_stale(db: Session) -> list[JobPosting]:
    current_jobs = list_jobs(db)
    latest_sync = max((job.last_synced_at for job in current_jobs), default=None)
    if latest_sync and not _is_refresh_stale(latest_sync, JOBS_AUTO_REFRESH_HOURS):
        return current_jobs
    return refresh_jobs(db)


def analyze_job_fit(db: Session, job_id: int) -> dict | None:
    job = get_job(db, job_id)
    user = db.scalar(select(User).limit(1))
    if not job or not user:
        return None

    strengths, gaps, rationale, fit_score = analyze_fit_for_text(user, f"{job.title} {job.summary}", job.description_md)
    job.skill_gaps_json = gaps
    job.fit_score = fit_score
    db.commit()
    db.refresh(job)
    return {
        "job_id": job.id,
        "fit_score": fit_score,
        "strengths": strengths,
        "gaps": gaps,
        "rationale": rationale,
    }


def analyze_fit_for_text(user: User | None, headline: str, details: str) -> tuple[list[str], list[str], str, int]:
    target_text = f"{headline} {details}".lower()
    strengths: list[str] = []
    gaps: list[str] = []
    score = 45

    desired_matches = {
        "python": "Python",
        "rag": "RAG",
        "retrieval": "Retrieval systems",
        "agent": "Agents and tools",
        "evaluation": "Evaluation",
        "observability": "Observability",
        "deployment": "Deployment",
        "fastapi": "FastAPI / backend APIs",
        "nextjs": "Next.js / frontend systems",
    }
    for keyword, label in desired_matches.items():
        if keyword in target_text:
            score += 6
            strengths.append(label)

    likely_gaps = {
        "mlops": "MLOps depth",
        "kubernetes": "Kubernetes operations",
        "deep learning": "Deep learning breadth",
        "pytorch": "PyTorch practice",
        "airflow": "Workflow orchestration",
    }
    for keyword, label in likely_gaps.items():
        if keyword in target_text:
            gaps.append(label)

    if user:
        if user.target_role.lower() in target_text:
            score += 10
        for area in user.preferences_json.get("preferred_topics", []):
            if area.replace("-", " ") in target_text or area in target_text:
                score += 5

    if not strengths:
        strengths = ["General AI product engineering overlap"]
    rationale = (
        "Strongest overlap comes from product-minded full-stack delivery, backend API ownership, and the portal's "
        "current focus areas around Python, RAG, agents, evaluation, and deployment."
    )
    return strengths[:4], gaps[:4], rationale, min(score, 98)


def _fetch_remote_jobs() -> list[dict]:
    results: list[dict] = []
    with httpx.Client(timeout=12.0, follow_redirects=True, headers={"User-Agent": "AIEngineerPortal/1.0"}) as client:
        for source in JOB_SOURCES:
            try:
                response = client.get(source["url"])
                response.raise_for_status()
                payload = response.json()
            except Exception:
                continue
            results.extend(_parse_jobs_payload(source["source_name"], payload))
    deduped: dict[str, dict] = {}
    for item in results:
        deduped[item["source_url"]] = item
    return list(deduped.values())[:18]


def _parse_jobs_payload(source_name: str, payload: dict | list) -> list[dict]:
    jobs: list[dict] = []
    raw_jobs = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw_jobs, list):
        return jobs

    for raw in raw_jobs:
        if not isinstance(raw, dict):
            continue
        title = (raw.get("title") or raw.get("position") or "").strip()
        company = (raw.get("company_name") or raw.get("company") or "").strip()
        url = (raw.get("url") or raw.get("job_url") or raw.get("apply_url") or "").strip()
        description = raw.get("description") or raw.get("description_html") or raw.get("candidate_required_location") or ""
        location = raw.get("candidate_required_location") or raw.get("location") or "Remote"
        employment_type = raw.get("job_type") or raw.get("employment_type") or "unknown"
        tags = raw.get("tags") or raw.get("category") or []
        published_raw = raw.get("publication_date") or raw.get("created_at") or raw.get("date")
        if not title or not company or not url:
            continue
        jobs.append(
            {
                "source_name": source_name,
                "title": title,
                "slug": _slugify(f"{source_name}-{company}-{title}"),
                "company_name": company,
                "location": str(location),
                "employment_type": str(employment_type),
                "summary": _strip_html(description)[:280],
                "source_url": url,
                "description_md": _strip_html(description)[:2000],
                "published_at": _parse_job_datetime(published_raw),
                "tags_json": _normalize_tags(tags),
            }
        )
    return jobs


def _normalize_tags(raw_tags: object) -> list[str]:
    if isinstance(raw_tags, list):
        return [str(tag).lower() for tag in raw_tags][:8]
    if isinstance(raw_tags, str):
        return [part.strip().lower() for part in raw_tags.split(",") if part.strip()][:8]
    return []


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


def _parse_job_datetime(value: object) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.utcnow()


def _is_refresh_stale(refreshed_at: datetime | None, refresh_window_hours: int) -> bool:
    if refreshed_at is None:
        return True
    return refreshed_at <= datetime.utcnow() - timedelta(hours=refresh_window_hours)
