from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models import NewsItem
from app.seed.data import NEWS_ITEMS

RSS_NAMESPACES = {"atom": "http://www.w3.org/2005/Atom"}
NEWS_FEEDS = [
    {"source_name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml", "category": "open-source"},
    {"source_name": "OpenAI", "url": "https://openai.com/news/rss.xml", "category": "model-release"},
    {"source_name": "Anthropic", "url": "https://www.anthropic.com/news/rss.xml", "category": "agents"},
]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


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
    return list(db.scalars(query.order_by(desc(NewsItem.published_at), desc(NewsItem.signal_score))).all())


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


def ensure_seed_news(db: Session) -> None:
    if db.scalar(select(NewsItem.id).limit(1)):
        return
    now = datetime.utcnow()
    for offset, payload in enumerate(NEWS_ITEMS):
        db.add(
            NewsItem(
                published_at=now,
                **payload,
            )
        )
    db.flush()


def refresh_news(db: Session) -> list[NewsItem]:
    fetched = _fetch_remote_news()
    if not fetched:
        return list_news(db)

    existing = {item.source_url: item for item in db.scalars(select(NewsItem)).all()}
    for payload in fetched:
        item = existing.get(payload["source_url"])
        if not item:
            item = NewsItem(source_url=payload["source_url"], slug=payload["slug"])
            db.add(item)
        item.source_name = payload["source_name"]
        item.title = payload["title"]
        item.slug = payload["slug"]
        item.summary = payload["summary"]
        item.category = payload["category"]
        item.published_at = payload["published_at"]
        item.signal_score = payload["signal_score"]
        item.tags_json = payload["tags_json"]
    db.commit()
    return list_news(db)


def _fetch_remote_news() -> list[dict]:
    items: list[dict] = []
    with httpx.Client(timeout=10.0, follow_redirects=True, headers={"User-Agent": "AIEngineerPortal/1.0"}) as client:
        for feed in NEWS_FEEDS:
            try:
                response = client.get(feed["url"])
                response.raise_for_status()
            except Exception:
                continue
            items.extend(_parse_feed(feed["source_name"], feed["category"], response.text))
    items.sort(key=lambda item: item["published_at"], reverse=True)
    return items[:18]


def _parse_feed(source_name: str, category: str, xml_text: str) -> list[dict]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    parsed: list[dict] = []

    for entry in root.findall(".//item"):
        title = (entry.findtext("title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        description = entry.findtext("description") or entry.findtext("content:encoded") or ""
        published = entry.findtext("pubDate") or entry.findtext("published") or entry.findtext("updated")
        if not title or not link:
            continue
        parsed.append(
            {
                "source_name": source_name,
                "title": title,
                "slug": _slugify(f"{source_name}-{title}"),
                "summary": _strip_html(description)[:280],
                "source_url": link,
                "category": category,
                "published_at": _parse_datetime(published),
                "signal_score": _score_news_signal(title, description, category),
                "tags_json": [category, source_name.lower().replace(" ", "-")],
            }
        )

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
        if not title or not link:
            continue
        parsed.append(
            {
                "source_name": source_name,
                "title": title,
                "slug": _slugify(f"{source_name}-{title}"),
                "summary": _strip_html(summary)[:280],
                "source_url": link,
                "category": category,
                "published_at": _parse_datetime(published),
                "signal_score": _score_news_signal(title, summary, category),
                "tags_json": [category, source_name.lower().replace(" ", "-")],
            }
        )

    return parsed


def _score_news_signal(title: str, summary: str, category: str) -> int:
    haystack = f"{title} {summary}".lower()
    score = 55
    for keyword in ["release", "launch", "agent", "evaluation", "rag", "retrieval", "api", "benchmark", "open-source"]:
        if keyword in haystack:
            score += 6
    if category in {"model-release", "agents", "evaluation"}:
        score += 8
    return min(score, 99)
