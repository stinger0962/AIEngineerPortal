from app.services.ziwei.chart_model import adapt_chart, branch_to_int
from app.services.ziwei.primitives import (
    san_fang_palaces, san_fang_all_stars, san_fang_mutagens, jia_palaces, dui_gong, ming_palace, has_star,
)


def _chart_json():
    # 命宫在子(0)；三方四正 = 子(0)/辰(4)/申(8)/午(6)
    def palace(name, branch, majors=None, minors=None):
        return {
            "name": name, "earthlyBranch": branch, "heavenlyStem": "甲",
            "majorStars": [{"name": n, "type": "major", "mutagen": m, "brightness": b}
                           for (n, m, b) in (majors or [])],
            "minorStars": [{"name": n, "type": "soft"} for n in (minors or [])],
            "adjectiveStars": [], "isBodyPalace": False, "isOriginalPalace": False,
            "changsheng12": "长生", "decadal": {"range": [1, 10], "heavenlyStem": "甲", "earthlyBranch": branch}, "ages": [],
        }
    return {
        "earthlyBranchOfSoulPalace": "子", "earthlyBranchOfBodyPalace": "午",
        "palaces": [
            palace("命宫", "子", majors=[("紫微", "权", "庙")], minors=["左辅"]),
            palace("兄弟", "丑"),
            palace("夫妻", "寅"),
            palace("子女", "卯"),
            palace("财帛", "辰", majors=[("天府", None, "旺")], minors=["右弼"]),
            palace("疾厄", "巳"),
            palace("迁移", "午", majors=[("贪狼", "禄", "平")]),
            palace("交友", "未"),
            palace("官禄", "申", majors=[("武曲", None, "得")], minors=["文昌"]),
            palace("田宅", "酉"),
            palace("福德", "戌"),
            palace("父母", "亥"),
        ],
    }


def test_branch_to_int():
    assert branch_to_int("子") == 0
    assert branch_to_int("午") == 6
    assert branch_to_int("亥") == 11


def test_san_fang_collects_命财官迁():
    chart = adapt_chart(_chart_json())
    names = {p.name for p in san_fang_palaces(chart)}
    assert names == {"命宫", "财帛", "官禄", "迁移"}


def test_san_fang_all_stars_and_mutagens():
    chart = adapt_chart(_chart_json())
    stars = san_fang_all_stars(chart)
    assert {"紫微", "左辅", "右弼", "贪狼", "武曲", "文昌", "天府"} <= stars
    assert san_fang_mutagens(chart) == {"权", "禄"}  # 紫微化权(命) + 贪狼化禄(迁)


def test_dui_gong_and_jia():
    chart = adapt_chart(_chart_json())
    assert dui_gong(chart, 0).name == "迁移"  # 子对午
    prev, nxt = jia_palaces(chart, 0)  # 命宫子 的夹宫 = 亥(父母) / 丑(兄弟)
    assert prev.name == "父母" and nxt.name == "兄弟"
    assert has_star(ming_palace(chart), "紫微")
