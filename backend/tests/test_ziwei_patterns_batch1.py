"""Batch 1 格局检测器测试（18 个 detector 的 HIT + 部分 MISS）。

三方四正 for 命宫 at 子(0): 子(命宫/0), 辰(财帛/4), 申(官禄/8), 午(迁移/6)。
夹宫 for 命宫 at 子(0): prev=亥(父母/11), next=丑(兄弟/1)。
"""
from app.services.ziwei.chart_model import adapt_chart
from app.services.ziwei.primitives import ming_palace
from app.services.ziwei.patterns import (
    detect_zi_fu, detect_fu_xiang_chao_yuan, detect_huo_tan_ling_tan, detect_wu_tan,
    detect_ji_yue_tong_liang, detect_lian_xiang, detect_wu_qi_sha, detect_tong_liang,
    detect_ri_yue_tong_gong, detect_ri_yue_jia_ming, detect_ju_ri_tong_gong,
    detect_shi_zhong_yin_yu, detect_ming_zhu_chu_hai, detect_zi_wei_in_ming,
    detect_fu_bi_jia_ming, detect_chang_qu_jia_ming, detect_kui_yue_jia_ming,
    detect_shuang_lu_chao_yuan,
)


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


def _run(detector, chart_json, with_ming=True):
    chart = adapt_chart(chart_json)
    out = []
    if with_ming:
        detector(chart, ming_palace(chart), out)
    else:
        detector(chart, out)
    return out


def _names(out):
    return {p.name for p in out}


# ── 1. 紫府同宫 ──────────────────────────────────────────────────
def test_zi_fu_hit_in_ming():
    cj = _mk({"子": ([("紫微", None, "庙"), ("天府", None, "旺")], [])})
    out = _run(detect_zi_fu, cj)
    assert "紫府同宫" in _names(out)
    assert next(p for p in out if p.name == "紫府同宫").level == "excellent"


def test_zi_fu_hit_not_in_ming_good():
    # 紫微+天府同在辰(财帛宫)，不在命宫 → good
    cj = _mk({"辰": ([("紫微", None, "庙"), ("天府", None, "旺")], [])})
    out = _run(detect_zi_fu, cj)
    assert "紫府同宫" in _names(out)
    assert next(p for p in out if p.name == "紫府同宫").level == "good"


def test_zi_fu_miss_different_palace():
    cj = _mk({"子": ([("紫微", None, "庙")], []), "辰": ([("天府", None, "旺")], [])})
    assert "紫府同宫" not in _names(_run(detect_zi_fu, cj))


# ── 2. 府相朝垣 ──────────────────────────────────────────────────
def test_fu_xiang_chao_yuan_hit():
    # 天府在辰(三方)，天相在申(三方)，命宫子无两星
    cj = _mk({"辰": ([("天府", None, "旺")], []), "申": ([("天相", None, "得")], [])})
    out = _run(detect_fu_xiang_chao_yuan, cj)
    assert "府相朝垣" in _names(out)


def test_fu_xiang_chao_yuan_miss_same_palace():
    cj = _mk({"辰": ([("天府", None, "旺"), ("天相", None, "得")], [])})
    assert "府相朝垣" not in _names(_run(detect_fu_xiang_chao_yuan, cj))


# ── 3. 火贪格 / 铃贪格 ───────────────────────────────────────────
def test_huo_tan_hit_same_palace():
    cj = _mk({"子": ([("贪狼", None, "庙")], ["火星"])})
    out = _run(detect_huo_tan_ling_tan, cj)
    assert "火贪格" in _names(out)


def test_ling_tan_hit_trine():
    # 贪狼在子(命宫/三方)，铃星在辰(三方=子+4)
    cj = _mk({"子": ([("贪狼", None, "庙")], []), "辰": ([], ["铃星"])})
    out = _run(detect_huo_tan_ling_tan, cj)
    assert "铃贪格" in _names(out)


# ── 4. 武贪格 ────────────────────────────────────────────────────
def test_wu_tan_hit_same_palace():
    cj = _mk({"子": ([("武曲", None, "旺"), ("贪狼", None, "庙")], [])})
    assert "武贪格" in _names(_run(detect_wu_tan, cj))


def test_wu_tan_hit_oppose():
    # 武曲在子(命宫)，贪狼在午(对宫=子+6)
    cj = _mk({"子": ([("武曲", None, "旺")], []), "午": ([("贪狼", None, "庙")], [])})
    assert "武贪格" in _names(_run(detect_wu_tan, cj))


