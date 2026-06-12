def test_dub_video_table_and_columns():
    from app.models.entities import DubVideo
    assert DubVideo.__tablename__ == "dub_videos"
    cols = set(DubVideo.__table__.columns.keys())
    assert {"id", "youtube_url", "title", "voice_id", "video_path", "duration_secs", "created_at"}.issubset(cols)
