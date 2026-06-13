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
MAX_UPLOAD_BYTES = 100 * 1024 * 1024   # 100 MB upload cap
DUB_RETENTION_DAYS = 7                  # auto-delete dubbed mp4s older than this
_MAX_TTS_SPEED = 1.30   # B: global MiniMax speed ceiling
_MAX_ATEMPO = 1.15      # A: per-clip residual speed-up ceiling (base handles global, so gentler than old 1.25)
_CHARS_PER_SEC = 4.8    # estimate: MiniMax zh narration ≈ 4.8 chars/sec at speed 1.0
_VOICE_FILL = 0.92      # voice occupies at most this fraction of the video, leaving breath
_DUCK_DB = -18

# C: 把 Whisper 碎片按句末标点合并成完整句再翻译/配音，避免半句（以「如果」等结尾）被单独成片。
_SENT_END = ("。", "！", "？", "…", ".", "!", "?")
_MERGE_MAX_MS = 12000   # 单个合并句的硬上限时长，防无标点长串并成巨句
_MERGE_MAX_CHARS = 180  # 单个合并句的硬上限字数


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
    """yt-dlp merged mp4 (<=480p) via Webshare proxy. Returns (title, video_path).
    Capped at 480p because the residential proxy is bandwidth-throttled and the video
    is only a backdrop for the Chinese narration — smaller download, faster dubbing."""
    import yt_dlp

    opts = {
        "format": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
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


def merge_sentences(segments: List[Dict]) -> List[Dict]:
    """C：把 Whisper 的碎片合并成完整句——累积直到文本以句末标点结束（或触及时长/字数硬上限）。
    合并单元 start=首片 start、end=末片 end、text=拼接。这样每段配音都是一个完整自然句，
    不会停在「如果」这种半句，整体也不再破碎。空输入安全退回原 segments。"""
    out: List[Dict] = []
    cur: Optional[Dict] = None
    for s in segments:
        text = (s.get("text") or "").strip()
        if not text:
            continue
        if cur is None:
            cur = {"start": float(s["start"]), "end": float(s["end"]), "text": text}
        else:
            cur["end"] = float(s["end"])
            cur["text"] = f"{cur['text']} {text}".strip()
        ends_sentence = cur["text"].rstrip().endswith(_SENT_END)
        too_big = (cur["end"] - cur["start"]) * 1000 >= _MERGE_MAX_MS or len(cur["text"]) >= _MERGE_MAX_CHARS
        if ends_sentence or too_big:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    return out or segments


_TRANSLATE_PROMPT = """把下面带编号的字幕逐条翻译成自然、口语化的中文。要求：
- 保持编号一一对应，每行输出「编号. 中文」
- 不要合并或拆分条目，不要加任何说明或前言
字幕：
{numbered}"""


def translate_segments(segments: List[Dict], anthropic_api_key: str, model: str) -> List[str]:
    """One Claude call, numbered 1:1. Returns a Chinese list the same length as segments;
    any missing line falls back to the original text so alignment never breaks."""
    import anthropic

    numbered = "\n".join(f"{i + 1}. {s['text']}" for i, s in enumerate(segments))
    client = anthropic.Anthropic(api_key=anthropic_api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": _TRANSLATE_PROMPT.format(numbered=numbered)}],
    )
    raw = msg.content[0].text

    by_idx: Dict[int, str] = {}
    for line in raw.splitlines():
        m = re.match(r"\s*(\d+)[\.、)]\s*(.+)", line)
        if m:
            by_idx[int(m.group(1))] = m.group(2).strip()

    return [by_idx.get(i + 1) or s["text"] for i, s in enumerate(segments)]


def estimate_ms(text: str) -> int:
    """按字数估算中文旁白时长（speed 1.0）。仅用于全局匀速预算，不求精确。"""
    return int(len(text.strip()) / _CHARS_PER_SEC * 1000)


def compute_base_speed(zh_texts: List[str], video_ms: int) -> float:
    """B：全局匀速——译文总估时超过视频可填时长则统一略提速（封顶 _MAX_TTS_SPEED），否则 1.0。"""
    total = sum(estimate_ms(t) for t in zh_texts)
    fillable = max(int(video_ms * _VOICE_FILL), 1)
    if total <= fillable:
        return 1.0
    return min(round(total / fillable, 3), _MAX_TTS_SPEED)


def plan_placements(segments: List[Dict], clip_durations_ms: List[int], video_ms: int) -> List[Dict]:
    """A：吃停顿对齐。每句锚定原句 start；可用窗 = 到下一句 start（含其后停顿），放不下才 atempo
    提速（封顶 _MAX_ATEMPO）；落后时 pos 被 cursor 顶高、可用窗收窄 → 内建追赶。最后一句窗到 video_ms。"""
    out: List[Dict] = []
    cursor = 0
    n = len(segments)
    for i, (seg, clip_ms) in enumerate(zip(segments, clip_durations_ms)):
        start_ms = int(seg["start"] * 1000)
        next_start = int(segments[i + 1]["start"] * 1000) if i + 1 < n else video_ms
        pos = max(start_ms, cursor)
        avail = max(next_start - pos, 1)
        ratio = 1.0
        if clip_ms > avail:
            ratio = min(clip_ms / avail, _MAX_ATEMPO)
        final_ms = int(round(clip_ms / ratio))
        out.append({"pos": pos, "ratio": ratio, "dur": final_ms})
        cursor = pos + final_ms
    return out


def _atempo(clip: "AudioSegment", ratio: float) -> "AudioSegment":
    """Speed up via ffmpeg atempo (pitch-preserving). ratio in (1.0, 2.0]."""
    if ratio <= 1.0:
        return clip
    with tempfile.TemporaryDirectory() as tmp:
        src = str(Path(tmp) / "in.mp3")
        dst = str(Path(tmp) / "out.mp3")
        clip.export(src, format="mp3")
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-filter:a", f"atempo={ratio:.3f}", dst],
            check=True, capture_output=True,
        )
        return AudioSegment.from_file(dst)


