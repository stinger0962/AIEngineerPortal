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


def test_generate_mindmap_valid(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    md = "# 中心主题\n## 分支一\n- 要点1\n## 分支二\n- 要点2"
    _mock_claude(monkeypatch, md)
    out = generate_mindmap("正文内容", "k", "m")
    assert out["title"] == "中心主题"
    assert "## 分支一" in out["markdown"]


def test_generate_mindmap_strips_fences(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    _mock_claude(monkeypatch, "```markdown\n# 主题\n## A\n- x\n## B\n- y\n```")
    out = generate_mindmap("正文", "k", "m")
    assert out["title"] == "主题"
    assert out["markdown"].startswith("# 主题")


def test_generate_mindmap_no_structure_raises(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    _mock_claude(monkeypatch, "就是一段没有任何标题的普通文字")
    with pytest.raises(ValueError, match="structure"):
        generate_mindmap("正文", "k", "m")


def test_generate_mindmap_single_branch_raises(monkeypatch):
    from app.services.mindmap_service import generate_mindmap
    _mock_claude(monkeypatch, "# 主题\n## 只有一个分支\n- x")
    with pytest.raises(ValueError, match="structure"):
        generate_mindmap("正文", "k", "m")
