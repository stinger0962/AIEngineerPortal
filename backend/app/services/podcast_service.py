"""Podcast generation service: transcript extraction, Claude digest, MiniMax TTS."""
from __future__ import annotations

import io
import json as _json
import os
import random
import re
import time
import urllib.parse as _urllib_parse
import urllib.request as _urllib_request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from youtube_transcript_api._errors import (
    AgeRestricted,
    InvalidVideoId,
    VideoUnavailable,
    VideoUnplayable,
)
from pydub import AudioSegment

# How many times to retry transcript extraction. Webshare's residential proxy
# gives a STICKY exit IP per session, so the library's internal retries all hit
# the same (possibly YouTube-blocked) IP. Building a fresh YouTubeTranscriptApi
# per attempt forces a new session -> new exit IP, which is what actually
# rotates past a blocked IP. ~50%+ of IPs work, so 6 attempts -> >98% success.
_TRANSCRIPT_MAX_ATTEMPTS = 6

# Genuine content problems — retrying with a different IP will never help, so we
# surface them immediately instead of burning all attempts.
_NON_RETRYABLE_TRANSCRIPT_ERRORS = (
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    InvalidVideoId,
    AgeRestricted,
)

AUDIO_DIR = Path(os.getenv("PODCAST_AUDIO_DIR", "/data/podcast_audio"))


def _ensure_audio_dir() -> Path:
    """Create AUDIO_DIR on first use — avoids mkdir at import time in test envs."""
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIO_DIR

YOUTUBE_REGEX = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
)


def validate_youtube_url(url: str) -> bool:
    """Return True if url looks like a valid YouTube video URL."""
    return bool(YOUTUBE_REGEX.search(url))


# MiniMax Chinese (Mandarin) system voices, curated into two pools.
# NARRATION_CATALOG drives the single-narration dropdown (and its 随机 option).
# DIALOGUE_CATALOG drives dialogue casting: host A = a random female, host B = a
# random male, chosen once per episode. Both are the single source of truth.

NARRATION_CATALOG: List[Dict[str, str]] = [
    # Female
    {"voice_id": "Chinese (Mandarin)_News_Anchor", "name": "新闻女主播 News Anchor", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_Wise_Women", "name": "智慧女声 Wise Woman", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_ExplorativeGirl", "name": "好奇女孩 Explorative Girl", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_HK_Flight_Attendant", "name": "港风空姐 HK Flight Attendant", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_Gentle_Senior", "name": "温和长辈(女) Gentle Senior", "gender": "female"},
    # Male
    {"voice_id": "Chinese (Mandarin)_Radio_Host", "name": "电台主持 Radio Host", "gender": "male"},
    {"voice_id": "Chinese (Mandarin)_Male_Announcer", "name": "播音男声 Male Announcer", "gender": "male"},
    {"voice_id": "Chinese (Mandarin)_Gentle_Youth", "name": "温柔青年 Gentle Youth", "gender": "male"},
]

