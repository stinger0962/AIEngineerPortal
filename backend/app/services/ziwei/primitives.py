"""格局检测原语：地支环math、三方四正、夹、对宫、煞计数、四化读取。
忠实移植 Renhuai123/ziwei-doushu lib/ziwei/patterns.ts 的 helper（MIT，署名 紫微研究）。"""
from __future__ import annotations

from typing import Optional

from .chart_model import Chart, Palace, Star

SHA_NAMES = ["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"]
SHA_HARD = ["擎羊", "陀罗", "火星", "铃星"]
SHA_KONG = ["地空", "地劫"]


def major_star_names(palace: Palace) -> list[str]:
    return [s.name for s in palace.stars if s.is_major]


def find_star(palace: Palace, name: str) -> Optional[Star]:
    return next((s for s in palace.stars if s.name == name), None)


def has_star(palace: Palace, name: str) -> bool:
    return any(s.name == name for s in palace.stars)


def find_star_palace(chart: Chart, name: str) -> Optional[Palace]:
    return next((p for p in chart.palaces if any(s.name == name for s in p.stars)), None)


def palace_by_branch(chart: Chart, branch: int) -> Optional[Palace]:
    b = ((branch % 12) + 12) % 12
    return next((p for p in chart.palaces if p.branch == b), None)


def ming_palace(chart: Chart) -> Optional[Palace]:
    return palace_by_branch(chart, chart.ming_branch)


def sha_count_in_palace(palace: Palace, sha_list: list[str] = SHA_HARD) -> int:
    return sum(1 for s in palace.stars if s.name in sha_list)


def has_sha_in_palace(palace: Palace, sha_list: list[str] = SHA_NAMES) -> bool:
    return any(s.name in sha_list for s in palace.stars)


def san_fang_palaces(chart: Chart) -> list[Palace]:
    m = chart.ming_branch
    branches = {m, (m + 4) % 12, (m + 8) % 12, (m + 6) % 12}
    return [p for p in chart.palaces if p.branch in branches]


def is_in_san_fang(chart: Chart, branch: int) -> bool:
    m = chart.ming_branch
    return branch in {m, (m + 4) % 12, (m + 8) % 12, (m + 6) % 12}


def dui_gong(chart: Chart, branch: int) -> Optional[Palace]:
    return palace_by_branch(chart, (branch + 6) % 12)


def jia_palaces(chart: Chart, branch: int) -> tuple[Optional[Palace], Optional[Palace]]:
    """返回 (prev, next) = (branch-1, branch+1) 两宫。"""
    return palace_by_branch(chart, (branch + 11) % 12), palace_by_branch(chart, (branch + 1) % 12)


def san_fang_all_stars(chart: Chart) -> set[str]:
    return {s.name for p in san_fang_palaces(chart) for s in p.stars}


def san_fang_mutagens(chart: Chart) -> set[str]:
    """三方四正中出现的四化集合。移植 `sanFangSet.has('化禄')` 用：'禄' in san_fang_mutagens(chart)。"""
    return {s.mutagen for p in san_fang_palaces(chart) for s in p.stars if s.mutagen}


def san_fang_sha_count(chart: Chart, sha_list: list[str] = SHA_HARD) -> int:
    return sum(sha_count_in_palace(p, sha_list) for p in san_fang_palaces(chart))


def is_bright(palace: Palace, star_name: str) -> bool:
    s = find_star(palace, star_name)
    return s is not None and s.brightness == "bright"


def is_dim(palace: Palace, star_name: str) -> bool:
    s = find_star(palace, star_name)
    return s is not None and s.brightness == "dim"


def star_mutagen(palace: Palace, star_name: str) -> Optional[str]:
    s = find_star(palace, star_name)
    return s.mutagen if s else None
