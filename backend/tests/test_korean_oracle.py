from app.services.korean.oracle import KoreanOracle


class _FakeBlock:
    def __init__(self, text): self.type = "text"; self.text = text


class _FakeUsage:
    input_tokens = 10; output_tokens = 5


class _FakeResp:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]; self.usage = _FakeUsage()


class _FakeMessages:
    def __init__(self, text): self._text = text
    def create(self, **kwargs):
        self._kwargs = kwargs
        return _FakeResp(self._text)


class _FakeClient:
    def __init__(self, text): self.messages = _FakeMessages(text)


def test_oracle_system_prompt_constrains_vocab():
    client = _FakeClient("네, 아메리카노 한 잔이요. [[goal_met]]")
    oracle = KoreanOracle(client=client, model="x")
    boss = {"goal_en": "Order coffee", "persona": "barista", "level": "beginner",
            "allowed_vocab": ["아메리카노", "주세요"], "success_criteria": "orders a drink", "max_turns": 8}
    result = oracle.run(boss=boss, messages=[{"role": "user", "content": "아메리카노 주세요"}])
    assert result is not None
    assert result["goal_met"] is True
    assert "아메리카노" in client.messages._kwargs["system"]  # allowed vocab injected


def test_oracle_detects_goal_not_met():
    client = _FakeClient("안녕하세요! 뭐 드릴까요?")
    oracle = KoreanOracle(client=client, model="x")
    boss = {"goal_en": "Order coffee", "persona": "barista", "level": "beginner",
            "allowed_vocab": ["아메리카노"], "success_criteria": "orders a drink", "max_turns": 8}
    result = oracle.run(boss=boss, messages=[{"role": "user", "content": "안녕하세요"}])
    assert result["goal_met"] is False
    assert "[[goal_met]]" not in result["response"]  # marker stripped from display text


def test_oracle_returns_none_on_api_failure():
    class _Boom:
        class messages:
            @staticmethod
            def create(**kwargs): raise RuntimeError("down")
    oracle = KoreanOracle(client=_Boom(), model="x")
    boss = {"goal_en": "x", "persona": "barista", "level": "beginner",
            "allowed_vocab": [], "success_criteria": "x", "max_turns": 8}
    assert oracle.run(boss=boss, messages=[{"role": "user", "content": "hi"}]) is None
