"""Unit tests for podcast_service helpers (no network calls)."""
import pytest
from app.services.podcast_service import validate_youtube_url


def test_validate_youtube_url_standard():
    assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True


def test_validate_youtube_url_short():
    assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True


def test_validate_youtube_url_with_timestamp():
    assert validate_youtube_url("https://www.youtube.com/watch?v=48IEIUMtFbI&t=1500s") is True


def test_validate_youtube_url_invalid():
    assert validate_youtube_url("https://vimeo.com/123456") is False
    assert validate_youtube_url("not a url") is False


def test_extract_transcript_retries_then_succeeds(monkeypatch):
    """A blocked IP on the first attempt should trigger a retry with a fresh api
    that succeeds — the sticky-IP rotation strategy."""
    import app.services.podcast_service as svc

    attempts = {"n": 0}

    def fake_build_api():
        return object()  # api object is opaque; _fetch is mocked

    def fake_fetch(api, video_id):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("blocked: too many 429 error responses")
        return "the transcript text"

    monkeypatch.setattr(svc, "_build_transcript_api", fake_build_api)
    monkeypatch.setattr(svc, "_fetch_transcript_text", fake_fetch)
    monkeypatch.setattr(svc, "fetch_video_title", lambda url: "My Title")
    monkeypatch.setattr(svc.time, "sleep", lambda s: None)  # no real delay

    title, text = svc.extract_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert title == "My Title"
    assert text == "the transcript text"
    assert attempts["n"] == 2  # failed once, succeeded on retry


def test_extract_transcript_does_not_retry_disabled(monkeypatch):
    """TranscriptsDisabled is a genuine content error — fail fast, no retries."""
    import app.services.podcast_service as svc
    from youtube_transcript_api import TranscriptsDisabled

    attempts = {"n": 0}

    def fake_fetch(api, video_id):
        attempts["n"] += 1
        raise TranscriptsDisabled(video_id)

    monkeypatch.setattr(svc, "_build_transcript_api", lambda: object())
    monkeypatch.setattr(svc, "_fetch_transcript_text", fake_fetch)
    monkeypatch.setattr(svc.time, "sleep", lambda s: None)

    with pytest.raises(ValueError, match="disabled"):
        svc.extract_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert attempts["n"] == 1  # no retry on genuine error


def test_extract_transcript_exhausts_attempts(monkeypatch):
    """If every attempt is blocked, raise a clear rate-limit ValueError after
    exhausting all attempts."""
    import app.services.podcast_service as svc

    attempts = {"n": 0}

    def fake_fetch(api, video_id):
        attempts["n"] += 1
        raise RuntimeError("blocked: too many 429 error responses")

    monkeypatch.setattr(svc, "_build_transcript_api", lambda: object())
    monkeypatch.setattr(svc, "_fetch_transcript_text", fake_fetch)
    monkeypatch.setattr(svc.time, "sleep", lambda s: None)

    with pytest.raises(ValueError, match="rate-limiting"):
        svc.extract_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert attempts["n"] == svc._TRANSCRIPT_MAX_ATTEMPTS


def test_build_single_prompt_contains_transcript():
    from app.services.podcast_service import _build_prompt
    prompt = _build_prompt("This is the transcript.", digest_length_mins=5, fmt="single")
    assert "This is the transcript." in prompt
    assert "30%" in prompt  # 5 min -> 30%


def test_build_dialogue_prompt_contains_format_instruction():
    from app.services.podcast_service import _build_prompt
    prompt = _build_prompt("Transcript here.", digest_length_mins=10, fmt="dialogue")
    assert "主持人A:" in prompt
    assert "60%" in prompt  # 10 min -> 60%
    assert "Transcript here." in prompt


def test_parse_dialogue_lines():
    from app.services.podcast_service import _parse_dialogue
    script = "主持人A: 你好，欢迎收听。\n主持人B: 谢谢，今天我们聊聊AI。\n主持人A: 对的。"
    lines = _parse_dialogue(script)
    assert lines == [
        ("A", "你好，欢迎收听。"),
        ("B", "谢谢，今天我们聊聊AI。"),
        ("A", "对的。"),
    ]


def test_parse_dialogue_skips_blank_lines():
    from app.services.podcast_service import _parse_dialogue
    script = "主持人A: 第一句。\n\n主持人B: 第二句。"
    lines = _parse_dialogue(script)
    assert len(lines) == 2


