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
    _mock_claude(monkeypatch, '{"title":"标题","tldr":"一句话","sections":[{"heading":"背景","points":["要点1","要点2"]},{"heading":"影响","points":["影响1"]}]}')
    out = generate_summary("正文内容", "fake_key", "fake_model")
    assert out["title"] == "标题"
    assert out["tldr"] == "一句话"
    assert out["sections"][0]["heading"] == "背景"
    assert out["sections"][0]["points"] == ["要点1", "要点2"]
    assert out["sections"][1]["heading"] == "影响"


def test_generate_summary_strips_code_fences(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '```json\n{"title":"T","tldr":"x","sections":[{"heading":"H","points":["p"]}]}\n```')
    out = generate_summary("正文", "k", "m")
    assert out["tldr"] == "x"
    assert out["sections"][0]["heading"] == "H"


def test_generate_summary_malformed_raises(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, "this is not json at all")
    with pytest.raises(ValueError, match="parse summary"):
        generate_summary("正文", "k", "m")


def test_generate_summary_missing_sections_raises(monkeypatch):
    from app.services.summary_service import generate_summary
    _mock_claude(monkeypatch, '{"title":"T","tldr":"x"}')
    with pytest.raises(ValueError, match="sections"):
        generate_summary("正文", "k", "m")
