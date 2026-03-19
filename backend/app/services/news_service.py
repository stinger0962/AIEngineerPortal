from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlparse, urlunparse
from xml.etree import ElementTree

import httpx
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models import NewsItem
from app.seed.data import NEWS_ITEMS

RSS_NAMESPACES = {"atom": "http://www.w3.org/2005/Atom"}
NEWS_AUTO_REFRESH_HOURS = 6
MAX_NEWS_ITEMS = 18
MAX_ITEMS_PER_SOURCE = 4

NEWS_FEEDS = [
    {"source_name": "OpenAI", "url": "https://openai.com/news/rss.xml", "category": "model-release", "priority": 1.0},
    {"source_name": "Anthropic", "url": "https://www.anthropic.com/news/rss.xml", "category": "agents", "priority": 0.95},
    {"source_name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "category": "open-source", "priority": 0.9},
    {"source_name": "LangChain", "url": "https://blog.langchain.com/rss/", "category": "agents", "priority": 0.82},
    {"source_name": "Pinecone", "url": "https://www.pinecone.io/blog/rss/", "category": "retrieval", "priority": 0.75},
]

TRACKED_TOPICS = {
    "rag": 10,
    "retrieval": 10,
    "agent": 10,
    "agents": 10,
    "evaluation": 10,
    "eval": 8,
    "benchmark": 8,
    "tool": 7,
    "tools": 7,
    "api": 6,
    "reasoning": 6,
    "inference": 6,
    "open-source": 6,
    "deployment": 6,
    "observability": 8,
    "latency": 5,
    "pricing": 4,
    "release": 6,
    "launch": 5,
}

CATEGORY_KEYWORDS = {
    "model-release": ["model", "release", "api", "pricing", "reasoning"],
    "agents": ["agent", "tool", "workflow", "orchestration"],
    "retrieval": ["retrieval", "rag", "embedding", "search", "vector"],
    "open-source": ["open-source", "oss", "model", "serving", "framework"],
}

NEWS_GUIDANCE = {
    "model-release": {
        "focus_area": "stack decisions",
        "path_slug": "llm-app-foundations",
        "path_title": "LLM App Foundations",
        "exercise_category": "api-async",
    },
    "agents": {
        "focus_area": "workflow orchestration",
        "path_slug": "ai-agents-and-tools",
        "path_title": "AI Agents and Tools",
        "exercise_category": "prompt-formatting",
    },
    "retrieval": {
        "focus_area": "retrieval quality",
        "path_slug": "rag-systems",
        "path_title": "RAG Systems",
        "exercise_category": "retrieval",
    },
    "evaluation": {
        "focus_area": "measurement discipline",
        "path_slug": "evaluation-and-observability",
        "path_title": "Evaluation and Observability",
        "exercise_category": "evaluation",
    },
    "open-source": {
        "focus_area": "tooling choices",
        "path_slug": "ai-deployment-and-mlops",
        "path_title": "AI Deployment and MLOps",
        "exercise_category": "python-refresh",
    },
}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_url(value: str) -> str:
    parsed = urlparse(value.strip())
    filtered_query = [
        (key, item)
        for key, item in parse_qsl(parsed.query, keep_blank_values=False)
        if not key.lower().startswith("utm_")
    ]
    normalized_path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), normalized_path, "", "&".join(f"{k}={v}" for k, v in filtered_query), ""))


def _title_key(source_name: str, title: str) -> str:
    return _slugify(f"{source_name}-{title}")[:160]


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        parsed = parsedate_to_datetime(value)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
    except (TypeError, ValueError, IndexError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def list_news(
    db: Session,
    category: str | None = None,
    search: str | None = None,
    saved_only: bool = False,
) -> list[NewsItem]:
    query = select(NewsItem)
    if category:
        query = query.where(NewsItem.category == category)
    if search:
        query = query.where(or_(NewsItem.title.ilike(f"%{search}%"), NewsItem.summary.ilike(f"%{search}%")))
    if saved_only:
        query = query.where(NewsItem.is_saved.is_(True))
    return list(db.scalars(query.order_by(desc(NewsItem.signal_score), desc(NewsItem.published_at))).all())


def get_news_refresh_meta(db: Session) -> dict:
    items = list_news(db)
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
        "is_stale": _is_refresh_stale(latest_sync, NEWS_AUTO_REFRESH_HOURS),
        "refresh_window_hours": NEWS_AUTO_REFRESH_HOURS,
        "auto_refresh_enabled": True,
    }


def get_news_item(db: Session, news_id: int) -> NewsItem | None:
    return db.scalar(select(NewsItem).where(NewsItem.id == news_id))


def set_news_saved(db: Session, news_id: int, saved: bool = True) -> NewsItem | None:
    item = get_news_item(db, news_id)
    if not item:
        return None
    item.is_saved = saved
    db.commit()
    db.refresh(item)
    return item


