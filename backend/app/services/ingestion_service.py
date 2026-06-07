"""Ingestion layer: turn a source (text / web / youtube) into clean text.

Each adapter has the signature value -> (title, text). Adding a new source
later means registering one more adapter; nothing downstream changes.
"""
from __future__ import annotations

from typing import Tuple

MIN_CONTENT_CHARS = 200


def _ingest_text(value: str) -> Tuple[str, str]:
    """Pasted text: use as-is. Title is inferred later by Claude."""
    return "", value.strip()


def _ingest_web(url: str) -> Tuple[str, str]:
    """Fetch a web article and extract its main text via trafilatura."""
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError("Could not fetch that URL.")
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text or not text.strip():
        raise ValueError("Could not extract article text from that URL.")

    title = ""
    try:
        meta = trafilatura.extract_metadata(downloaded)
        if meta and getattr(meta, "title", None):
            title = meta.title
    except Exception:
        title = ""
    return title, text.strip()


def _ingest_youtube(url: str) -> Tuple[str, str]:
    """Reuse the podcast tool's transcript extraction (proxy + retry built in)."""
    from app.services.podcast_service import extract_transcript

    return extract_transcript(url)


def ingest(source_type: str, value: str) -> Tuple[str, str]:
    """Dispatch to the right adapter and enforce a minimum content length.

    Returns (title, clean_text). Raises ValueError on failure or too-short content.
    """
    if source_type == "text":
        title, text = _ingest_text(value)
    elif source_type == "web":
        title, text = _ingest_web(value)
    elif source_type == "youtube":
        title, text = _ingest_youtube(value)
    else:
        raise ValueError(f"Unknown source type: {source_type}")

    if len(text.strip()) < MIN_CONTENT_CHARS:
        raise ValueError("Content too short to summarize (need ~200+ characters).")
    return title, text
