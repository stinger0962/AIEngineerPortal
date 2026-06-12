from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.entities import DubVideo


def test_dubvideo_table_name():
    assert DubVideo.__tablename__ == "dub_videos"


def test_dubvideo_allows_null_youtube_url():
    """Uploaded videos have no source URL — the column must accept NULL."""
    engine = create_engine("sqlite://")
    DubVideo.__table__.create(bind=engine)
    with Session(engine) as s:
        d = DubVideo(youtube_url=None, title="local.mp4", voice_id="v1", video_path="/tmp/x.mp4")
        s.add(d)
        s.commit()
        s.refresh(d)
        assert d.id is not None
        assert d.youtube_url is None
