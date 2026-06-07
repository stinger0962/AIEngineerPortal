import pytest


def test_ingest_text_passthrough():
    from app.services.ingestion_service import ingest
    long_text = "你好世界。" * 60  # > 200 chars
    title, text = ingest("text", long_text)
    assert title == ""
    assert "你好世界" in text


def test_ingest_too_short_raises():
    from app.services.ingestion_service import ingest
    with pytest.raises(ValueError, match="too short"):
        ingest("text", "太短了")


def test_ingest_unknown_type_raises():
    from app.services.ingestion_service import ingest
    with pytest.raises(ValueError, match="Unknown source type"):
        ingest("pdf", "whatever")


def test_ingest_web_uses_trafilatura(monkeypatch):
    import app.services.ingestion_service as ing
    monkeypatch.setattr(ing, "_ingest_web", lambda url: ("Web Title", "网页正文。" * 80))
    title, text = ing.ingest("web", "https://example.com/article")
    assert title == "Web Title"
    assert "网页正文" in text


def test_ingest_web_empty_extraction_raises(monkeypatch):
    import app.services.ingestion_service as ing
    import trafilatura
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: "<html></html>")
    monkeypatch.setattr(trafilatura, "extract", lambda *a, **k: None)
    with pytest.raises(ValueError, match="extract article text"):
        ing._ingest_web("https://example.com/x")


def test_ingest_youtube_reuses_extract_transcript(monkeypatch):
    import app.services.ingestion_service as ing
    monkeypatch.setattr(ing, "_ingest_youtube", lambda url: ("Vid", "视频讲稿内容。" * 80))
    title, text = ing.ingest("youtube", "https://youtube.com/watch?v=abc12345678")
    assert title == "Vid"
    assert "视频讲稿" in text
