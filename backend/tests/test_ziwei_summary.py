"""Tests for personas.py and chart_summary.py (Phase 3a Task 5)."""
from app.services.ziwei.personas import persona_prompt, PERSONAS, DEFAULT_PERSONA
from app.services.ziwei.chart_summary import format_chart_summary


# ──────────────────────────────────────────────────────────────────────────────
# Helpers (mirrors _mk from test_ziwei_patterns_batch1.py)
# ──────────────────────────────────────────────────────────────────────────────

def _mk(palaces_spec, ming="子", shen="午",
        gender="男", solar="2000-01-01", lunar="腊月廿五",
        time="子时", five_class="水二局", soul="文昌", body="天机",
        zodiac="龙", sign="摩羯"):
    """Build a minimal iztro-shaped chart_json dict for testing."""
    order = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    start = branches.index(ming)
    rot = branches[start:] + branches[:start]
    palaces = []
    for i, name in enumerate(order):
        br = rot[i]
        majors_raw, minors_raw = palaces_spec.get(br, ([], []))
        is_body = br == shen
        palaces.append({
            "name": name,
            "earthlyBranch": br,
            "heavenlyStem": "甲",
            "majorStars": [
                {"name": n, "type": "major", "mutagen": m, "brightness": b}
                for (n, m, b) in majors_raw
            ],
            "minorStars": [{"name": n, "type": "soft", "mutagen": None, "brightness": ""} for n in minors_raw],
            "adjectiveStars": [],
            "isBodyPalace": is_body,
            "isOriginalPalace": False,
        })
    return {
        "earthlyBranchOfSoulPalace": ming,
        "earthlyBranchOfBodyPalace": shen,
        "gender": gender,
        "solarDate": solar,
        "lunarDate": lunar,
        "time": time,
        "fiveElementsClass": five_class,
        "soul": soul,
        "body": body,
        "zodiac": zodiac,
        "sign": sign,
        "palaces": palaces,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: personas — three distinct, fallback to sage
# ──────────────────────────────────────────────────────────────────────────────

def test_personas_three_distinct():
    sage_p = persona_prompt("sage")
    taoist_p = persona_prompt("taoist")
    analyst_p = persona_prompt("analyst")

    # Each is non-empty
    assert sage_p and len(sage_p) > 10
    assert taoist_p and len(taoist_p) > 10
    assert analyst_p and len(analyst_p) > 10

    # All three are distinct
    assert sage_p != taoist_p
    assert sage_p != analyst_p
    assert taoist_p != analyst_p

    # Unknown key falls back to sage's prompt
    assert persona_prompt("unknown") == sage_p
    assert persona_prompt("") == sage_p
    assert persona_prompt("wizard") == sage_p


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: summary contains basics and palace info
# ──────────────────────────────────────────────────────────────────────────────

def test_summary_contains_basics_and_palaces():
    # 命宫子: 紫微庙化权, 迁移午: body palace
    cj = _mk(
        {
            "子": ([("紫微", "权", "庙")], []),
            "辰": ([("天机", None, "旺")], []),
        },
        ming="子", shen="午",
        gender="女", five_class="水二局", soul="文昌", body="天机",
    )
    result = format_chart_summary(cj)

    # Basic section present
    assert "【基本】" in result
    assert "女" in result
    assert "水二局" in result

    # Palaces section present
    assert "【十二宫】" in result

    # Palace name present
    assert "命宫" in result

    # Star with brightness + 化mutagen: 紫微庙化权
    assert "紫微庙化权" in result

    # Body palace marker (迁移 is shen=午)
    assert "·身" in result


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: summary includes a hit pattern (君臣庆会)
# ──────────────────────────────────────────────────────────────────────────────

def test_summary_includes_hit_pattern():
    # 君臣庆会: 紫微入命(子), 左辅在辰(三方财帛), 右弼在申(三方官禄)
    # 三方四正 for 命宫子(0): 子(0), 辰(4), 申(8), 午(6)
    cj = _mk(
        {
            "子": ([("紫微", None, "庙")], []),   # 命宫: 紫微
            "辰": ([], ["左辅"]),                  # 财帛: 左辅 (minor)
            "申": ([], ["右弼"]),                  # 官禄: 右弼 (minor)
        },
        ming="子", shen="午",
    )
    result = format_chart_summary(cj)

    assert "【命中格局】" in result
    assert "君臣庆会" in result
    assert "《紫微斗数全书·君臣庆会格》" in result


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: no-pattern branch → 无显著格局
# ──────────────────────────────────────────────────────────────────────────────

def test_summary_no_pattern_branch():
    # Sparse chart: only 天同 in 命宫, nothing that triggers any pattern
    cj = _mk(
        {
            "子": ([("天同", None, "平")], []),
        },
        ming="子", shen="午",
    )
    result = format_chart_summary(cj)

    assert "【命中格局】" in result
    assert "无显著格局" in result
