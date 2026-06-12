import pytest


def test_probe_duration_rejects_too_long(monkeypatch):
    import app.services.dub_service as dub

    class FakeYDL:
        def __init__(self, opts): ...
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def extract_info(self, url, download): return {"duration": 700}

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)
    with pytest.raises(ValueError, match="10 分钟"):
        dub.probe_duration("https://youtu.be/abc12345678")


def test_probe_duration_returns_seconds(monkeypatch):
    import app.services.dub_service as dub

    class FakeYDL:
        def __init__(self, opts): ...
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def extract_info(self, url, download): return {"duration": 300}

    import yt_dlp
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)
    assert dub.probe_duration("https://youtu.be/abc12345678") == 300
