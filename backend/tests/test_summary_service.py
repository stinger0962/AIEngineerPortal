import pytest


def _mock_claude(monkeypatch, response_text):
    from unittest.mock import MagicMock
    import anthropic
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client = MagicMock()
    client.messages.create.return_value = msg
    monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: client)
    return client


def test_generate_summary_parses_valid_json(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '{"title":"标题","tldr":"一句话","key_points":["要点1","要点2"],"takeaways":["收获1"]}')
    out = generate_summary("正文内容", "fake_key", "fake_model")
    assert out["title"] == "标题"
    assert out["tldr"] == "一句话"
    assert out["key_points"] == ["要点1", "要点2"]
    assert out["takeaways"] == ["收获1"]


def test_generate_summary_strips_code_fences(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '```json\n{"title":"T","tldr":"x","key_points":[],"takeaways":[]}\n```')
    out = generate_summary("正文", "k", "m")
    assert out["tldr"] == "x"


def test_generate_summary_malformed_raises(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, "this is not json at all")
    with pytest.raises(ValueError, match="parse summary"):
        generate_summary("正文", "k", "m")


def test_generate_summary_missing_tldr_raises(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '{"title":"T","key_points":[],"takeaways":[]}')
    with pytest.raises(ValueError, match="tldr"):
        generate_summary("正文", "k", "m")
