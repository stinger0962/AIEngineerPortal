from app.services.ziwei.chart_model import adapt_chart
from app.services.ziwei.patterns import detect_patterns


def _mk(palaces_spec, ming="子", shen="午"):
    """palaces_spec: {地支: ([(主星,四化,亮度)], [辅星名])}; 自动补满12宫。order[0]=命宫 落在 ming 地支。"""
    order = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    start = branches.index(ming)
    rot = branches[start:] + branches[:start]
    palaces = []
    for i, name in enumerate(order):
        br = rot[i]
        majors, minors = palaces_spec.get(br, ([], []))
        palaces.append({
            "name": name, "earthlyBranch": br, "heavenlyStem": "甲",
            "majorStars": [{"name": n, "type": "major", "mutagen": m, "brightness": b} for (n, m, b) in majors],
            "minorStars": [{"name": n, "type": "soft"} for n in minors],
            "adjectiveStars": [], "isBodyPalace": False, "isOriginalPalace": False,
            "changsheng12": "长生", "decadal": {"range": [1, 10], "heavenlyStem": "甲", "earthlyBranch": br}, "ages": [],
        })
    return {"earthlyBranchOfSoulPalace": ming, "earthlyBranchOfBodyPalace": shen, "palaces": palaces}


def _patterns(chart_json):
    return detect_patterns(adapt_chart(chart_json))


def _names(chart_json):
    return {p.name for p in _patterns(chart_json)}


# ── 原始 4 个测试 ────────────────────────────────────────────────────

def test_jun_chen_qing_hui_hit():
    cj = _mk({"子": ([("紫微", None, "庙")], []), "辰": ([], ["左辅"]), "申": ([], ["右弼"])})
    assert "君臣庆会" in _names(cj)


def test_jun_chen_qing_hui_miss_without_fubi():
    cj = _mk({"子": ([("紫微", None, "庙")], [])})
    assert "君臣庆会" not in _names(cj)


def test_san_qi_jia_hui_hit():
    cj = _mk({"子": ([("紫微", "权", "庙")], []), "辰": ([("武曲", "禄", "得")], []), "申": ([("文昌", "科", "得")], [])})
    assert "三奇加会" in _names(cj)


def test_sha_po_lang_hit():
    cj = _mk({"子": ([("七杀", None, "庙")], []), "辰": ([("破军", None, "旺")], []), "申": ([("贪狼", None, "平")], [])})
    assert "杀破狼" in _names(cj)


# ── 4 个追加测试 ─────────────────────────────────────────────────────

# 三方四正 for 命宫 at 子(0): 子(命宫), 辰(财帛), 申(官禄), 午(迁移)

def test_sha_po_lang_miss_incomplete():
    """只有七杀和破军在三方，缺贪狼 → 不触发杀破狼。"""
    cj = _mk({
        "子": ([("七杀", None, "庙")], []),
        "辰": ([("破军", None, "旺")], []),
        # 贪狼不在三方四正（放在丑，属兄弟宫，不在三方）
        "丑": ([("贪狼", None, "平")], []),
    })
    assert "杀破狼" not in _names(cj)


def test_yang_liang_chang_lu_miss_no_luru():
    """太阳、天梁、文昌 在三方，但缺禄存 → 不触发阳梁昌禄。"""
    cj = _mk({
        "子": ([("太阳", None, "庙")], []),
        "辰": ([("天梁", None, "旺")], []),
        "申": ([], ["文昌"]),
        # 禄存不在三方四正 → 条件不满足
    })
    assert "阳梁昌禄" not in _names(cj)


def test_san_qi_jia_hui_miss_only_two_mutagens():
    """只有化禄和化权在三方，缺化科 → 不触发三奇加会。"""
    cj = _mk({
        "子": ([("紫微", "权", "庙")], []),
        "辰": ([("武曲", "禄", "得")], []),
        # 无化科星在三方四正
        "申": ([("天府", None, "旺")], []),
    })
    assert "三奇加会" not in _names(cj)


def test_jun_chen_qing_hui_downgrade_with_kong_jie():
    """紫微入命 + 左辅右弼 + 地空地劫双入三方 → 君臣庆会触发但降为 good。"""
    # 地空放辰(财帛)，地劫放申(官禄)，都在三方四正内
    cj = _mk({
        "子": ([("紫微", None, "庙")], []),
        "辰": ([], ["左辅", "地空"]),
        "申": ([], ["右弼", "地劫"]),
    })
    patterns = _patterns(cj)
    names = {p.name for p in patterns}
    assert "君臣庆会" in names
    jun_chen = next(p for p in patterns if p.name == "君臣庆会")
    assert jun_chen.level == "good"
