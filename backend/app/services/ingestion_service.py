"""Ingestion layer: turn a source (text / web / youtube) into clean text.

Each adapter has the signature value -> (title, text). Adding a new source
later means registering one more adapter; nothing downstream changes.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

MIN_CONTENT_CHARS = 200

# WeChat (and some publishers) serve an anti-bot page to datacenter IPs. Fetching
# through the Webshare residential proxy returns the real article. WeChat
# additionally requires a MicroMessenger (WeChat in-app browser) User-Agent.
_WECHAT_HOSTS = ("mp.weixin.qq.com",)
_WECHAT_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.0"
)
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _ingest_text(value: str) -> Tuple[str, str]:
    """Pasted text: use as-is. Title is inferred later by Claude."""
    return "", value.strip()


def _webshare_proxy_url() -> Optional[str]:
    """Return the Webshare residential proxy URL if credentials are configured."""
    user = os.getenv("WEBSHARE_PROXY_USERNAME", "")
    password = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
    if user and password:
        return f"http://{user}:{password}@p.webshare.io:80"
    return None


def _fetch_via_proxy(url: str, user_agent: str) -> Optional[str]:
    """Fetch a URL through the Webshare residential proxy. Returns HTML or None."""
    proxy = _webshare_proxy_url()
    if not proxy:
        return None
    import httpx

    try:
        with httpx.Client(
            proxy=proxy,
            headers={"User-Agent": user_agent},
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            resp = client.get(url)
        if resp.status_code == 200 and resp.text:
            return resp.text
    except Exception:
        return None
    return None


def _ingest_web(url: str) -> Tuple[str, str]:
    """Fetch a web article and extract its main text via trafilatura.

    Strategy:
    - WeChat URLs: fetch via residential proxy + MicroMessenger UA (datacenter
      IPs get an anti-bot page; only a residential IP sees the article).
    - Other URLs: direct fetch first (fast, no proxy bandwidth); if that yields
      nothing usable, retry through the proxy (handles other IP-blocked sites).
    """
    import trafilatura

    is_wechat = any(host in url for host in _WECHAT_HOSTS)

    if is_wechat:
        html = _fetch_via_proxy(url, _WECHAT_UA)
    else:
        html = trafilatura.fetch_url(url)

    text = trafilatura.extract(html, include_comments=False, include_tables=False) if html else None

    # Proxy fallback for non-WeChat sites that block datacenter IPs.
    if (not text or not text.strip()) and not is_wechat:
        proxied = _fetch_via_proxy(url, _BROWSER_UA)
        if proxied:
            html = proxied
            text = trafilatura.extract(html, include_comments=False, include_tables=False)

    if not html:
        raise ValueError("Could not fetch that URL.")
    if not text or not text.strip():
        raise ValueError("Could not extract article text from that URL.")

    title = ""
    try:
        meta = trafilatura.extract_metadata(html)
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
