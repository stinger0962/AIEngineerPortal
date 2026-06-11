"""Tests for ZiweiOracle single-call inline-marker pipeline (fake Anthropic client)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.services.ziwei.oracle import ZiweiOracle
from app.services.ziwei.oracle_tools import parse_markers


# ────────────────────────────────────────────────────────────────
# Helpers: minimal chart_json factory (mirrors _mk from test_ziwei_patterns_batch1.py)
# ────────────────────────────────────────────────────────────────

def _mk(palaces_spec: dict, ming: str = "子", shen: str = "午") -> dict:
    """Build a minimal chart_json dict.  palaces_spec: {地支: ([(star, mutagen, brightness)], [minor_names])}"""
    order = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    start = branches.index(ming)
    rot = branches[start:] + branches[:start]
    palaces = []
    for i, name in enumerate(order):
        br = rot[i]
        majors, minors = palaces_spec.get(br, ([], []))
        palaces.append({
            "name": name,
            "earthlyBranch": br,
            "heavenlyStem": "甲",
            "majorStars": [{"name": n, "type": "major", "mutagen": m, "brightness": b} for (n, m, b) in majors],
            "minorStars": [{"name": n, "type": "soft"} for n in minors],
            "adjectiveStars": [],
            "isBodyPalace": False,
            "isOriginalPalace": False,
            "changsheng12": "长生",
            "decadal": {"range": [1, 10], "heavenlyStem": "甲", "earthlyBranch": br},
            "ages": [],
        })
    return {
        "earthlyBranchOfSoulPalace": ming,
        "earthlyBranchOfBodyPalace": shen,
        "palaces": palaces,
        "gender": "男",
        "solarDate": "1990-01-01",
        "lunarDate": "己巳年腊月初五",
        "time": "子时",
        "fiveElementsClass": "水二局",
        "soul": "贪狼",
        "body": "文昌",
        "zodiac": "蛇",
        "sign": "摩羯座",
    }


# ────────────────────────────────────────────────────────────────
# Fake Anthropic SDK objects (single-call)
# ────────────────────────────────────────────────────────────────

def _fake_response(text: str, in_tok: int = 200, out_tok: int = 120) -> Any:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


class FakeClient:
    def __init__(self, response: Any):
        self._response = response
        self.calls: list[dict] = []

    class _Messages:
        def __init__(self, outer: "FakeClient"):
            self._o = outer

        def create(self, **kwargs: Any) -> Any:
            self._o.calls.append(kwargs)
            r = self._o._response
            if isinstance(r, Exception):
                raise r
            return r

    @property
    def messages(self) -> "_Messages":
        return self._Messages(self)


SIMPLE_CHART = _mk({"子": ([("紫微", None, "庙")], [])})
SIMPLE_MESSAGES = [{"role": "user", "content": "帮我解盘"}]


def test_parse_markers_focus_overview_term():
    text = "开场。[[overview]] 你命宫紫微。[[focus:命宫]] 这是机月同梁格[[term:机月同梁格|稳健务实之格]]，宜稳。"
    response, segments, cams = parse_markers(text)
    assert "[[" not in response  # markers stripped from prose
    assert cams == [
        {"type": "overview"},
        {"type": "focus_palace", "palace": "命宫"},
        {"type": "explain_term", "term": "机月同梁格", "explanation": "稳健务实之格"},
    ]
    # segments group text-before-marker with that marker's command
    assert segments[0]["commands"] == [{"type": "overview"}]
    assert "命宫紫微" in segments[1]["text"] and segments[1]["commands"][0]["type"] == "focus_palace"


def test_parse_markers_friends_palace_alias_and_invalid_dropped():
    text = "看交友。[[focus:交友]] 乱写[[focus:火星宫]] 结束。"
    _, _, cams = parse_markers("看交友。[[focus:交友]] 结束。")
    assert cams == [{"type": "focus_palace", "palace": "仆役"}]  # 交友→仆役
    _, _, cams2 = parse_markers(text)
    assert cams2 == [{"type": "focus_palace", "palace": "仆役"}]  # 火星宫 invalid → dropped


def test_parse_markers_no_markers():
    response, segments, cams = parse_markers("纯文字没有标记。")
    assert response == "纯文字没有标记。"
    assert segments == [{"text": "纯文字没有标记。", "commands": []}]
    assert cams == []


def test_oracle_single_call_returns_segments_and_commands():
    client = FakeClient(_fake_response("命宫紫微，气象不凡。[[focus:命宫]] 宜走高位。", in_tok=300, out_tok=150))
    oracle = ZiweiOracle(client=client, model="claude-test")
    result = oracle.run(chart_json=SIMPLE_CHART, persona="sage", scenario="natal", portrait={}, messages=SIMPLE_MESSAGES)
    assert result is not None
    assert len(client.calls) == 1  # SINGLE call
    assert "tools" not in client.calls[0]  # no tools
    assert "[[" not in result["response"]
    assert result["camera_commands"] == [{"type": "focus_palace", "palace": "命宫"}]
    assert len(result["segments"]) == 2
    assert result["_meta"]["input_tokens"] == 300 and result["_meta"]["rounds"] == 1


def test_oracle_system_prompt_includes_summary_persona_and_markers():
    chart = _mk({"子": ([("紫微", None, "庙")], []), "辰": ([], ["左辅"]), "申": ([], ["右弼"])})
    client = FakeClient(_fake_response("解读完毕。"))
    oracle = ZiweiOracle(client=client, model="claude-test")
    oracle.run(chart_json=chart, persona="taoist", scenario="natal", portrait={}, messages=SIMPLE_MESSAGES)
    system = client.calls[0]["system"]
    assert "水二局" in system  # chart summary
    assert "君臣庆会" in system  # detected pattern
    assert "命主" in system  # taoist persona
    assert "[[focus:" in system  # marker instructions


def test_oracle_returns_none_on_exception():
    client = FakeClient(Exception("boom"))
    oracle = ZiweiOracle(client=client, model="claude-test")
    assert oracle.run(chart_json=SIMPLE_CHART, persona="sage", scenario="natal", portrait={}, messages=SIMPLE_MESSAGES) is None