DIALOGUE_CATALOG: List[Dict[str, str]] = [
    # Female (host A pool)
    {"voice_id": "Chinese (Mandarin)_Warm_Girl", "name": "温柔女孩 Warm Girl", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_Sweet_Lady", "name": "甜美女声 Sweet Lady", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_Crisp_Girl", "name": "清脆女孩 Crisp Girl", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_Soft_Girl", "name": "软糯女声 Soft Girl", "gender": "female"},
    {"voice_id": "Chinese (Mandarin)_Warm_Bestie", "name": "暖心闺蜜 Warm Bestie", "gender": "female"},
    # Male (host B pool)
    {"voice_id": "Chinese (Mandarin)_Humorous_Elder", "name": "幽默长者(男) Humorous Elder", "gender": "male"},
    {"voice_id": "Chinese (Mandarin)_Straightforward_Boy", "name": "直率男孩 Straightforward Boy", "gender": "male"},
    {"voice_id": "Chinese (Mandarin)_Pure-hearted_Boy", "name": "纯真男孩 Pure-hearted Boy", "gender": "male"},
    {"voice_id": "Chinese (Mandarin)_Southern_Young_Man", "name": "南方青年 Southern Young Man", "gender": "male"},
]

_NARRATION_VOICE_IDS = {v["voice_id"] for v in NARRATION_CATALOG}


def pick_random_narration() -> str:
    """Return a random voice_id from the narration pool (any gender)."""
    return random.choice([v["voice_id"] for v in NARRATION_CATALOG])


def pick_dialogue_voice(gender: str) -> str:
    """Return a random dialogue voice_id of the given gender (female=host A, male=host B)."""
    return random.choice([v["voice_id"] for v in DIALOGUE_CATALOG if v["gender"] == gender])


def resolve_voice(requested: Optional[str]) -> str:
    """
    Resolve a single-narration voice request:
    - None / "" / "random" -> a random voice from the narration pool
    - a known narration voice_id -> that voice
    - an unknown voice_id -> fall back to random (avoids invalid-voice API errors)
    """
    if not requested or requested == "random":
        return pick_random_narration()
    if requested in _NARRATION_VOICE_IDS:
        return requested
    return pick_random_narration()


def _build_transcript_api() -> YouTubeTranscriptApi:
    """
    Build a fresh YouTubeTranscriptApi. When Webshare credentials are present,
    route through Webshare residential proxies. Each fresh instance gets a new
    requests.Session and therefore a new sticky exit IP (Webshare rotates per
    session, not per request), which is how we rotate past a blocked IP.

    retries_when_blocked is kept low (2) because all internal retries reuse the
    same session IP — they rarely help. The outer retry loop in
    extract_transcript provides the real IP rotation.
    """
    proxy_username = os.getenv("WEBSHARE_PROXY_USERNAME", "")
    proxy_password = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
    if proxy_username and proxy_password:
        from youtube_transcript_api.proxies import WebshareProxyConfig
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=proxy_username,
                proxy_password=proxy_password,
                retries_when_blocked=2,
            )
        )
    return YouTubeTranscriptApi()


def _fetch_transcript_text(api: YouTubeTranscriptApi, video_id: str) -> str:
    """
    Fetch and flatten the transcript text for a video using the given api.
    Prefers manual English, then auto-generated English, then any language.
    May raise transcript-api errors (blocked IP, disabled, etc.).
    """
    transcript_list = api.list(video_id)

    try:
        transcript = transcript_list.find_manually_created_transcript(["en", "en-US", "en-GB"])
    except NoTranscriptFound:
        try:
            transcript = transcript_list.find_generated_transcript(["en", "en-US", "en-GB"])
        except NoTranscriptFound:
            # Take whatever is available (first in list)
            transcript = next(iter(transcript_list))

    snippets = transcript.fetch()
    text = " ".join(s.text for s in snippets)
    # Clean up newlines within snippet text
    return re.sub(r"\s+", " ", text).strip()


def extract_transcript(youtube_url: str) -> Tuple[str, str]:
    """
    Fetch transcript using youtube-transcript-api, routed through Webshare
    residential proxies when configured.

    YouTube blocks many proxy exit IPs with a 429/CAPTCHA. Because Webshare
    gives a sticky IP per session, we retry with a FRESH api instance (new
    session -> new exit IP) up to _TRANSCRIPT_MAX_ATTEMPTS times. Genuine
    content errors (disabled captions, unavailable video) are surfaced
    immediately rather than retried.

    Returns (video_title, transcript_text). Raises ValueError on failure.
    """
    match = YOUTUBE_REGEX.search(youtube_url)
    if not match:
        raise ValueError("Invalid YouTube URL")
    video_id = match.group(1)

    last_exc: Optional[Exception] = None
    for attempt in range(1, _TRANSCRIPT_MAX_ATTEMPTS + 1):
        try:
            api = _build_transcript_api()  # fresh session -> fresh exit IP
            text = _fetch_transcript_text(api, video_id)
            # Fetch real title from oEmbed; falls back to "" on any failure
            video_title = fetch_video_title(youtube_url)
            return video_title, text

        except TranscriptsDisabled:
            raise ValueError(
                "Transcripts are disabled for this video. "
                "Try a video with captions enabled."
            )
        except _NON_RETRYABLE_TRANSCRIPT_ERRORS as exc:
            raise ValueError(f"Could not fetch transcript: {exc}") from exc
        except Exception as exc:
            # Transient: blocked IP / 429 / network. Retry with a new exit IP.
            last_exc = exc
            if attempt < _TRANSCRIPT_MAX_ATTEMPTS:
                time.sleep(1)

    raise ValueError(
        f"Could not fetch transcript after {_TRANSCRIPT_MAX_ATTEMPTS} attempts — "
        f"YouTube is rate-limiting the proxy IPs right now. Please try again in a moment."
    )


