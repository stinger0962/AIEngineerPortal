def test_scribe_transcript_table_and_columns():
    from app.models.entities import ScribeTranscript
    assert ScribeTranscript.__tablename__ == "scribe_transcripts"
    cols = set(ScribeTranscript.__table__.columns.keys())
    assert {"id", "youtube_url", "title", "transcript", "char_count", "created_at"}.issubset(cols)
