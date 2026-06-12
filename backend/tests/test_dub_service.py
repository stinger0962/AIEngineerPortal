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


def test_translate_segments_parses_numbered(monkeypatch):
    import app.services.dub_service as dub
    from unittest.mock import MagicMock
    import anthropic

    segs = [{"start": 0, "end": 1, "text": "Hello"}, {"start": 1, "end": 2, "text": "World"}]
    msg = MagicMock(); msg.content = [MagicMock(text="1. 你好\n2. 世界")]
    client = MagicMock(); client.messages.create.return_value = msg
    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: client)

    out = dub.translate_segments(segs, "k", "m")
    assert out == ["你好", "世界"]


def test_translate_segments_fallback_on_missing(monkeypatch):
    import app.services.dub_service as dub
    from unittest.mock import MagicMock
    import anthropic

    segs = [{"start": 0, "end": 1, "text": "Hello"}, {"start": 1, "end": 2, "text": "World"}]
    msg = MagicMock(); msg.content = [MagicMock(text="1. 你好")]  # line 2 missing
    client = MagicMock(); client.messages.create.return_value = msg
    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: client)

    out = dub.translate_segments(segs, "k", "m")
    assert out == ["你好", "World"]


def test_plan_placements_anchors_caps_and_overflows():
    from app.services.dub_service import plan_placements, _MAX_SPEED
    segs = [{"start": 0, "end": 2}, {"start": 2, "end": 4}, {"start": 4, "end": 6}]
    plans = plan_placements(segs, [1500, 5000, 1000])

    assert plans[0]["pos"] == 0 and plans[0]["ratio"] == 1.0 and plans[0]["dur"] == 1500
    assert plans[1]["ratio"] == _MAX_SPEED and plans[1]["dur"] == 4000
    assert plans[1]["pos"] == 2000
    assert plans[2]["pos"] == 6000


def test_probe_local_duration_rejects_too_long(monkeypatch):
    import app.services.dub_service as dub

    class R:
        stdout = "700.0"

    monkeypatch.setattr(dub.subprocess, "run", lambda *a, **k: R())
    with pytest.raises(ValueError, match="10 分钟"):
        dub.probe_local_duration("/tmp/x.mp4")


def test_probe_local_duration_returns_seconds(monkeypatch):
    import app.services.dub_service as dub

    class R:
        stdout = "300.5\n"

    monkeypatch.setattr(dub.subprocess, "run", lambda *a, **k: R())
    assert dub.probe_local_duration("/tmp/x.mp4") == 300


def test_probe_local_duration_rejects_non_video(monkeypatch):
    import app.services.dub_service as dub

    def boom(*a, **k):
        raise RuntimeError("not a video")

    monkeypatch.setattr(dub.subprocess, "run", boom)
    with pytest.raises(ValueError, match="无法识别为视频"):
        dub.probe_local_duration("/tmp/notvideo.txt")


def test_purge_expired_deletes_old_keeps_fresh(tmp_path):
    from datetime import datetime, timedelta
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models.entities import DubVideo
    import app.services.dub_service as dub

    engine = create_engine("sqlite://")
    DubVideo.__table__.create(bind=engine)

    old_file = tmp_path / "old.mp4"
    old_file.write_bytes(b"x")
    fresh_file = tmp_path / "fresh.mp4"
    fresh_file.write_bytes(b"y")

    now = datetime.utcnow()
    with Session(engine) as s:
        old = DubVideo(youtube_url=None, title="old", voice_id="v", video_path=str(old_file),
                       created_at=now - timedelta(days=8))
        fresh = DubVideo(youtube_url=None, title="fresh", voice_id="v", video_path=str(fresh_file),
                         created_at=now)
        missing = DubVideo(youtube_url=None, title="missing", voice_id="v",
                           video_path=str(tmp_path / "gone.mp4"),
                           created_at=now - timedelta(days=9))
        s.add_all([old, fresh, missing])
        s.commit()

        purged = dub.purge_expired(s)

        assert purged == 2  # old + missing
        remaining = s.scalars(select(DubVideo)).all()
        assert [d.title for d in remaining] == ["fresh"]

    assert not old_file.exists()      # file removed
    assert fresh_file.exists()        # fresh kept
