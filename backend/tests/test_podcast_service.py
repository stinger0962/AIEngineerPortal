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


def test_generic_proxy_config_accepts_correct_kwargs():
    """GenericProxyConfig uses http_url/https_url, not http_proxy/https_proxy."""
    from youtube_transcript_api.proxies import GenericProxyConfig
    proxy_url = "http://user:pass@host:1234"
    # Must not raise TypeError
    cfg = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
    assert cfg is not None
