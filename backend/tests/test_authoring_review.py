from scripts.korean_authoring.briefs import get_brief
from scripts.korean_authoring.review import review_region


class _Block:
    def __init__(self, t): self.type = "text"; self.text = t


class _Resp:
    def __init__(self, t): self.content = [_Block(t)]


class _Msgs:
    def __init__(self, t): self._t = t
    def create(self, **kw): return _Resp(self._t)


class _Client:
    def __init__(self, t): self.messages = _Msgs(t)


def test_review_returns_notes():
    brief = get_brief("getting-around")
    client = _Client('{"notes":[{"node":"getting-around-bus","severity":"low","note":"slightly formal"}]}')
    notes = review_region(brief, {"slug": "getting-around", "nodes": []}, client, "m")
    assert notes == [{"node": "getting-around-bus", "severity": "low", "note": "slightly formal"}]


def test_review_tolerates_garbage():
    brief = get_brief("getting-around")
    notes = review_region(brief, {"slug": "getting-around", "nodes": []}, _Client("sorry, no json"), "m")
    assert notes == []
