"""把 iztro chart_json + 命中格局格式化为紧凑中文摘要，注入 oracle system prompt。"""
from __future__ import annotations

from .chart_model import adapt_chart
from .patterns import detect_patterns


def _star_str(star: dict) -> str:
    s = star["name"]
    if star.get("brightness"):
        s += star["brightness"]
    if star.get("mutagen"):
        s += f"化{star['mutagen']}"
    return s


def format_chart_summary(chart_json: dict) -> str:
    lines: list[str] = []
    lines.append(
        f"【基本】{chart_json.get('gender','')} · 公历{chart_json.get('solarDate','')} · 农历{chart_json.get('lunarDate','')}"
        f" · {chart_json.get('time','')} · 五行局{chart_json.get('fiveElementsClass','')}"
        f" · 命主{chart_json.get('soul','')}身主{chart_json.get('body','')}"
        f" · 生肖{chart_json.get('zodiac','')}星座{chart_json.get('sign','')}"
    )
    lines.append("【十二宫】")
    for p in chart_json.get("palaces", []):
        majors = "、".join(_star_str(s) for s in p.get("majorStars", [])) or "（空宫）"
        minors = "、".join(_star_str(s) for s in p.get("minorStars", []))
        body = "·身" if p.get("isBodyPalace") else ""
        seg = f"  {p['name']}{body}（{p.get('heavenlyStem','')}{p.get('earthlyBranch','')}）：{majors}"
        if minors:
            seg += f"；辅佐：{minors}"
        lines.append(seg)

    patterns = detect_patterns(adapt_chart(chart_json))
    if patterns:
        lines.append("【命中格局】（确定性规则检测，含古籍出处）")
        for pat in patterns:
            extras = []
            if pat.bonus:
                extras.append("加分：" + "、".join(pat.bonus))
            if pat.breaking:
                extras.append("破格：" + "、".join(pat.breaking))
            tail = f"（{'；'.join(extras)}）" if extras else ""
            lines.append(f"  ▸ {pat.name}［{pat.level}］{pat.source}{tail}：{pat.description}")
    else:
        lines.append("【命中格局】无显著格局（以星曜本性与三方四正综合论之）")
    return "\n".join(lines)