def test_fetch_video_title_returns_title_on_success():
    """fetch_video_title parses the oEmbed JSON and returns the title field."""
    from unittest.mock import patch, MagicMock
    from app.services.podcast_service import fetch_video_title
    import json

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"title": "Test Video Title"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = fetch_video_title("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result == "Test Video Title"


def test_fetch_video_title_returns_empty_on_failure():
    """fetch_video_title never raises — returns '' on any network error."""
    from unittest.mock import patch
    from app.services.podcast_service import fetch_video_title

    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        result = fetch_video_title("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result == ""


def test_get_chinese_title_uses_translation_prompt_when_title_provided():
    """When english_title is provided, get_chinese_title builds a translation prompt."""
    from unittest.mock import patch, MagicMock
    from app.services.podcast_service import get_chinese_title

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="  测试视频标题  ")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("anthropic.Anthropic", return_value=mock_client):
        result = get_chinese_title("Test Title", "some transcript", "fake_key", "fake_model")

    assert result == "测试视频标题"
    call_args = mock_client.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "翻译" in prompt
    assert "Test Title" in prompt


def test_get_chinese_title_uses_inference_prompt_when_no_title():
    """When english_title is empty, get_chinese_title infers title from transcript."""
    from unittest.mock import patch, MagicMock
    from app.services.podcast_service import get_chinese_title

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="推断出的标题")]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("anthropic.Anthropic", return_value=mock_client):
        result = get_chinese_title("", "This is the transcript content...", "fake_key", "fake_model")

    assert result == "推断出的标题"
    call_args = mock_client.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "讲稿" in prompt
    assert "This is the transcript content..." in prompt


def test_webshare_proxy_config_accepts_correct_kwargs():
    """WebshareProxyConfig uses proxy_username/proxy_password."""
    from youtube_transcript_api.proxies import WebshareProxyConfig
    # Must not raise TypeError
    cfg = WebshareProxyConfig(proxy_username="user", proxy_password="pass")
    assert cfg is not None


def test_tts_bytes_decodes_minimax_hex_audio():
    """_tts_bytes posts to MiniMax and decodes the hex audio field to raw bytes."""
    from unittest.mock import patch, MagicMock
    from app.services.podcast_service import _tts_bytes

    raw = b"\x49\x44\x33fakemp3"  # arbitrary bytes
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": {"audio": raw.hex()},
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        out = _tts_bytes("你好", "Chinese (Mandarin)_Radio_Host", "key", "gid")

    assert out == raw
    # Verify the request shape: GroupId in URL, voice_id + mp3 format in body
    call = mock_post.call_args
    assert "GroupId=gid" in call.args[0]
    assert call.kwargs["json"]["voice_setting"]["voice_id"] == "Chinese (Mandarin)_Radio_Host"
    assert call.kwargs["json"]["audio_setting"]["format"] == "mp3"


def test_pick_dialogue_voice_respects_gender():
    from app.services.podcast_service import pick_dialogue_voice, DIALOGUE_CATALOG
    female_ids = {v["voice_id"] for v in DIALOGUE_CATALOG if v["gender"] == "female"}
    male_ids = {v["voice_id"] for v in DIALOGUE_CATALOG if v["gender"] == "male"}
    # Many draws should always stay within the requested gender pool
    for _ in range(50):
        assert pick_dialogue_voice("female") in female_ids
        assert pick_dialogue_voice("male") in male_ids


def test_pick_random_narration_in_pool():
    from app.services.podcast_service import pick_random_narration, _NARRATION_VOICE_IDS
    for _ in range(50):
        assert pick_random_narration() in _NARRATION_VOICE_IDS


def test_resolve_voice_random_and_explicit():
    from app.services.podcast_service import resolve_voice, _NARRATION_VOICE_IDS
    # "random" / None / "" -> a valid narration voice
    assert resolve_voice("random") in _NARRATION_VOICE_IDS
    assert resolve_voice(None) in _NARRATION_VOICE_IDS
    assert resolve_voice("") in _NARRATION_VOICE_IDS
    # explicit valid voice is preserved
    a_valid = next(iter(_NARRATION_VOICE_IDS))
    assert resolve_voice(a_valid) == a_valid
    # unknown voice falls back to a valid one (never passes garbage to the API)
    assert resolve_voice("Nonexistent_Voice_XYZ") in _NARRATION_VOICE_IDS


def test_narration_and_dialogue_pools_are_distinct_concepts():
    """Dialogue female/male pools must each be non-empty so casting never fails."""
    from app.services.podcast_service import DIALOGUE_CATALOG
    females = [v for v in DIALOGUE_CATALOG if v["gender"] == "female"]
    males = [v for v in DIALOGUE_CATALOG if v["gender"] == "male"]
    assert len(females) >= 1
    assert len(males) >= 1


def test_tts_bytes_raises_on_minimax_error_status():
    """A non-zero MiniMax status_code surfaces as a ValueError, not silent garbage."""
    from unittest.mock import patch, MagicMock
    from app.services.podcast_service import _tts_bytes

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": None,
        "base_resp": {"status_code": 1004, "status_msg": "invalid voice_id"},
    }

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(ValueError, match="1004"):
            _tts_bytes("你好", "bad_voice", "key", "gid")
