"""Tests for ZiweiOracle tool_use loop (fake Anthropic client, no real API)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.ziwei.oracle import ZiweiOracle
from app.services.ziwei.oracle_tools import execute_tool


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
# Fake Anthropic SDK objects
# ────────────────────────────────────────────────────────────────

def _fake_usage(input_tokens: int = 100, output_tokens: int = 50) -> Any:
    return SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)


def _fake_tool_use_block(name: str, tool_input: dict, block_id: str = "t1") -> Any:
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def _fake_text_block(text: str) -> Any:
    return SimpleNamespace(type="text", text=text)


def _fake_response(stop_reason: str, content: list, in_tok: int = 100, out_tok: int = 50) -> Any:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
        usage=_fake_usage(in_tok, out_tok),
    )


class FakeClient:
    """Fake Anthropic client that returns pre-configured responses in sequence."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self._call_index = 0
        self.calls: list[dict] = []  # record kwargs for each call

    class _Messages:
        def __init__(self, outer: "FakeClient"):
            self._outer = outer

        def create(self, **kwargs) -> Any:
            self._outer.calls.append(kwargs)
            idx = self._outer._call_index
            self._outer._call_index += 1
            resp = self._outer._responses[idx]
            if isinstance(resp, Exception):
                raise resp
            return resp

    @property
    def messages(self) -> "_Messages":
        return self._Messages(self)


# ────────────────────────────────────────────────────────────────
# Minimal valid inputs
# ────────────────────────────────────────────────────────────────

SIMPLE_CHART = _mk({"子": ([("紫微", None, "庙")], [])})
SIMPLE_MESSAGES = [{"role": "user", "content": "帮我解盘"}]


# ────────────────────────────────────────────────────────────────
# Test 1: tool_use round → text round, camera command collected
# ────────────────────────────────────────────────────────────────

def test_oracle_collects_camera_command_and_returns_text():
    tool_resp = _fake_response(
        stop_reason="tool_use",
        content=[_fake_tool_use_block("focus_palace", {"palace": "官禄"}, "t1")],
        in_tok=120, out_tok=30,
    )
    text_resp = _fake_response(
        stop_reason="end_turn",
        content=[_fake_text_block("官禄宫武曲……")],
        in_tok=150, out_tok=80,
    )
    client = FakeClient([tool_resp, text_resp])
    oracle = ZiweiOracle(client=client, model="claude-test")

    result = oracle.run(
        chart_json=SIMPLE_CHART,
        persona="sage",
        scenario="natal",
        portrait={},
        messages=SIMPLE_MESSAGES,
    )

    assert result is not None
    assert result["response"] == "官禄宫武曲……"
    assert result["camera_commands"] == [{"type": "focus_palace", "palace": "官禄"}]
    assert result["_meta"]["rounds"] == 2
    # tokens summed across both calls: 120+150=270 in, 30+80=110 out
    assert result["_meta"]["input_tokens"] == 270
    assert result["_meta"]["output_tokens"] == 110
    assert result["_meta"]["total_tokens"] == 380


# ────────────────────────────────────────────────────────────────
# Test 2: system prompt includes chart summary, pattern name, and persona phrase
# ────────────────────────────────────────────────────────────────

def test_oracle_system_prompt_includes_summary_and_persona():
    # 君臣庆会: 紫微 in 命宫(子), 左辅 in 辰(三方), 右弼 in 申(三方)
    chart = _mk({
        "子": ([("紫微", None, "庙")], []),
        "辰": ([], ["左辅"]),
        "申": ([], ["右弼"]),
    })
    # We only need one text response; system prompt is built before the call
    text_resp = _fake_response(
        stop_reason="end_turn",
        content=[_fake_text_block("解读完毕")],
    )
    client = FakeClient([text_resp])
    oracle = ZiweiOracle(client=client, model="claude-test")

    oracle.run(
        chart_json=chart,
        persona="taoist",
        scenario="natal",
        portrait={},
        messages=SIMPLE_MESSAGES,
    )

    assert len(client.calls) == 1
    system = client.calls[0]["system"]

    # Chart summary includes the 五行局 value
    assert "水二局" in system

    # Pattern section includes 君臣庆会
    assert "君臣庆会" in system

    # Taoist persona uses "命主"
    assert "命主" in system


