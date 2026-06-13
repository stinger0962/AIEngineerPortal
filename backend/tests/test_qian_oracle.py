from types import SimpleNamespace
from typing import Any

from app.services.qian.oracle import QianOracle

SIGN = {
    "id": 7, "grade": "上签", "palace": "辰宫", "title": "李世民登位",
    "poetry": "一句签诗。二句签诗。三句签诗。四句签诗。",
    "meaning": "此卦吉象。", "holy": "圣意如此。",
}


def _fake_response(text: str, in_tok=200, out_tok=120):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


class FakeClient:
    def __init__(self, response): self._r = response; self.calls = []
    class _M:
        def __init__(self, o): self._o = o
        def create(self, **k): self._o.calls.append(k); return self._o._r
    @property
    def messages(self): return FakeClient._M(self)


def test_system_prompt_has_sign_and_persona():
    client = FakeClient(_fake_response("签诗大意……宽心即可。"))
    oracle = QianOracle(client=client, model="m")
    oracle.run(sign=SIGN, question="今年事业如何？")
    system = client.calls[0]["system"]
    assert "一句签诗" in system
    assert "上签" in system and "辰宫" in system
    assert "解签人" in system
    assert "[[term:" in system
    user_msg = client.calls[0]["messages"][-1]["content"]
    assert "今年事业" in user_msg


def test_run_returns_clean_segments_cameras():
    client = FakeClient(_fake_response("此乃上签。[[term:辰宫|地支之一]] 凡事可成。"))
    oracle = QianOracle(client=client, model="m")
    result = oracle.run(sign=SIGN, question="问")
    assert result is not None
    assert "[[" not in result["response"]
    assert any(c["type"] == "explain_term" for c in result["camera_commands"])
    assert result["_meta"]["input_tokens"] == 200


def test_run_none_on_exception():
    client = FakeClient(Exception("boom"))
    oracle = QianOracle(client=client, model="m")
    assert oracle.run(sign=SIGN, question="问") is None
