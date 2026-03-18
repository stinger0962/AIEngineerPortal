from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models import JobPosting, User
from app.seed.data import JOB_POSTINGS

JOBS_AUTO_REFRESH_HOURS = 12
MAX_JOB_ITEMS = 18
MIN_LIVE_JOB_KEEP_COUNT = 5

JOB_SOURCES = [
    {
        "source_name": "Remotive",
        "url": "https://remotive.com/api/remote-jobs",
        "params": [{"search": value} for value in ["ai engineer", "applied ai", "llm engineer", "rag engineer"]],
        "priority": 1.0,
    },
    {
        "source_name": "Arbeitnow",
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "params": [{}],
        "priority": 0.8,
    },
]

JOB_RELEVANCE_WEIGHTS = {
    "ai engineer": 18,
    "applied ai": 16,
    "llm engineer": 16,
    "machine learning engineer": 10,
    "rag": 14,
    "retrieval": 12,
    "agent": 12,
    "agents": 12,
    "evaluation": 10,
    "python": 8,
    "fastapi": 7,
    "next.js": 6,
    "nextjs": 6,
    "api": 5,
    "deployment": 8,
    "observability": 8,
    "platform": 6,
    "inference": 8,
    "prompt": 5,
    "tooling": 5,
}

ROLE_FILTER_TERMS = [
    "ai engineer",
    "applied ai",
    "llm engineer",
    "machine learning engineer",
    "ml engineer",
    "platform engineer",
    "software engineer, ai",
]


def _contains_phrase(haystack: str, phrase: str) -> bool:
    pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"[\s/-]+") + r"\b"
    return re.search(pattern, haystack) is not None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "job"


def _normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    filtered_query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=False)
        if not key.lower().startswith("utm_")
    ]
    normalized_path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), normalized_path, "", urlencode(filtered_query), ""))


def _job_identity_key(company: str, title: str) -> str:
    return _slugify(f"{company}-{title}")[:180]


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
    if live_count and seeded_count:
        source = "mixed"
    elif live_count:
        source = "live"
    else:
        source = "seeded"
    return {
        "source": source,
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
    existing_items = db.scalars(select(JobPosting)).all()
    existing_by_url = {_normalize_url(item.source_url): item for item in existing_items}
    existing_by_identity = {_job_identity_key(item.company_name, item.title): item for item in existing_items}

    for payload in fetched:
        normalized_url = _normalize_url(payload["source_url"])
        job = existing_by_url.get(normalized_url) or existing_by_identity.get(
            _job_identity_key(payload["company_name"], payload["title"])
        )
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
        job.source_url = normalized_url
        job.description_md = payload["description_md"]
        job.published_at = payload["published_at"]
        job.tags_json = payload["tags_json"]
        job.is_seeded = False
        job.last_synced_at = sync_time
        _, gaps, _, fit_score = analyze_fit_for_text(user, f"{job.title} {job.summary}", job.description_md)
        job.skill_gaps_json = gaps
        job.fit_score = max(payload["relevance_score"], fit_score)

    db.flush()

    if len(fetched) >= MIN_LIVE_JOB_KEEP_COUNT:
        for seeded_job in db.scalars(select(JobPosting).where(JobPosting.is_seeded.is_(True))).all():
            db.delete(seeded_job)

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
        "platform": "Platform thinking",
        "api": "API ownership",
    }
    for keyword, label in desired_matches.items():
        if _contains_phrase(target_text, keyword):
            score += 6
            strengths.append(label)

    likely_gaps = {
        "mlops": "MLOps depth",
        "kubernetes": "Kubernetes operations",
        "deep learning": "Deep learning breadth",
        "pytorch": "PyTorch practice",
        "airflow": "Workflow orchestration",
        "distributed": "Distributed systems depth",
    }
    for keyword, label in likely_gaps.items():
        if _contains_phrase(target_text, keyword):
            gaps.append(label)

    if user:
        if _contains_phrase(target_text, user.target_role.lower()):
            score += 10
        for area in user.preferences_json.get("preferred_topics", []):
            if _contains_phrase(target_text, area.replace("-", " ")) or _contains_phrase(target_text, area):
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
            for params in source["params"]:
                try:
                    response = client.get(source["url"], params=params)
                    response.raise_for_status()
                    payload = response.json()
                except Exception:
                    continue
                results.extend(_parse_jobs_payload(source, payload))
    return _dedupe_and_rank_jobs(results)


