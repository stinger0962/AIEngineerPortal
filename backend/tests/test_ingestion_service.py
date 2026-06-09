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
    monkeypatch.setattr(ing, "_fetch_via_proxy", lambda url, ua: None)  # proxy also yields nothing
    with pytest.raises(ValueError, match="extract article text"):
        ing._ingest_web("https://example.com/x")


def test_ingest_web_wechat_uses_proxy(monkeypatch):
    """WeChat URLs fetch through the proxy (with MicroMessenger UA), then extract."""
    import app.services.ingestion_service as ing
    import trafilatura

    calls = {}

    def fake_proxy(url, user_agent):
        calls["url"] = url
        calls["ua"] = user_agent
        return "<html>fake wechat html</html>"

    monkeypatch.setattr(ing, "_fetch_via_proxy", fake_proxy)
    monkeypatch.setattr(trafilatura, "extract", lambda *a, **k: "微信文章正文。" * 50)
    monkeypatch.setattr(trafilatura, "extract_metadata", lambda html: None)

    title, text = ing._ingest_web("https://mp.weixin.qq.com/s?__biz=abc&mid=123")
    assert "微信文章正文" in text
    assert "MicroMessenger" in calls["ua"]   # WeChat UA was used
    assert "mp.weixin.qq.com" in calls["url"]


def test_ingest_web_falls_back_to_proxy(monkeypatch):
    """Non-WeChat site: if direct fetch yields nothing, retry through the proxy."""
    import app.services.ingestion_service as ing
    import trafilatura

    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: None)  # direct fails
    monkeypatch.setattr(ing, "_fetch_via_proxy", lambda url, ua: "<html>proxied</html>")
    monkeypatch.setattr(trafilatura, "extract", lambda *a, **k: "代理获取的正文。" * 50)
    monkeypatch.setattr(trafilatura, "extract_metadata", lambda html: None)

    title, text = ing._ingest_web("https://example.com/blocked-article")
    assert "代理获取的正文" in text


def test_ingest_x_tweet_via_fxtwitter(monkeypatch):
    """X/Twitter URLs fetch tweet text via the fxtwitter embed API."""
    import app.services.ingestion_service as ing
    from unittest.mock import MagicMock
    import httpx

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"tweet": {"text": "这是一条推文。" * 30, "author": {"name": "某人"}}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: resp)

    title, text = ing._ingest_web("https://x.com/foo/status/123")
    assert "某人" in title
    assert "这是一条推文" in text


def test_ingest_x_article_raises(monkeypatch):
    """X long-form Articles can't be extracted → clear error, not junk."""
    import app.services.ingestion_service as ing
    from unittest.mock import MagicMock
    import httpx

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"tweet": {"text": "http://x.com/i/article/999", "author": {"name": "某人"}}}
    monkeypatch.setattr(httpx, "get", lambda *a, **k: resp)

    with pytest.raises(ValueError, match="长文"):
        ing._ingest_web("https://x.com/foo/status/123")


def test_ingest_web_js_shell_raises(monkeypatch):
    """A JavaScript-only shell page must error, not be summarized into nonsense."""
    import app.services.ingestion_service as ing
    import trafilatura

    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: "<html>shell</html>")
    monkeypatch.setattr(
        trafilatura, "extract",
        lambda *a, **k: "We've detected that JavaScript is disabled in this browser. Please enable JavaScript.",
    )
    monkeypatch.setattr(ing, "_fetch_via_proxy", lambda url, ua: None)
    with pytest.raises(ValueError, match="JavaScript"):
        ing._ingest_web("https://example.com/spa-page")


def test_x_host_not_falsely_matched():
    """'x.com' substring must not match unrelated hosts like netflix.com."""
    from app.services.ingestion_service import _host, _X_HOSTS
    assert _host("https://netflix.com/title/123") not in _X_HOSTS
    assert _host("https://x.com/foo/status/1") in _X_HOSTS
    assert _host("https://twitter.com/foo/status/1") in _X_HOSTS


def test_ingest_youtube_reuses_extract_transcript(monkeypatch):
    import app.services.ingestion_service as ing
    monkeypatch.setattr(ing, "_ingest_youtube", lambda url: ("Vid", "视频讲稿内容。" * 80))
    title, text = ing.ingest("youtube", "https://youtube.com/watch?v=abc12345678")
    assert title == "Vid"
    assert "视频讲稿" in text
