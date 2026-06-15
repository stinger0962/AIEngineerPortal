"""Shared yt-dlp helpers: residential proxy + per-attempt exit-IP rotation +
bot-check-dodging player clients.

YouTube blocks ~half of residential exit IPs at any moment and throws
"Sign in to confirm you're not a bot" at its `web` player client. Webshare hands
out a sticky exit IP per TCP session, so a single yt-dlp call is a coin flip. We
retry with a FRESH ``YoutubeDL`` (=> fresh session => fresh exit IP) per attempt,
and prefer the ``tv``/``ios`` player clients which don't trip the web bot-check
(``web`` kept only as a last-resort fallback). See
``docs/youtube-ip-bypass-playbook.md``.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

_MAX_ATTEMPTS = 5
_RETRY_SLEEP_S = 0.8

# Substrings meaning "this exit IP is blocked / rate-limited" — a fresh IP may
# succeed, so retry. Genuine content errors (private / unavailable / age /
# members-only) lack these markers and therefore fail fast.
_RETRYABLE_MARKERS = (
    "sign in to confirm",
    "not a bot",
    "confirm you're not",
    "http error 429",
    "too many requests",
    "http error 403",
    "forbidden",
    "blocked",
    "rate limit",
    "temporarily",
    "timed out",
    "timeout",
    "unable to download webpage",
)


def proxy_url() -> Optional[str]:
    user = os.getenv("WEBSHARE_PROXY_USERNAME", "")
    pw = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
    return f"http://{user}:{pw}@p.webshare.io:80" if user and pw else None


def build_opts(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Base yt-dlp opts: quiet + residential proxy (when configured) +
    bot-check-dodging player clients. ``extra`` (format / outtmpl /
    postprocessors …) is merged on top."""
    opts: Dict[str, Any] = {"quiet": True, "no_warnings": True, "noplaylist": True}
    proxy = proxy_url()
    if proxy:
        opts["proxy"] = proxy
    # Prefer mobile clients: they dodge the web "sign in to confirm you're not a
    # bot" check AND return clean (non-DRM) downloadable streams. NOT `tv` — it
    # avoids the bot-check but serves DRM-encrypted streams for some videos.
    # `web` kept only as a last-resort fallback.
    opts["extractor_args"] = {"youtube": {"player_client": ["ios", "android", "web"]}}
    if extra:
        opts.update(extra)
    return opts


def _retryable(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(m in s for m in _RETRYABLE_MARKERS)


def extract_info(
    youtube_url: str,
    *,
    download: bool,
    extra_opts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run yt-dlp ``extract_info`` with a fresh session (=> fresh Webshare exit
    IP) per attempt, retrying past bot-detected / rate-limited exit IPs. Returns
    the info dict; re-raises the last yt-dlp exception once attempts are exhausted.
    """
    import yt_dlp

    last: Optional[Exception] = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            with yt_dlp.YoutubeDL(build_opts(extra_opts)) as ydl:
                return ydl.extract_info(youtube_url, download=download)
        except Exception as exc:  # classify by message; rotate IP and retry if transient
            last = exc
            if _retryable(exc) and attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_RETRY_SLEEP_S)
                continue
            raise
    assert last is not None  # pragma: no cover
    raise last
