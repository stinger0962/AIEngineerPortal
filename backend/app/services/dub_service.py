"""配 Dub: foreign YouTube video -> Chinese voice-over dubbed mp4."""
from __future__ import annotations

import io
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydub import AudioSegment

DUB_DIR = Path(os.getenv("DUB_VIDEO_DIR", "/data/dub_videos"))
MAX_DURATION_S = 600
_MAX_SPEED = 1.25
_DUCK_DB = -18


def _ensure_dir() -> Path:
    DUB_DIR.mkdir(parents=True, exist_ok=True)
    return DUB_DIR


def _proxy_url() -> Optional[str]:
    u = os.getenv("WEBSHARE_PROXY_USERNAME", "")
    p = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
    return f"http://{u}:{p}@p.webshare.io:80" if u and p else None


def probe_duration(youtube_url: str) -> int:
    """Return duration seconds without downloading. Raises ValueError if unavailable or > 10 min."""
    import yt_dlp

    opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
    proxy = _proxy_url()
    if proxy:
        opts["proxy"] = proxy
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
        dur = int(info.get("duration") or 0)
    except Exception as exc:
        raise ValueError(f"无法读取该视频信息：{exc}") from exc
    if dur <= 0:
        raise ValueError("无法读取视频时长。")
    if dur > MAX_DURATION_S:
        raise ValueError("视频超过 10 分钟上限，请换更短的视频。")
    return dur


def download_video(youtube_url: str, out_dir: str) -> Tuple[str, str]:
    """yt-dlp merged mp4 (<=720p) via Webshare proxy. Returns (title, video_path)."""
    import yt_dlp

    opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(Path(out_dir) / "dub.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    proxy = _proxy_url()
    if proxy:
        opts["proxy"] = proxy
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
        title = (info.get("title") or "视频").strip()
    except Exception as exc:
        raise ValueError(f"无法下载该视频：{exc}") from exc

    mp4 = Path(out_dir) / "dub.mp4"
    if mp4.exists():
        return title, str(mp4)
    vids = [c for c in Path(out_dir).glob("dub.*") if c.suffix in (".mp4", ".mkv", ".webm")]
    if not vids:
        raise ValueError("视频下载失败。")
    return title, str(vids[0])


def _extract_audio(video_path: str, out_path: str, sample_rate: int, channels: int) -> str:
    """ffmpeg audio extraction helper."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ar", str(sample_rate), "-ac", str(channels), out_path],
        check=True, capture_output=True,
    )
    return out_path


def extract_segments(video_path: str, openai_api_key: str) -> List[Dict]:
    """16kHz mono mp3 -> Whisper verbose_json -> [{start, end, text}]. (<=10min => single call.)"""
    from openai import OpenAI

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = _extract_audio(video_path, str(Path(tmp) / "asr.mp3"), 16000, 1)
        client = OpenAI(api_key=openai_api_key)
        with open(mp3, "rb") as fh:
            resp = client.audio.transcriptions.create(
                model="whisper-1", file=fh, response_format="verbose_json"
            )

    segs: List[Dict] = []
    for s in (resp.segments or []):
        start = s.get("start") if isinstance(s, dict) else getattr(s, "start", None)
        end = s.get("end") if isinstance(s, dict) else getattr(s, "end", None)
        text = s.get("text") if isinstance(s, dict) else getattr(s, "text", None)
        if text and text.strip():
            segs.append({"start": float(start or 0), "end": float(end or 0), "text": text.strip()})
    if not segs:
        raise ValueError("未检测到可转写的语音。")
    return segs
