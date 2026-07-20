"""配 Dub: foreign YouTube video -> Chinese voice-over dubbed mp4."""
from __future__ import annotations

import io
import logging
import os
import random
import re
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Known-good narration voice used as a safety net if a chosen voice is rejected.
_DUB_FALLBACK_VOICE = "Chinese (Mandarin)_Radio_Host"

# MiniMax caps TTS requests-per-minute (RPM) per account. The dub bursts many TTS
# calls in parallel, which trips "1002 rate limit exceeded(RPM)". Proactively space
# request STARTS ≥ _TTS_MIN_INTERVAL apart (across all threads) so we stay under the
# cap. Tune via MINIMAX_TTS_MIN_INTERVAL env (seconds): 2.0s ≈ 30 RPM. Lower it if
# your MiniMax tier allows a higher RPM (faster dubs); raise it if 1002 persists.
_TTS_MIN_INTERVAL = float(os.getenv("MINIMAX_TTS_MIN_INTERVAL", "2.0"))
_tts_rl_lock = threading.Lock()
_tts_last_start = 0.0


def _tts_throttled(*args, **kwargs) -> bytes:
    """Rate-limited wrapper around MiniMax _tts_bytes: reserve a start slot ≥
    _TTS_MIN_INTERVAL after the previous one (the sleep runs under the lock so
    threads queue in order), then do the actual HTTP call outside the lock so
    requests still overlap."""
    global _tts_last_start
    from app.services.podcast_service import _tts_bytes

    with _tts_rl_lock:
        wait = _TTS_MIN_INTERVAL - (time.monotonic() - _tts_last_start)
        if wait > 0:
            time.sleep(wait)
        _tts_last_start = time.monotonic()
    return _tts_bytes(*args, **kwargs)


def _is_rate_limit(exc: Exception) -> bool:
    s = str(exc).lower()
    return "1002" in s or "rate limit" in s or "rpm" in s or "429" in s or "too many" in s


def _resolve_dub_voice(voice_id: str, mm_key: str, mm_group: str, mm_model: str, mm_base: str) -> str:
    """Probe the chosen narration voice once (tiny TTS). If MiniMax rejects it
    (unknown/invalid id), fall back to a known-good voice so a bad selection never
    fails the whole dub job. Negligible next to the full transcribe→dub pipeline."""
    try:
        _tts_throttled("你好", voice_id, mm_key, mm_group, mm_model, mm_base)
        return voice_id
    except Exception as exc:  # noqa: BLE001
        # A rate-limit here isn't the voice's fault — don't wrongly fall back.
        if _is_rate_limit(exc):
            return voice_id
        logger.warning("dub: voice %r rejected (%s); falling back to %r", voice_id, exc, _DUB_FALLBACK_VOICE)
        return _DUB_FALLBACK_VOICE

_TTS_CONCURRENCY = 5   # fire N MiniMax TTS calls at once (I/O-bound); RPM is capped by _tts_throttled, not this
_TTS_RETRIES = 4       # per-segment retry (rate-limit backoff needs a few attempts to clear the RPM window)

DUB_DIR = Path(os.getenv("DUB_VIDEO_DIR", "/data/dub_videos"))
MAX_DURATION_S = 600
MAX_UPLOAD_BYTES = 100 * 1024 * 1024   # 100 MB upload cap
# Auto-delete dubbed mp4s older than this. Dub outputs are large videos on a small
# droplet, so unlike podcast/oracle (which keep files forever) dub is capped. Default
# 90d; tune via env DUB_RETENTION_DAYS (e.g. a very large number ≈ keep "forever").
DUB_RETENTION_DAYS = int(os.getenv("DUB_RETENTION_DAYS", "90"))
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


def probe_duration(youtube_url: str) -> int:
    """Return duration seconds without downloading. Raises ValueError if unavailable or > 10 min."""
    from app.services import ytdlp_util

    try:
        info = ytdlp_util.extract_info(youtube_url, download=False)
        dur = int(info.get("duration") or 0)
    except Exception as exc:
        raise ValueError(f"无法读取该视频信息：{exc}") from exc
    if dur <= 0:
        raise ValueError("无法读取视频时长。")
    if dur > MAX_DURATION_S:
        raise ValueError("视频超过 10 分钟上限，请换更短的视频。")
    return dur