# ────────────────────────────────────────────────────────────────
# Test 3: exception from client → run returns None
# ────────────────────────────────────────────────────────────────

def test_oracle_returns_none_on_exception():
    client = FakeClient([Exception("connection error")])
    oracle = ZiweiOracle(client=client, model="claude-test")

    result = oracle.run(
        chart_json=SIMPLE_CHART,
        persona="sage",
        scenario="natal",
        portrait={},
        messages=SIMPLE_MESSAGES,
    )

    assert result is None


# ────────────────────────────────────────────────────────────────
# Test 4: invalid palace not added to camera_commands, loop continues to text
# ────────────────────────────────────────────────────────────────

def test_oracle_invalid_palace_not_collected():
    # First call: tool_use with invalid palace "火星宫"
    tool_resp = _fake_response(
        stop_reason="tool_use",
        content=[_fake_tool_use_block("focus_palace", {"palace": "火星宫"}, "t_bad")],
        in_tok=100, out_tok=20,
    )
    # Second call: text response
    text_resp = _fake_response(
        stop_reason="end_turn",
        content=[_fake_text_block("综合论断如下……")],
        in_tok=110, out_tok=60,
    )
    client = FakeClient([tool_resp, text_resp])
    oracle = ZiweiOracle(client=client, model="claude-test")

    result = oracle.run(
        chart_json=SIMPLE_CHART,
        persona="sage",
        scenario="natal",
        portrait={},
        messages=SIMPLE_MESSAGES,
    )

    assert result is not None
    # Invalid palace must NOT be in camera_commands
    assert result["camera_commands"] == []
    # Loop continued and returned the text
    assert result["response"] == "综合论断如下……"
    assert result["_meta"]["rounds"] == 2


# ────────────────────────────────────────────────────────────────
# Test 5: a question that keeps calling focus_palace must still return text —
# the final round drops tools, forcing a text answer instead of None (the prod
# 502 bug: multi-palace questions exhausted the tool_use rounds before answering).
# ────────────────────────────────────────────────────────────────

def test_oracle_forces_text_on_final_round_when_tools_exhausted():
    class GreedyToolClient:
        """Returns tool_use whenever tools are offered; text once tools are withheld."""

        def __init__(self) -> None:
            self.calls: list[dict] = []

        class _Messages:
            def __init__(self, outer: "GreedyToolClient") -> None:
                self._outer = outer

            def create(self, **kwargs: Any) -> Any:
                self._outer.calls.append(kwargs)
                if "tools" in kwargs:
                    return _fake_response(
                        stop_reason="tool_use",
                        content=[_fake_tool_use_block("focus_palace", {"palace": "官禄"}, f"t{len(self._outer.calls)}")],
                    )
                return _fake_response(stop_reason="end_turn", content=[_fake_text_block("综合来看，事业宜……")])

        @property
        def messages(self) -> "_Messages":
            return self._Messages(self)

    client = GreedyToolClient()
    oracle = ZiweiOracle(client=client, model="claude-test")

    result = oracle.run(
        chart_json=SIMPLE_CHART,
        persona="sage",
        scenario="natal",
        portrait={},
        messages=[{"role": "user", "content": "事业方向？"}],
    )

    assert result is not None  # must NOT return None despite greedy tool calls
    assert result["response"] == "综合来看，事业宜……"
    # default max_rounds=6: rounds 1-5 offer tools, round 6 drops tools → forced text
    assert len(client.calls) == 6
    assert "tools" in client.calls[0]
    assert "tools" not in client.calls[-1]
    assert result["camera_commands"]  # focus_palace commands collected along the way
    assert result["_meta"]["rounds"] == 6
