"""内部命盘表示 + iztro chart_json 适配器（供格局检测使用）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

BRANCH_NAMES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
BRANCH_INDEX = {name: i for i, name in enumerate(BRANCH_NAMES)}

_BRIGHTNESS_MAP = {"庙": "bright", "旺": "bright", "得": "normal", "利": "normal", "平": "normal", "不": "dim", "陷": "dim"}


@dataclass
class Star:
    name: str
    is_major: bool
    mutagen: Optional[str] = None  # 禄|权|科|忌|None
    brightness: str = "normal"  # bright|normal|dim


@dataclass
class Palace:
    name: str  # 命宫..父母
    branch: int  # 0-11
    stars: list[Star] = field(default_factory=list)


@dataclass
class Chart:
    ming_branch: int
    shen_branch: int
    palaces: list[Palace]


def branch_to_int(branch: str) -> int:
    return BRANCH_INDEX[branch]


def adapt_chart(chart_json: dict) -> Chart:
    """iztro chart_json(dict) → 内部 Chart。majorStars→is_major=True，其余 False。"""
    palaces: list[Palace] = []
    for pj in chart_json.get("palaces", []):
        stars: list[Star] = []
        for sj in pj.get("majorStars", []):
            stars.append(_adapt_star(sj, is_major=True))
        for sj in pj.get("minorStars", []) + pj.get("adjectiveStars", []):
            stars.append(_adapt_star(sj, is_major=False))
        palaces.append(Palace(name=pj["name"], branch=branch_to_int(pj["earthlyBranch"]), stars=stars))
    return Chart(
        ming_branch=branch_to_int(chart_json["earthlyBranchOfSoulPalace"]),
        shen_branch=branch_to_int(chart_json["earthlyBranchOfBodyPalace"]),
        palaces=palaces,
    )


def _adapt_star(sj: dict, is_major: bool) -> Star:
    raw_brightness = sj.get("brightness") or ""
    return Star(
        name=sj["name"],
        is_major=is_major,
        mutagen=sj.get("mutagen") or None,
        brightness=_BRIGHTNESS_MAP.get(raw_brightness, "normal"),
    )