# ── 5. 机月同梁 ──────────────────────────────────────────────────
def test_ji_yue_tong_liang_hit():
    # 天机、太阴、天同、天梁分布于三方四正 子/辰/申/午
    cj = _mk({
        "子": ([("天机", None, "旺")], []),
        "辰": ([("太阴", None, "旺")], []),
        "申": ([("天同", None, "得")], []),
        "午": ([("天梁", None, "庙")], []),
    })
    assert "机月同梁" in _names(_run(detect_ji_yue_tong_liang, cj))


def test_ji_yue_tong_liang_miss_only_three():
    cj = _mk({
        "子": ([("天机", None, "旺")], []),
        "辰": ([("太阴", None, "旺")], []),
        "申": ([("天同", None, "得")], []),
        # 天梁放丑(兄弟宫)，不在三方
        "丑": ([("天梁", None, "庙")], []),
    })
    assert "机月同梁" not in _names(_run(detect_ji_yue_tong_liang, cj))


# ── 6. 廉贞天相格 ────────────────────────────────────────────────
def test_lian_xiang_hit():
    cj = _mk({"子": ([("廉贞", None, "平"), ("天相", None, "得")], [])})
    out = _run(detect_lian_xiang, cj, with_ming=False)
    assert "廉贞天相格" in _names(out)


def test_lian_xiang_miss_different_palace():
    cj = _mk({"子": ([("廉贞", None, "平")], []), "辰": ([("天相", None, "得")], [])})
    assert "廉贞天相格" not in _names(_run(detect_lian_xiang, cj, with_ming=False))


# ── 7. 武曲七杀 ──────────────────────────────────────────────────
def test_wu_qi_sha_hit():
    cj = _mk({"子": ([("武曲", None, "旺"), ("七杀", None, "庙")], [])})
    out = _run(detect_wu_qi_sha, cj, with_ming=False)
    assert "武曲七杀" in _names(out)
    assert next(p for p in out if p.name == "武曲七杀").level == "excellent"


# ── 8. 天同天梁格 ────────────────────────────────────────────────
def test_tong_liang_hit():
    cj = _mk({"子": ([("天同", None, "得"), ("天梁", None, "庙")], [])})
    assert "天同天梁格" in _names(_run(detect_tong_liang, cj, with_ming=False))


# ── 9. 日月同宫 ──────────────────────────────────────────────────
def test_ri_yue_tong_gong_hit_wei():
    # 太阳太阴同在未(7)，命宫在未
    cj = _mk({"未": ([("太阳", None, "得"), ("太阴", None, "旺")], [])}, ming="未")
    out = _run(detect_ri_yue_tong_gong, cj, with_ming=False)
    assert "日月同宫" in _names(out)


def test_ri_yue_tong_gong_miss_wrong_branch():
    # 太阳太阴同在子(0) → 非丑/未 → 不触发
    cj = _mk({"子": ([("太阳", None, "得"), ("太阴", None, "旺")], [])})
    assert "日月同宫" not in _names(_run(detect_ri_yue_tong_gong, cj, with_ming=False))


# ── 10. 日月夹命 ─────────────────────────────────────────────────
def test_ri_yue_jia_ming_hit():
    # 命宫子(0)，prev=亥(11)放太阳，next=丑(1)放太阴
    cj = _mk({"亥": ([("太阳", None, "庙")], []), "丑": ([("太阴", None, "旺")], [])})
    assert "日月夹命" in _names(_run(detect_ri_yue_jia_ming, cj, with_ming=False))


def test_ri_yue_jia_ming_miss_not_adjacent():
    # 太阳太阴在三方但不夹命 → 不触发
    cj = _mk({"辰": ([("太阳", None, "庙")], []), "申": ([("太阴", None, "旺")], [])})
    assert "日月夹命" not in _names(_run(detect_ri_yue_jia_ming, cj, with_ming=False))


# ── 11. 巨日同宫 ─────────────────────────────────────────────────
def test_ju_ri_tong_gong_hit_yin():
    # 巨门太阳同在寅(2)，命宫在寅
    cj = _mk({"寅": ([("巨门", None, "庙"), ("太阳", None, "庙")], [])}, ming="寅")
    out = _run(detect_ju_ri_tong_gong, cj, with_ming=False)
    assert "巨日同宫" in _names(out)
    assert next(p for p in out if p.name == "巨日同宫").level == "excellent"


def test_ju_ri_tong_gong_miss_wrong_branch():
    # 巨门太阳同在子(0) → 非寅/申 → 不触发
    cj = _mk({"子": ([("巨门", None, "庙"), ("太阳", None, "庙")], [])})
    assert "巨日同宫" not in _names(_run(detect_ju_ri_tong_gong, cj, with_ming=False))


