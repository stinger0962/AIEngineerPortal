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
    from app.services.dub_service import plan_placements, _MAX_ATEMPO
    # video_ms=8000; segs end at 6s, video ends at 8s
    # seg0: start=0,end=2 → next_start=2000, clip=1500 → fits (ratio 1.0, dur=1500)
    # seg1: start=2,end=4 → next_start=4000, cursor=1500, pos=2000, avail=2000, clip=5000 → ratio=min(2.5,1.15)=1.15
    # seg2: start=4,end=6 → next_start=video_ms=8000, cursor=2000+int(5000/1.15)=2000+4348=6348, pos=6348, avail=1652, clip=1000 → fits
    segs = [{"start": 0, "end": 2}, {"start": 2, "end": 4}, {"start": 4, "end": 6}]
    plans = plan_placements(segs, [1500, 5000, 1000], video_ms=8000)

    assert plans[0]["pos"] == 0 and plans[0]["ratio"] == 1.0 and plans[0]["dur"] == 1500
    assert plans[1]["ratio"] == _MAX_ATEMPO
    assert plans[1]["pos"] == 2000
    assert plans[2]["pos"] > 4000


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


from app.services.dub_service import plan_placements, estimate_ms, compute_base_speed


def test_tts_bytes_passes_speed(monkeypatch):
    import app.services.podcast_service as ps
    captured = {}
    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"base_resp": {"status_code": 0}, "data": {"audio": "00"}}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["speed"] = json["voice_setting"]["speed"]
        return _Resp()
    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)
    ps._tts_bytes("你好", "v", "k", "g", "m", "https://api.minimax.io", speed=1.2)
    assert captured["speed"] == 1.2


def test_estimate_ms_proportional():
    assert estimate_ms("") == 0
    a, b = estimate_ms("六个字六个"), estimate_ms("十二个字十二个字十二")
    assert b > a > 0


def test_compute_base_speed_fits_when_roomy():
    assert compute_base_speed(["你好"], 60_000) == 1.0


def test_compute_base_speed_speeds_up_when_dense():
    zh = ["这是一段很长很长的中文" * 20]
    g = compute_base_speed(zh, 3_000)
    assert 1.0 < g <= 1.30


def test_plan_placements_uses_following_gap():
    segs = [{"start": 0.0, "end": 1.0}, {"start": 5.0, "end": 6.0}]
    plans = plan_placements(segs, [2000, 500], video_ms=8000)
    assert plans[0]["ratio"] == 1.0 and plans[0]["pos"] == 0
    assert plans[0]["dur"] == 2000


def test_plan_placements_speeds_when_exceeds_gap():
    segs = [{"start": 0.0, "end": 1.0}, {"start": 5.0, "end": 6.0}]
    plans = plan_placements(segs, [6000, 500], video_ms=8000)
    assert 1.0 < plans[0]["ratio"] <= 1.15


def test_plan_placements_last_uses_video_end():
    segs = [{"start": 0.0, "end": 1.0}]
    plans = plan_placements(segs, [3000], video_ms=10000)
    assert plans[0]["ratio"] == 1.0


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
