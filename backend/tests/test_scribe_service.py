import pytest


def test_download_audio_uses_proxy_and_returns_title(monkeypatch, tmp_path):
    import app.services.scribe_service as svc
    monkeypatch.setenv("WEBSHARE_PROXY_USERNAME", "u")
    monkeypatch.setenv("WEBSHARE_PROXY_PASSWORD", "p")
    captured = {}

    class FakeYDL:
        def __init__(self, opts):
            captured["opts"] = opts
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def extract_info(self, url, download):
            (tmp_path / "scribe.mp3").write_bytes(b"audio")
            return {"title": "测试视频"}

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)

    title, path = svc.download_audio("https://youtu.be/abc12345678", str(tmp_path))
    assert title == "测试视频"
    assert path.endswith("scribe.mp3")
    assert "p.webshare.io" in captured["opts"]["proxy"]


def test_download_audio_failure_raises(monkeypatch, tmp_path):
    import app.services.scribe_service as svc

    class BoomYDL:
        def __init__(self, opts): ...
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def extract_info(self, url, download):
            raise RuntimeError("blocked")

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", BoomYDL)
    with pytest.raises(ValueError, match="无法下载"):
        svc.download_audio("https://youtu.be/abc12345678", str(tmp_path))


def test_transcribe_audio_concatenates(monkeypatch, tmp_path):
    import app.services.scribe_service as svc
    from unittest.mock import MagicMock

    p1 = tmp_path / "a.part0.mp3"; p1.write_bytes(b"x")
    p2 = tmp_path / "a.part1.mp3"; p2.write_bytes(b"y")
    monkeypatch.setattr(svc, "_split_audio", lambda path: [str(p1), str(p2)])

    import openai
    resp = MagicMock(text="片段")
    client = MagicMock()
    client.audio.transcriptions.create.return_value = resp
    monkeypatch.setattr(openai, "OpenAI", lambda api_key: client)

    out = svc.transcribe_audio(str(tmp_path / "a.mp3"), "k")
    assert out == "片段 片段"
    assert not p1.exists()


def test_transcribe_audio_empty_raises(monkeypatch, tmp_path):
    import app.services.scribe_service as svc
    from unittest.mock import MagicMock

    p1 = tmp_path / "a.part0.mp3"; p1.write_bytes(b"x")
    monkeypatch.setattr(svc, "_split_audio", lambda path: [str(p1)])

    import openai
    resp = MagicMock(text="")
    client = MagicMock()
    client.audio.transcriptions.create.return_value = resp
    monkeypatch.setattr(openai, "OpenAI", lambda api_key: client)

    with pytest.raises(ValueError, match="为空"):
        svc.transcribe_audio(str(tmp_path / "a.mp3"), "k")