def fetch_video_title(youtube_url: str) -> str:
    """Fetch video title from YouTube oEmbed API. Returns empty string on any failure."""
    try:
        encoded = _urllib_parse.quote(youtube_url, safe="")
        oembed_url = f"https://www.youtube.com/oembed?url={encoded}&format=json"
        with _urllib_request.urlopen(oembed_url, timeout=5) as resp:
            data = _json.loads(resp.read())
            return data.get("title", "")
    except Exception:
        return ""


def get_chinese_title(
    english_title: str,
    transcript: str,
    anthropic_api_key: str,
    model: str,
) -> str:
    """
    Return a Chinese title for the episode.
    - If english_title is provided: translate it to Chinese.
    - If empty (live stream / oEmbed failed): infer a concise Chinese title from transcript.
    Returns a plain Chinese string, no quotes, no punctuation wrapping.
    """
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    if english_title:
        prompt = (
            f"将以下视频标题翻译成中文，只输出翻译结果，不要引号或任何解释：\n{english_title}"
        )
    else:
        # Truncate transcript to first 1000 chars to keep tokens low
        snippet = transcript[:1000]
        prompt = (
            "根据以下视频讲稿片段，为这个视频起一个简洁的中文标题（10字以内），"
            "只输出标题本身，不要引号或任何解释：\n" + snippet
        )
    message = client.messages.create(
        model=model,
        max_tokens=60,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


_DIGEST_PCT = {5: 30, 10: 60}

_SINGLE_PROMPT = """你是一位专业的中文播客主持人。请将以下英文视频讲稿整理为一期播客脚本。

要求：
1. 长度约为原文的{pct}%，提炼最核心的观点（目标时长：{target_mins}分钟）
2. 语气自然口语化，像在和听众轻松对话
3. 开头一句话引入主题，结尾一句话总结收尾
4. 保留最重要的例子、数据和结论
5. 直接输出播客脚本，不要任何说明或前言

讲稿内容：
{transcript}"""

_DIALOGUE_PROMPT = """你是两位中文播客主持人（主持人A：女声，主持人B：男声）。
请将以下英文视频讲稿改编为一段自然的双人对话播客脚本。

要求：
1. 长度约为原文的{pct}%，提炼最核心的观点（目标时长：{target_mins}分钟）
2. 对话要自然、有来有往，A和B轮流发言，每次发言2-4句话
3. A负责引入话题和总结，B负责追问、补充例子和表达观点
4. 语气轻松口语化，像朋友间的专业讨论
5. 严格按以下格式输出，每行一句发言，不要其他内容：

主持人A: [发言内容]
主持人B: [发言内容]
主持人A: [发言内容]
...

讲稿内容：
{transcript}"""


def _build_prompt(transcript: str, digest_length_mins: int, fmt: str) -> str:
    """Build the Claude prompt for the given format and length."""
    pct = _DIGEST_PCT.get(digest_length_mins, 30)  # unknown lengths default to 30% (5 min)
    template = _SINGLE_PROMPT if fmt == "single" else _DIALOGUE_PROMPT
    return template.format(pct=pct, target_mins=digest_length_mins, transcript=transcript)


def generate_script(
    transcript: str,
    digest_length_mins: int,
    fmt: str,
    anthropic_api_key: str,
    model: str = "claude-sonnet-4-6",
) -> str:
    """
    Call Claude to produce a Chinese podcast script.
    Returns the raw script text (plain for single, 主持人A/B: lines for dialogue).
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = _build_prompt(transcript, digest_length_mins, fmt)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def _parse_dialogue(script: str) -> List[Tuple[str, str]]:
    """
    Parse a dialogue script into (speaker, text) pairs.
    Expects lines like '主持人A: ...' or '主持人B: ...'
    Skips blank lines and any line not matching the pattern.
    """
    pairs: List[Tuple[str, str]] = []
    for line in script.splitlines():
        line = line.strip()
        if line.startswith("主持人A:"):
            pairs.append(("A", line[len("主持人A:"):].strip()))
        elif line.startswith("主持人B:"):
            pairs.append(("B", line[len("主持人B:"):].strip()))
    return pairs


def _tts_bytes(
    text: str,
    voice_id: str,
    api_key: str,
    group_id: str,
    model: str = "speech-2.6-hd",
    api_base: str = "https://api.minimax.io",
    speed: float = 1.0,
) -> bytes:
    """
    Call MiniMax (海螺) T2A v2 API and return raw MP3 bytes.

    MiniMax is purpose-built for Mandarin (far better than ElevenLabs on Chinese).
    The API returns hex-encoded audio in data.audio; we decode it to raw MP3 bytes.
    Raises ValueError on a non-zero MiniMax status code.
    """
    import httpx

    url = f"{api_base}/v1/t2a_v2?GroupId={group_id}"
    resp = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": speed,
                "vol": 1.0,
                "pitch": 0,
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
            },
        },
        timeout=120.0,
    )
    resp.raise_for_status()
    payload = resp.json()

    base = payload.get("base_resp") or {}
    if base.get("status_code", 0) != 0:
        raise ValueError(
            f"MiniMax TTS error {base.get('status_code')}: {base.get('status_msg')}"
        )

    audio_hex = (payload.get("data") or {}).get("audio")
    if not audio_hex:
        raise ValueError("MiniMax TTS returned no audio data")
    return bytes.fromhex(audio_hex)


def generate_audio_single(
    script: str,
    episode_id: int,
    voice_id_a: str,
    api_key: str,
    group_id: str,
    model: str = "speech-2.6-hd",
    api_base: str = "https://api.minimax.io",
) -> Tuple[Path, int]:
    """
    Generate a single-narrator MP3 from the full script.
    Returns (audio_path, duration_secs).
    """
    mp3_bytes = _tts_bytes(script, voice_id_a, api_key, group_id, model, api_base)
    audio_path = _ensure_audio_dir() / f"{episode_id}.mp3"
    audio_path.write_bytes(mp3_bytes)
    segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    duration_secs = int(len(segment) / 1000)
    return audio_path, duration_secs


def generate_audio_dialogue(
    script: str,
    episode_id: int,
    voice_id_a: str,
    voice_id_b: str,
    api_key: str,
    group_id: str,
    model: str = "speech-2.6-hd",
    api_base: str = "https://api.minimax.io",
) -> Tuple[Path, int]:
    """
    Generate a two-person dialogue MP3 by calling MiniMax once per line
    and stitching with 300ms silence between turns.
    Returns (audio_path, duration_secs).
    """
    lines = _parse_dialogue(script)
    if not lines:
        raise ValueError("Dialogue script contains no parseable speaker lines.")

    silence = AudioSegment.silent(duration=300)  # 300ms between turns
    combined = AudioSegment.empty()

    for speaker, text in lines:
        voice_id = voice_id_a if speaker == "A" else voice_id_b
        mp3_bytes = _tts_bytes(text, voice_id, api_key, group_id, model, api_base)
        segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        if len(combined) > 0:
            combined += silence
        combined += segment

    audio_path = _ensure_audio_dir() / f"{episode_id}.mp3"
    combined.export(str(audio_path), format="mp3")
    duration_secs = int(len(combined) / 1000)
    return audio_path, duration_secs