def build_voice_track(
    segments: List[Dict],
    zh_texts: List[str],
    voice_id: str,
    mm_key: str,
    mm_group: str,
    mm_model: str,
    mm_base: str,
    video_ms: int,
) -> "AudioSegment":
    """B：先按全局 base_speed 生成 TTS（匀速、自然）；A：gap-aware 锚定放置，残余才小幅 atempo。"""
    from app.services.podcast_service import _tts_bytes

    base_speed = compute_base_speed(zh_texts, video_ms)
    clips: List[Optional[AudioSegment]] = []
    durations: List[int] = []
    for zh in zh_texts:
        if not zh.strip():
            clips.append(None)
            durations.append(0)
            continue
        data = _tts_bytes(zh, voice_id, mm_key, mm_group, mm_model, mm_base, speed=base_speed)
        clip = AudioSegment.from_file(io.BytesIO(data))
        clips.append(clip)
        durations.append(len(clip))

    plans = plan_placements(segments, durations, video_ms)
    base = AudioSegment.silent(duration=max(video_ms, 1))
    for clip, plan in zip(clips, plans):
        if clip is None:
            continue
        if plan["ratio"] > 1.0:
            clip = _atempo(clip, plan["ratio"])
        base = base.overlay(clip, position=plan["pos"])
    return base


def compose(video_path: str, voice_track: "AudioSegment", out_path: str) -> int:
    """Duck the original audio (-18dB) + overlay the voice track, then mux onto the video.
    Returns the output duration in seconds."""
    with tempfile.TemporaryDirectory() as tmp:
        orig_mp3 = _extract_audio(video_path, str(Path(tmp) / "orig.mp3"), 44100, 2)
        original = AudioSegment.from_file(orig_mp3)
        final = original.apply_gain(_DUCK_DB).overlay(voice_track)
        final_path = str(Path(tmp) / "final.mp3")
        final.export(final_path, format="mp3")
        # mp4 can't hold VP9/VP8 via stream-copy. If yt-dlp fell back to webm/mkv,
        # re-encode the video to H.264; otherwise copy the stream (fast, lossless).
        ext = Path(video_path).suffix.lower()
        if ext in (".webm", ".mkv"):
            video_codec_args = ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
        else:
            video_codec_args = ["-c:v", "copy"]
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-i", final_path,
             "-map", "0:v:0", "-map", "1:a:0", *video_codec_args, "-c:a", "aac",
             # +faststart 把 moov 元数据挪到文件开头：iOS <video> 第一段就能起播，不必先跳到
             # 文件末尾找 moov——在弱网（如经 GFW/Cloudflare 的跨境大媒体流）下少几次易被重置的来回。
             "-movflags", "+faststart",
             "-shortest", out_path],
            check=True, capture_output=True,
        )
        return int(len(original) / 1000)


def probe_local_duration(video_path: str) -> int:
    """ffprobe a local file for its duration (seconds). Raises ValueError if the
    file isn't a readable video or exceeds the 10-minute cap."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            check=True, capture_output=True, text=True,
        )
        dur = int(float(out.stdout.strip()))
    except Exception as exc:
        raise ValueError("无法识别为视频文件，请换一个文件。") from exc
    if dur <= 0:
        raise ValueError("无法读取视频时长。")
    if dur > MAX_DURATION_S:
        raise ValueError("视频超过 10 分钟上限，请换更短的视频。")
    return dur


def purge_expired(db) -> int:
    """Delete DubVideo rows (and their mp4 files) older than DUB_RETENTION_DAYS.
    Best-effort on files: a missing/unremovable file never blocks row deletion.
    Returns the number of rows purged."""
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.models.entities import DubVideo

    cutoff = datetime.utcnow() - timedelta(days=DUB_RETENTION_DAYS)
    stale = db.scalars(select(DubVideo).where(DubVideo.created_at < cutoff)).all()
    count = 0
    for d in stale:
        try:
            p = Path(d.video_path)
            if p.exists():
                p.unlink()
        except OSError:
            pass
        db.delete(d)
        count += 1
    if count:
        db.commit()
    return count