def serialize_news_item(item: NewsItem) -> dict:
    guidance = NEWS_GUIDANCE.get(item.category, {})
    return {
        "id": item.id,
        "source_name": item.source_name,
        "title": item.title,
        "slug": item.slug,
        "summary": item.summary,
        "source_url": item.source_url,
        "category": item.category,
        "published_at": item.published_at,
        "signal_score": item.signal_score,
        "tags_json": item.tags_json,
        "is_saved": item.is_saved,
        "is_seeded": item.is_seeded,
        "last_synced_at": item.last_synced_at,
        "why_it_matters": build_news_why_it_matters(item),
        "suggested_action": build_news_suggested_action(item),
        "focus_area": guidance.get("focus_area", "external signal translation"),
        "recommended_path_slug": guidance.get("path_slug"),
        "recommended_path_title": guidance.get("path_title"),
        "recommended_exercise_category": guidance.get("exercise_category"),
    }


def ensure_seed_news(db: Session) -> None:
    if db.scalar(select(NewsItem.id).limit(1)):
        return
    now = datetime.utcnow()
    for payload in NEWS_ITEMS:
        db.add(
            NewsItem(
                published_at=now,
                is_seeded=True,
                last_synced_at=now,
                **payload,
            )
        )
    db.flush()


def refresh_news(db: Session) -> list[NewsItem]:
    fetched = _fetch_remote_news()
    if not fetched:
        return list_news(db)

    sync_time = datetime.utcnow()
    existing_by_url = {_normalize_url(item.source_url): item for item in db.scalars(select(NewsItem)).all()}
    existing_by_title = {_title_key(item.source_name, item.title): item for item in db.scalars(select(NewsItem)).all()}

    touched_ids: set[int] = set()
    for payload in fetched:
        normalized_url = _normalize_url(payload["source_url"])
        item = existing_by_url.get(normalized_url) or existing_by_title.get(_title_key(payload["source_name"], payload["title"]))
        if not item:
            item = NewsItem(source_url=payload["source_url"], slug=payload["slug"])
            db.add(item)
        item.source_name = payload["source_name"]
        item.title = payload["title"]
        item.slug = payload["slug"]
        item.summary = payload["summary"]
        item.source_url = normalized_url
        item.category = payload["category"]
        item.published_at = payload["published_at"]
        item.signal_score = payload["signal_score"]
        item.tags_json = payload["tags_json"]
        item.is_seeded = False
        item.last_synced_at = sync_time
        if item.id:
            touched_ids.add(item.id)

    db.flush()

    live_count = len(fetched)
    if live_count >= 6:
        for seeded_item in db.scalars(select(NewsItem).where(NewsItem.is_seeded.is_(True))).all():
            db.delete(seeded_item)

    db.commit()
    return list_news(db)


def refresh_news_if_stale(db: Session) -> list[NewsItem]:
    current_items = list_news(db)
    latest_sync = max((item.last_synced_at for item in current_items), default=None)
    if latest_sync and not _is_refresh_stale(latest_sync, NEWS_AUTO_REFRESH_HOURS):
        return current_items
    return refresh_news(db)


def _fetch_remote_news() -> list[dict]:
    items: list[dict] = []
    with httpx.Client(timeout=10.0, follow_redirects=True, headers={"User-Agent": "AIEngineerPortal/1.0"}) as client:
        for feed in NEWS_FEEDS:
            try:
                response = client.get(feed["url"])
                response.raise_for_status()
            except Exception:
                continue
            items.extend(_parse_feed(feed, response.text))
    return _dedupe_and_rank_news(items)