def _parse_jobs_payload(source: dict, payload: dict | list) -> list[dict]:
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

        description_text = _strip_html(description)
        relevance_score = _score_job_relevance(title, description_text, tags, source["priority"])
        if relevance_score < 55 or not _looks_like_relevant_role(title, description_text):
            continue

        jobs.append(
            {
                "source_name": source["source_name"],
                "title": title,
                "slug": _slugify(f"{source['source_name']}-{company}-{title}"),
                "company_name": company,
                "location": str(location),
                "employment_type": _normalize_employment_type(str(employment_type)),
                "summary": description_text[:280],
                "source_url": _normalize_url(url),
                "description_md": description_text[:2500],
                "published_at": _parse_job_datetime(published_raw),
                "tags_json": _normalize_tags(tags, title, description_text),
                "relevance_score": relevance_score,
            }
        )
    return jobs


def _normalize_tags(raw_tags: object, title: str, description: str) -> list[str]:
    tags: set[str] = set()
    if isinstance(raw_tags, list):
        tags.update(str(tag).lower() for tag in raw_tags[:8])
    elif isinstance(raw_tags, str):
        tags.update(part.strip().lower() for part in raw_tags.split(",") if part.strip())

    haystack = f"{title} {description}".lower()
    for keyword in JOB_RELEVANCE_WEIGHTS:
        if _contains_phrase(haystack, keyword):
            tags.add(keyword.replace(" ", "-"))
    return sorted(tags)[:8]


def _normalize_employment_type(raw_value: str) -> str:
    value = raw_value.lower()
    if "full" in value:
        return "full-time"
    if "part" in value:
        return "part-time"
    if "contract" in value:
        return "contract"
    return value or "unknown"


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_relevant_role(title: str, description: str) -> bool:
    haystack = f"{title} {description}".lower()
    title_text = title.lower()
    return any(_contains_phrase(title_text, term) for term in ROLE_FILTER_TERMS) or (
        any(_contains_phrase(haystack, term) for term in ["rag", "retrieval", "agent", "evaluation", "llm"])
        and any(_contains_phrase(haystack, term) for term in ["engineer", "developer", "architect"])
    )


def _score_job_relevance(title: str, description: str, tags: object, source_priority: float) -> int:
    haystack = f"{title} {description} {tags}".lower()
    score = 34 + int(source_priority * 14)
    for keyword, weight in JOB_RELEVANCE_WEIGHTS.items():
        if _contains_phrase(haystack, keyword):
            score += weight
    if any(_contains_phrase(haystack, term) for term in ["senior", "staff", "lead"]):
        score += 5
    if _contains_phrase(haystack, "remote"):
        score += 3
    if not _looks_like_relevant_role(title, description):
        score -= 18
    return min(score, 99)


def _dedupe_and_rank_jobs(items: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    identities_seen: set[str] = set()

    ranked = sorted(items, key=_job_sort_key, reverse=True)
    for item in ranked:
        url_key = item["source_url"]
        identity_key = _job_identity_key(item["company_name"], item["title"])
        if url_key in deduped or identity_key in identities_seen:
            continue
        deduped[url_key] = item
        identities_seen.add(identity_key)
        if len(deduped) >= MAX_JOB_ITEMS:
            break
    return list(deduped.values())


def _job_sort_key(item: dict) -> tuple[int, datetime]:
    return item["relevance_score"], item["published_at"]


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