def download_video(youtube_url: str, out_dir: str) -> Tuple[str, str]:
    """yt-dlp merged mp4 (<=480p) via Webshare proxy, with exit-IP rotation on
    bot-detection. Returns (title, video_path). Capped at 480p because the
    residential proxy is bandwidth-throttled and the video is only a backdrop for
    the Chinese narration — smaller download, faster dubbing."""
    from app.services import ytdlp_util

    try:
        info = ytdlp_util.extract_info(
            youtube_url,
            download=True,
            extra_opts={
                "format": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
                "merge_output_format": "mp4",
                "outtmpl": str(Path(out_dir) / "dub.%(ext)s"),
            },
        )
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

# Translate in batches so a long video never overflows the model's output window.
# A single call used to truncate at max_tokens on long videos → the cut-off tail
# lines didn't parse → every un-parsed segment silently fell back to the ORIGINAL
# foreign transcript and got dubbed back (e.g. a Korean video "dubbed" in Korean).
_TRANSLATE_BATCH = 30
_LINE_RE = re.compile(r"\s*(\d+)\s*[\.、):：]\s*(.+)")
# Hangul (syllables + jamo) and Japanese kana. Chinese never contains these, so if a
# "translation" still has them it wasn't translated → don't synthesize it as the dub.
_NON_CHINESE_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏぀-ヿ]")


def translate_segments(segments: List[Dict], anthropic_api_key: str, model: str) -> List[str]:
    """Translate each subtitle to Chinese, numbered 1:1, in batches (so a long video
    never truncates the response). Returns a list the SAME length as segments; any
    segment that couldn't be translated — missing line, or output still in the source
    language — becomes "" (synthesized as silence), NEVER the foreign original. Raises
    ValueError if most segments fail, so the user gets a clear "翻译失败" instead of a
    broken/foreign-language dub."""
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    result: List[str] = [""] * len(segments)

    for start in range(0, len(segments), _TRANSLATE_BATCH):
        batch = segments[start:start + _TRANSLATE_BATCH]
        numbered = "\n".join(f"{i + 1}. {s['text']}" for i, s in enumerate(batch))
        msg = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": _TRANSLATE_PROMPT.format(numbered=numbered)}],
        )
        raw = msg.content[0].text if msg.content else ""
        for line in raw.splitlines():
            m = _LINE_RE.match(line)
            if not m:
                continue
            local = int(m.group(1)) - 1
            if 0 <= local < len(batch):
                zh = m.group(2).strip()
                # Skip anything that didn't actually become Chinese (empty, or still
                # Hangul/kana) — synthesizing the foreign source is the bug we're killing.
                if zh and not _NON_CHINESE_RE.search(zh):
                    result[start + local] = zh

    src_idx = [i for i, s in enumerate(segments) if s["text"].strip()]
    translated = [i for i in src_idx if result[i]]
    if src_idx and len(translated) < len(src_idx) * 0.5:
        logger.warning("dub translate: only %d/%d segments translated", len(translated), len(src_idx))
        raise ValueError("字幕翻译失败（可能内容过长或语言不支持），请重试或更换视频。")
    return result


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
    voice_id = _resolve_dub_voice(voice_id, mm_key, mm_group, mm_model, mm_base)

    def _synth(zh: str) -> Optional[AudioSegment]:
        if not zh.strip():
            return None
        last_exc: Optional[Exception] = None
        for attempt in range(_TTS_RETRIES):
            try:
                data = _tts_throttled(zh, voice_id, mm_key, mm_group, mm_model, mm_base, speed=base_speed)
                return AudioSegment.from_file(io.BytesIO(data))
            except Exception as exc:  # transient rate-limit / timeout under parallel load → retry
                last_exc = exc
                # Rate-limit (RPM) windows are per-minute — back off much longer than a
                # plain transient, with jitter so parallel workers don't re-fire in sync.
                if _is_rate_limit(exc):
                    time.sleep(3.0 * (attempt + 1) + random.uniform(0, 1.5))
                else:
                    time.sleep(0.6 * (attempt + 1))
        raise last_exc if last_exc else RuntimeError("TTS failed")

    # Parallelize the per-segment TTS (I/O-bound HTTP calls) — order preserved by map().
    with ThreadPoolExecutor(max_workers=_TTS_CONCURRENCY) as ex:
        clips: List[Optional[AudioSegment]] = list(ex.map(_synth, zh_texts))
    durations: List[int] = [len(c) if c is not None else 0 for c in clips]

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