def _parse_feed(feed: dict, xml_text: str) -> list[dict]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    parsed: list[dict] = []
    source_name = feed["source_name"]
    category = feed["category"]
    priority = feed["priority"]

    for entry in root.findall(".//item"):
        title = (entry.findtext("title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        description = entry.findtext("description") or entry.findtext("content:encoded") or ""
        published = entry.findtext("pubDate") or entry.findtext("published") or entry.findtext("updated")
        payload = _build_news_payload(source_name, category, priority, title, link, description, published)
        if payload:
            parsed.append(payload)

    for entry in root.findall(".//atom:entry", RSS_NAMESPACES):
        title = (entry.findtext("atom:title", default="", namespaces=RSS_NAMESPACES) or "").strip()
        link_node = entry.find("atom:link", RSS_NAMESPACES)
        link = (link_node.get("href") if link_node is not None else "") or ""
        summary = (
            entry.findtext("atom:summary", default="", namespaces=RSS_NAMESPACES)
            or entry.findtext("atom:content", default="", namespaces=RSS_NAMESPACES)
        )
        published = entry.findtext("atom:published", default="", namespaces=RSS_NAMESPACES) or entry.findtext(
            "atom:updated", default="", namespaces=RSS_NAMESPACES
        )
        payload = _build_news_payload(source_name, category, priority, title, link, summary, published)
        if payload:
            parsed.append(payload)

    return parsed


def _build_news_payload(
    source_name: str,
    category: str,
    source_priority: float,
    title: str,
    link: str,
    raw_summary: str,
    published: str | None,
) -> dict | None:
    if not title or not link:
        return None
    summary = _strip_html(raw_summary)[:320]
    published_at = _parse_datetime(published)
    signal_score = _score_news_signal(title, summary, category, source_priority, published_at)
    if signal_score < 50:
        return None
    return {
        "source_name": source_name,
        "title": title,
        "slug": _slugify(f"{source_name}-{title}"),
        "summary": summary,
        "source_url": _normalize_url(link),
        "category": _classify_news_category(title, summary, category),
        "published_at": published_at,
        "signal_score": signal_score,
        "tags_json": _build_news_tags(title, summary, category, source_name),
    }


def _classify_news_category(title: str, summary: str, default_category: str) -> str:
    haystack = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return category
    return default_category


def _build_news_tags(title: str, summary: str, category: str, source_name: str) -> list[str]:
    haystack = f"{title} {summary}".lower()
    tags = {category, source_name.lower().replace(" ", "-")}
    for topic in TRACKED_TOPICS:
        if topic in haystack:
            tags.add(topic.replace(" ", "-"))
    return sorted(tags)[:8]


def _score_news_signal(
    title: str,
    summary: str,
    category: str,
    source_priority: float,
    published_at: datetime,
) -> int:
    haystack = f"{title} {summary}".lower()
    score = 40 + int(source_priority * 14)
    for keyword, weight in TRACKED_TOPICS.items():
        if keyword in haystack:
            score += weight
    if category in {"model-release", "agents", "retrieval", "evaluation"}:
        score += 8
    age_hours = max(0.0, (datetime.utcnow() - published_at).total_seconds() / 3600)
    if age_hours <= 24:
        score += 10
    elif age_hours <= 72:
        score += 6
    elif age_hours <= 168:
        score += 2
    else:
        score -= min(12, int(age_hours // 48))
    return max(0, min(score, 99))


def _dedupe_and_rank_news(items: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    title_seen: set[str] = set()
    per_source_counts: dict[str, int] = {}

    ranked = sorted(items, key=_news_sort_key, reverse=True)
    for item in ranked:
        url_key = item["source_url"]
        title_key = _title_key(item["source_name"], item["title"])
        source_name = item["source_name"]
        if url_key in deduped or title_key in title_seen:
            continue
        if per_source_counts.get(source_name, 0) >= MAX_ITEMS_PER_SOURCE:
            continue
        deduped[url_key] = item
        title_seen.add(title_key)
        per_source_counts[source_name] = per_source_counts.get(source_name, 0) + 1
        if len(deduped) >= MAX_NEWS_ITEMS:
            break
    return list(deduped.values())


def _news_sort_key(item: dict) -> tuple[int, datetime, int]:
    topic_match_count = len(item.get("tags_json", []))
    return item["signal_score"], item["published_at"], topic_match_count


def _is_refresh_stale(refreshed_at: datetime | None, refresh_window_hours: int) -> bool:
    if refreshed_at is None:
        return True
    return refreshed_at <= datetime.utcnow() - timedelta(hours=refresh_window_hours)


def build_news_why_it_matters(item: NewsItem) -> str:
    if item.category == "model-release":
        return "This can change which models, APIs, or agent capabilities are worth learning and integrating next."
    if item.category == "agents":
        return "Agent workflow patterns are directly relevant to the kinds of portfolio projects and interview stories you need."
    if item.category == "retrieval":
        return "Retrieval and evaluation changes often translate into better RAG architecture and benchmarking choices."
    if item.category == "open-source":
        return "Open-source momentum is a strong signal for what tooling employers will expect you to recognize and use."
    return "This is a useful external signal to translate into project, learning, or interview preparation decisions."


def build_news_suggested_action(item: NewsItem) -> str:
    if item.category == "model-release":
        return "Review the release, compare it to your current stack, and note one concrete experiment for the portal or a side project."
    if item.category == "agents":
        return "Map this workflow pattern to one project idea or interview explanation you can strengthen this week."
    if item.category == "retrieval":
        return "Update one retrieval or evaluation note in the portal and connect it to a RAG practice task."
    if item.category == "open-source":
        return "Decide whether this tool belongs on your project shortlist and capture the decision in a knowledge note."
    return "Turn this signal into one next action in learning, project work, or interview prep."
