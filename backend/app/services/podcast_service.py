"""Podcast generation service: transcript extraction, Claude digest, ElevenLabs TTS."""
from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from pydub import AudioSegment

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


def extract_transcript(youtube_url: str) -> Tuple[str, str]:
    """
    Fetch transcript using youtube-transcript-api (no cookies, no bot detection).

    Tries English transcripts first (manual then auto-generated), falls back to
    any available language. Returns (video_title, transcript_text).
    Raises ValueError if no transcript is available.
    """
    match = YOUTUBE_REGEX.search(youtube_url)
    if not match:
        raise ValueError("Invalid YouTube URL")
    video_id = match.group(1)

    try:
        proxy_username = os.getenv("WEBSHARE_PROXY_USERNAME", "")
        proxy_password = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
        if proxy_username and proxy_password:
            from youtube_transcript_api.proxies import WebshareProxyConfig
            api = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=proxy_username,
                    proxy_password=proxy_password,
                )
            )
        else:
            api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Prefer manual English, then auto-generated English, then anything
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
        text = re.sub(r"\s+", " ", text).strip()

        # Use video_id as title placeholder — transcript API doesn't return title
        # Route will update it from the SSE payload if available
        video_title = f"YouTube video ({video_id})"

    except TranscriptsDisabled:
        raise ValueError(
            "Transcripts are disabled for this video. "
            "Try a video with captions enabled."
        )
    except Exception as exc:
        raise ValueError(f"Could not fetch transcript: {exc}") from exc

    return video_title, text


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
    model: str = "claude-sonnet-4-20250514",
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


def _tts_bytes(text: str, voice_id: str, api_key: str) -> bytes:
    """
    Call ElevenLabs TTS API and return raw MP3 bytes.
    Uses eleven_multilingual_v2 model for best Chinese quality.
    """
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    # The SDK returns a generator of bytes chunks
    return b"".join(audio)


def generate_audio_single(
    script: str,
    episode_id: int,
    voice_id_a: str,
    api_key: str,
) -> Tuple[Path, int]:
    """
    Generate a single-narrator MP3 from the full script.
    Returns (audio_path, duration_secs).
    """
    mp3_bytes = _tts_bytes(script, voice_id_a, api_key)
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
) -> Tuple[Path, int]:
    """
    Generate a two-person dialogue MP3 by calling ElevenLabs once per line
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
        mp3_bytes = _tts_bytes(text, voice_id, api_key)
        segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
        if len(combined) > 0:
            combined += silence
        combined += segment

    audio_path = _ensure_audio_dir() / f"{episode_id}.mp3"
    combined.export(str(audio_path), format="mp3")
    duration_secs = int(len(combined) / 1000)
    return audio_path, duration_secs