# ── 12. 石中隐玉 ─────────────────────────────────────────────────
def test_shi_zhong_yin_yu_hit():
    # 巨门入命于子(0)
    cj = _mk({"子": ([("巨门", None, "旺")], [])})
    assert "石中隐玉" in _names(_run(detect_shi_zhong_yin_yu, cj))


def test_shi_zhong_yin_yu_miss_wrong_branch():
    # 巨门入命于丑(1) → 非子/午 → 不触发
    cj = _mk({"丑": ([("巨门", None, "旺")], [])}, ming="丑")
    assert "石中隐玉" not in _names(_run(detect_shi_zhong_yin_yu, cj))


# ── 13. 明珠出海 ─────────────────────────────────────────────────
def test_ming_zhu_chu_hai_hit():
    # 命宫在未(7)空宫，对宫丑(1)为太阳太阴
    cj = _mk({"丑": ([("太阳", None, "庙"), ("太阴", None, "旺")], [])}, ming="未")
    assert "明珠出海" in _names(_run(detect_ming_zhu_chu_hai, cj))


def test_ming_zhu_chu_hai_miss_ming_not_empty():
    # 命宫未有主星 → 不触发
    cj = _mk({
        "未": ([("天机", None, "旺")], []),
        "丑": ([("太阳", None, "庙"), ("太阴", None, "旺")], []),
    }, ming="未")
    assert "明珠出海" not in _names(_run(detect_ming_zhu_chu_hai, cj))


# ── 14. 紫微入命 ─────────────────────────────────────────────────
def test_zi_wei_in_ming_hit():
    cj = _mk({"子": ([("紫微", None, "庙")], []), "辰": ([], ["左辅"]), "申": ([], ["右弼"])})
    out = _run(detect_zi_wei_in_ming, cj)
    assert "紫微入命" in _names(out)
    assert next(p for p in out if p.name == "紫微入命").level == "excellent"


def test_zi_wei_in_ming_miss_with_tianfu():
    # 紫微+天府同坐 → detect_zi_wei_in_ming 不触发（归 detect_zi_fu）
    cj = _mk({"子": ([("紫微", None, "庙"), ("天府", None, "旺")], [])})
    assert "紫微入命" not in _names(_run(detect_zi_wei_in_ming, cj))


# ── 15. 辅弼夹命 ─────────────────────────────────────────────────
def test_fu_bi_jia_ming_hit():
    # 命宫子(0)，亥(11)放左辅，丑(1)放右弼
    cj = _mk({"亥": ([], ["左辅"]), "丑": ([], ["右弼"])})
    out = _run(detect_fu_bi_jia_ming, cj, with_ming=False)
    assert "辅弼夹命" in _names(out)
    assert next(p for p in out if p.name == "辅弼夹命").level == "excellent"


def test_fu_bi_jia_ming_miss_same_side():
    # 左辅右弼都在亥(同一侧) → 不夹
    cj = _mk({"亥": ([], ["左辅", "右弼"])})
    assert "辅弼夹命" not in _names(_run(detect_fu_bi_jia_ming, cj, with_ming=False))


# ── 16. 昌曲夹命 ─────────────────────────────────────────────────
def test_chang_qu_jia_ming_hit():
    cj = _mk({"亥": ([], ["文昌"]), "丑": ([], ["文曲"])})
    assert "昌曲夹命" in _names(_run(detect_chang_qu_jia_ming, cj, with_ming=False))


def test_chang_qu_jia_ming_miss():
    cj = _mk({"亥": ([], ["文昌"]), "辰": ([], ["文曲"])})
    assert "昌曲夹命" not in _names(_run(detect_chang_qu_jia_ming, cj, with_ming=False))


# ── 17. 魁钺夹命 ─────────────────────────────────────────────────
def test_kui_yue_jia_ming_hit():
    cj = _mk({"亥": ([], ["天魁"]), "丑": ([], ["天钺"])})
    out = _run(detect_kui_yue_jia_ming, cj, with_ming=False)
    assert "魁钺夹命" in _names(out)
    assert next(p for p in out if p.name == "魁钺夹命").level == "good"


# ── 18. 双禄朝垣 ─────────────────────────────────────────────────
def test_shuang_lu_chao_yuan_hit():
    # 化禄在辰(三方)，禄存在申(三方)
    cj = _mk({"辰": ([("武曲", "禄", "旺")], []), "申": ([], ["禄存"])})
    assert "双禄朝垣" in _names(_run(detect_shuang_lu_chao_yuan, cj))


def test_shuang_lu_chao_yuan_miss_only_lucun():
    # 仅禄存在三方，无化禄 → 不触发
    cj = _mk({"辰": ([], ["禄存"])})
    assert "双禄朝垣" not in _names(_run(detect_shuang_lu_chao_yuan, cj))
