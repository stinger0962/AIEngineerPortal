"""格局检测（移植 Renhuai123/ziwei-doushu lib/ziwei/patterns.ts，MIT，署名 紫微研究）。
作用于内部 Chart（见 chart_model.py）。每个 Pattern 自带古籍出处 source。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from .chart_model import Chart, Palace
from .primitives import (
    SHA_HARD, SHA_KONG, find_star_palace, has_sha_in_palace, has_star, jia_palaces,
    major_star_names, ming_palace, san_fang_all_stars, san_fang_mutagens, san_fang_palaces,
    san_fang_sha_count, star_mutagen, is_bright, is_dim,
)


@dataclass
class Pattern:
    name: str
    level: str  # excellent|good|neutral|caution
    description: str
    palaces: list[str]
    source: str = ""
    required: list[str] = field(default_factory=list)
    bonus: list[str] = field(default_factory=list)
    breaking: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ───────── 主星 / 三方 / 四化格局 ─────────

def detect_jun_chen_qing_hui(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    if not has_star(ming, "紫微"):
        return
    sf = san_fang_all_stars(chart)
    if "左辅" not in sf or "右弼" not in sf:
        return
    bonus, breaking = [], []
    if "文昌" in sf or "文曲" in sf:
        bonus.append("再会文昌或文曲")
    if "天魁" in sf or "天钺" in sf:
        bonus.append("魁钺贵人加照")
    if star_mutagen(ming, "紫微") == "权":
        bonus.append("紫微化权")
    if san_fang_sha_count(chart, SHA_KONG) >= 2:
        breaking.append("地空地劫双夹会照（紫微忌空劫）")
    out.append(Pattern(
        name="君臣庆会",
        level="good" if breaking else "excellent",
        description="紫微入命，左辅右弼同会，帝王得贤臣辅佐，主大富大贵、统御之命。一生贵人不绝，宜走政商高位、跨界领袖之途。",
        palaces=["命宫"], source="《紫微斗数全书·君臣庆会格》",
        required=["紫微入命", "左辅右弼同会三方四正"], bonus=bonus, breaking=breaking,
    ))


def detect_sha_po_lang(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    sf = san_fang_all_stars(chart)
    has = [s for s in ("七杀", "破军", "贪狼") if s in sf]
    if len(has) < 3:
        return
    bonus, breaking = [], []
    mut = san_fang_mutagens(chart)
    if "禄" in mut or "权" in mut:
        bonus.append("三方有化禄或化权（动得有力）")
    if "左辅" in sf and "右弼" in sf:
        bonus.append("辅弼同会（变动中得贵人）")
    if san_fang_sha_count(chart, SHA_HARD) >= 3:
        breaking.append("煞星过重（动而无成）")
    if has_sha_in_palace(ming, SHA_KONG):
        breaking.append("命坐空劫（动得辛苦）")
    out.append(Pattern(
        name="杀破狼",
        level="caution" if breaking else "good",
        description="七杀、破军、贪狼三星会命，开创闯荡之命格。一生变动多、不甘平凡，宜创业、军警、业务、销售。中年后才能稳定守成，年轻时易因冲动失利。",
        palaces=[p.name for p in san_fang_palaces(chart) if major_star_names(p) and major_star_names(p)[0] in has],
        source="《紫微斗数全书·杀破狼》",
        required=["七杀、破军、贪狼三星齐入命宫三方四正"], bonus=bonus, breaking=breaking,
    ))


def detect_yang_liang_chang_lu(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    sf = san_fang_all_stars(chart)
    if not ({"太阳", "天梁", "文昌", "禄存"} <= sf):
        return
    sun = find_star_palace(chart, "太阳")
    liang = find_star_palace(chart, "天梁")
    bonus, breaking = [], []
    if sun and is_bright(sun, "太阳"):
        bonus.append("太阳庙旺")
    if liang and is_bright(liang, "天梁"):
        bonus.append("天梁庙旺")
    if "科" in san_fang_mutagens(chart):
        bonus.append("再会化科")
    if sun and is_dim(sun, "太阳"):
        breaking.append("太阳落陷（阳梁失辉）")
    if san_fang_sha_count(chart, SHA_HARD) >= 2:
        breaking.append("三方煞重")
    out.append(Pattern(
        name="阳梁昌禄",
        level="good" if breaking else "excellent",
        description='太阳、天梁、文昌、禄存四星齐会命宫三方，号称"科举之星"，主清贵显达、考运极佳，宜走学术、文教、研究、专业认证之路，一生功名易就。',
        palaces=[p.name for p in (sun, liang) if p], source="《紫微斗数全书·阳梁昌禄格》",
        required=["太阳会命宫三方", "天梁会命宫三方", "文昌会命宫三方", "禄存会命宫三方"],
        bonus=bonus, breaking=breaking,
    ))


def detect_san_qi_jia_hui(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    mut = san_fang_mutagens(chart)
    if not ({"禄", "权", "科"} <= mut):
        return
    out.append(Pattern(
        name="三奇加会", level="excellent",
        description='化禄、化权、化科三吉化齐会命宫三方四正，号称"三奇加会"。主一生功名、财富、贵人三全，是紫微斗数最高吉格之一。',
        palaces=[p.name for p in san_fang_palaces(chart)], source="《紫微斗数全书·三奇加会》",
        required=["化禄、化权、化科三吉化齐会命宫三方四正"],
    ))


# 占位：Task 4 追加下半检测器并填充 detect_patterns 的完整调用序列
def detect_patterns(chart: Chart) -> list[Pattern]:
    ming = ming_palace(chart)
    if not ming:
        return []
    out: list[Pattern] = []
    detect_jun_chen_qing_hui(chart, ming, out)
    detect_sha_po_lang(chart, ming, out)
    detect_yang_liang_chang_lu(chart, ming, out)
    detect_san_qi_jia_hui(chart, ming, out)
    return out
