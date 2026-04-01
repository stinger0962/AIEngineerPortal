"""Real job search via Himalayas free API."""
import httpx
from typing import Optional


HIMALAYAS_BASE = "https://himalayas.app/jobs/api"


async def search_jobs(
    query: str = "ai engineer",
    limit: int = 20,
) -> list[dict]:
    """Search Himalayas for real job postings. Free, no auth."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                HIMALAYAS_BASE,
                params={"query": query, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()

            jobs = data.get("jobs", [])
            return [
                {
                    "title": j.get("title", ""),
                    "company_name": j.get("companyName", ""),
                    "company_logo": j.get("companyLogo", ""),
                    "location": j.get("location", "Remote"),
                    "url": j.get("applicationLink") or j.get("url", ""),
                    "description_snippet": (j.get("description", "") or "")[:300],
                    "salary_range": j.get("salaryCurrency", "") + " " + str(j.get("minSalary", "")) + "-" + str(j.get("maxSalary", "")) if j.get("minSalary") else "",
                    "posted_date": j.get("pubDate", ""),
                    "tags": j.get("tags", []),
                    "seniority": j.get("seniority", ""),
                    "source": "himalayas",
                }
                for j in jobs
            ]
    except Exception:
        return []
