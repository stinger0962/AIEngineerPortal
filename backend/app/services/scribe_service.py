"""录 Scribe: download YouTube audio (via residential proxy) + OpenAI Whisper transcription."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

_WHISPER_MODEL = "whisper-1"
_CHUNK_MS = 10 * 60 * 1000  # 10-min chunks — 16kHz mono mp3 stays well under OpenAI's 25MB/request


def _proxy_url() -> Optional[str]:
    user = os.getenv("WEBSHARE_PROXY_USERNAME", "")
    pw = os.getenv("WEBSHARE_PROXY_PASSWORD", "")
    return f"http://{user}:{pw}@p.webshare.io:80" if user and pw else None


def download_audio(youtube_url: str, out_dir: str) -> Tuple[str, str]:
    """yt-dlp bestaudio -> 16kHz mono mp3 at out_dir/scribe.mp3 (via Webshare proxy
    when configured). Returns (title, audio_path). Raises ValueError on failure."""
    import yt_dlp

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(out_dir) / "scribe.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
        "postprocessor_args": ["-ar", "16000", "-ac", "1"],
    }
    proxy = _proxy_url()
    if proxy:
        opts["proxy"] = proxy

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
        title = (info.get("title") or "YouTube 视频").strip()
    except Exception as exc:
        raise ValueError(f"无法下载该视频的音频：{exc}") from exc

    mp3 = Path(out_dir) / "scribe.mp3"
    if not mp3.exists():
        raise ValueError("音频下载失败。")
    return title, str(mp3)


def _split_audio(audio_path: str) -> List[str]:
    """Split an audio file into <= _CHUNK_MS mp3 chunks; return the chunk paths."""
    from pydub import AudioSegment

    audio = AudioSegment.from_file(audio_path)
    spans = list(range(0, len(audio), _CHUNK_MS)) or [0]
    paths: List[str] = []
    for idx, start in enumerate(spans):
        chunk = audio[start:start + _CHUNK_MS]
        path = f"{audio_path}.part{idx}.mp3"
        chunk.export(path, format="mp3")
        paths.append(path)
    return paths


def transcribe_audio(audio_path: str, openai_api_key: str) -> str:
    """Chunk + transcribe with OpenAI Whisper; return the concatenated text.
    Raises ValueError on API failure or empty result."""
    from openai import OpenAI

    client = OpenAI(api_key=openai_api_key)
    parts: List[str] = []
    for chunk_path in _split_audio(audio_path):
        try:
            with open(chunk_path, "rb") as fh:
                resp = client.audio.transcriptions.create(model=_WHISPER_MODEL, file=fh)
            parts.append((resp.text or "").strip())
        except Exception as exc:
            raise ValueError(f"转写失败：{exc}") from exc
        finally:
            try:
                os.remove(chunk_path)
            except OSError:
                pass

    text = " ".join(p for p in parts if p).strip()
    if not text:
        raise ValueError("转写结果为空。")
    return text


def scribe_youtube(youtube_url: str, openai_api_key: str) -> Tuple[str, str]:
    """Orchestrate download + transcribe in a temp dir. Returns (title, transcript)."""
    with tempfile.TemporaryDirectory() as tmp:
        title, audio_path = download_audio(youtube_url, tmp)
        transcript = transcribe_audio(audio_path, openai_api_key)
    return title, transcript
