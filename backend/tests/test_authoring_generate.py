import pytest

from scripts.korean_authoring.briefs import get_brief
from scripts.korean_authoring.generate import extract_json, coerce_region, generate_region


def test_extract_json_strips_fences():
    assert extract_json("```json\n{\"a\": 1}\n```") == {"a": 1}
    assert extract_json("prose before {\"b\": 2} after") == {"b": 2}


def test_extract_json_raises_without_object():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_coerce_prefixes_slug_and_renumbers():
    brief = get_brief("getting-around")
    nodes = [
        {"slug": "subway", "kind": "scene", "title": "S",
         "content_json": {"setting": "s", "character": "c", "lines": [{"speaker": "c", "ko": "x", "romaji": "x", "en": "x"}],
                          "your_turns": [], "new_vocab": [{"ko": "x", "en": "x", "romaji": "x"}]}},
    ]
    region = coerce_region(brief, nodes)
    assert region["slug"] == "getting-around"
    assert region["nodes"][0]["slug"] == "getting-around-subway"
    assert region["nodes"][0]["order_index"] == 0
    assert region["nodes"][0]["content_json"]["lines"][0]["audio_key"]


class _Block:
    def __init__(self, t): self.type = "text"; self.text = t


class _Resp:
    def __init__(self, t): self.content = [_Block(t)]


class _Msgs:
    def __init__(self, t): self._t = t; self.calls = 0
    def create(self, **kw): self.calls += 1; return _Resp(self._t)


class _Client:
    def __init__(self, t): self.messages = _Msgs(t)


def test_generate_region_parses_and_coerces():
    brief = get_brief("getting-around")
    payload = '{"nodes":[{"slug":"x","kind":"boss","title":"B","content_json":{"goal_en":"g","persona":"taxi_driver","level":"beginner","allowed_vocab":["버스"],"success_criteria":"s","max_turns":8}}]}'
    client = _Client(payload)
    region = generate_region(brief, client, "m")
    assert region["slug"] == "getting-around"
    assert region["nodes"][0]["slug"] == "getting-around-x"
    assert region["nodes"][0]["order_index"] == 0


def test_generate_region_raises_on_unparseable():
    brief = get_brief("getting-around")
    with pytest.raises(ValueError):
        generate_region(brief, _Client("not json at all"), "m", max_retries=1)
