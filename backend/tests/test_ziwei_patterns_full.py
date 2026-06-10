"""Batch 2 格局检测器测试（19 个新 detector 的 HIT）+ detect_patterns 编排测试。

三方四正 for 命宫 at 子(0): 子(命宫/0), 辰(财帛/4), 申(官禄/8), 午(迁移/6)。
夹宫 for 命宫 at 子(0): prev=亥(父母/11), next=丑(兄弟/1)。
"""
from app.services.ziwei.chart_model import adapt_chart
from app.services.ziwei.primitives import ming_palace
from app.services.ziwei.patterns import (
    Pattern, detect_patterns,
    detect_hua_lu_ru_ming, detect_hua_ji_ru_ming_qian, detect_yang_tuo_jia_ji,
    detect_huo_ling_jia_ming, detect_kong_jie_jia_ming, detect_lian_sha_yang,
    detect_ju_huo_yang, detect_ling_chang_tuo_wu, detect_ma_tou_dai_jian,
    detect_lu_cun_shou_shen, detect_tian_ma_ru_ming, detect_hua_lu_ru_cai,
    detect_hua_quan_ru_guan, detect_hua_ke_ru_ming_shen, detect_ji_yue_tong_liang_partial,
    detect_chang_qu_tong_hui, detect_fu_bi_tong_hui, detect_kui_yue_tong_hui,
    detect_ke_quan_shuang_hui,
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


def _run(detector, chart_json, with_ming=False):
    chart = adapt_chart(chart_json)
    out = []
    if with_ming:
        detector(chart, ming_palace(chart), out)
    else:
        detector(chart, out)
    return out


def _names(out):
    return {p.name for p in out}


# ── 1. X化禄入命 ────────────────────────────────────────────────
def test_hua_lu_ru_ming_hit():
    cj = _mk({"子": ([("武曲", "禄", "旺")], [])})
    out = _run(detect_hua_lu_ru_ming, cj, with_ming=True)
    assert "武曲化禄入命" in _names(out)
    assert next(p for p in out if p.name == "武曲化禄入命").level == "good"


# ── 2. X化忌入命/迁 ─────────────────────────────────────────────
def test_hua_ji_ru_ming_hit():
    cj = _mk({"子": ([("太阳", "忌", "旺")], [])})
    out = _run(detect_hua_ji_ru_ming_qian, cj)
    assert "太阳化忌入命" in _names(out)


def test_hua_ji_ru_qian_hit():
    # 化忌主星在迁移宫午(6)=子+6
    cj = _mk({"午": ([("巨门", "忌", "旺")], [])})
    out = _run(detect_hua_ji_ru_ming_qian, cj)
    assert "巨门化忌入迁" in _names(out)


# ── 3. 羊陀夹忌 ──────────────────────────────────────────────────
def test_yang_tuo_jia_ji_hit():
    # 命宫子化忌，亥(prev)擎羊，丑(next)陀罗
    cj = _mk({"子": ([("太阳", "忌", "旺")], []), "亥": ([], ["擎羊"]), "丑": ([], ["陀罗"])})
    out = _run(detect_yang_tuo_jia_ji, cj)
    assert "羊陀夹忌" in _names(out)
    assert next(p for p in out if p.name == "羊陀夹忌").level == "caution"


# ── 4. 火铃夹命 ──────────────────────────────────────────────────
def test_huo_ling_jia_ming_hit():
    cj = _mk({"亥": ([], ["火星"]), "丑": ([], ["铃星"])})
    assert "火铃夹命" in _names(_run(detect_huo_ling_jia_ming, cj))


# ── 5. 空劫夹命 ──────────────────────────────────────────────────
def test_kong_jie_jia_ming_hit():
    cj = _mk({"亥": ([], ["地空"]), "丑": ([], ["地劫"])})
    assert "空劫夹命" in _names(_run(detect_kong_jie_jia_ming, cj))


# ── 6. 廉杀羊 ────────────────────────────────────────────────────
def test_lian_sha_yang_hit():
    # 三方四正 子/辰/申: 廉贞、七杀、擎羊
    cj = _mk({"子": ([("廉贞", None, "平")], []), "辰": ([("七杀", None, "庙")], []), "申": ([], ["擎羊"])})
    assert "廉杀羊" in _names(_run(detect_lian_sha_yang, cj))


# ── 7. 巨火羊 ────────────────────────────────────────────────────
def test_ju_huo_yang_hit():
    cj = _mk({"子": ([("巨门", None, "旺")], []), "辰": ([], ["火星"]), "申": ([], ["擎羊"])})
    assert "巨火羊" in _names(_run(detect_ju_huo_yang, cj))


# ── 8. 铃昌陀武 ──────────────────────────────────────────────────
def test_ling_chang_tuo_wu_hit():
    cj = _mk({
        "子": ([("武曲", None, "旺")], ["文昌"]),
        "辰": ([], ["铃星"]),
        "申": ([], ["陀罗"]),
    })
    assert "铃昌陀武" in _names(_run(detect_ling_chang_tuo_wu, cj))


# ── 9. 马头带箭 ──────────────────────────────────────────────────
def test_ma_tou_dai_jian_hit():
    # 命宫在午(6)，擎羊坐命
    cj = _mk({"午": ([], ["擎羊"])}, ming="午")
    out = _run(detect_ma_tou_dai_jian, cj, with_ming=True)
    assert "马头带箭" in _names(out)


def test_ma_tou_dai_jian_bonus_good():
    # 命午擎羊 + 三方七杀 → good
    cj = _mk({"午": ([], ["擎羊"]), "戌": ([("七杀", None, "庙")], [])}, ming="午")
    out = _run(detect_ma_tou_dai_jian, cj, with_ming=True)
    assert next(p for p in out if p.name == "马头带箭").level == "good"


# ── 10. 禄存守命/身 ─────────────────────────────────────────────
def test_lu_cun_shou_ming_hit():
    cj = _mk({"子": ([], ["禄存"])})
    out = _run(detect_lu_cun_shou_shen, cj)
    assert "禄存守命" in _names(out)


def test_lu_cun_shou_shen_hit():
    # 身宫在午，禄存在午
    cj = _mk({"午": ([], ["禄存"])}, shen="午")
    out = _run(detect_lu_cun_shou_shen, cj)
    assert "禄存守身" in _names(out)


# ── 11. 天马入命/迁 ─────────────────────────────────────────────
def test_tian_ma_ru_ming_hit():
    cj = _mk({"子": ([], ["天马"])})
    assert "天马入命" in _names(_run(detect_tian_ma_ru_ming, cj))


def test_tian_ma_zai_qian_hit():
    cj = _mk({"午": ([], ["天马"])})
    assert "天马在迁" in _names(_run(detect_tian_ma_ru_ming, cj))


# ── 12. 化禄入财 ─────────────────────────────────────────────────
def test_hua_lu_ru_cai_hit():
    # 财帛宫在辰(子命起)，武曲化禄入财
    cj = _mk({"辰": ([("武曲", "禄", "旺")], [])})
    assert "化禄入财" in _names(_run(detect_hua_lu_ru_cai, cj))


# ── 13. 化权入官 ─────────────────────────────────────────────────
def test_hua_quan_ru_guan_hit():
    # 官禄宫在申(子命起)，太阳化权入官
    cj = _mk({"申": ([("太阳", "权", "旺")], [])})
    assert "化权入官" in _names(_run(detect_hua_quan_ru_guan, cj))


# ── 14. 化科入命/身 ─────────────────────────────────────────────
def test_hua_ke_ru_ming_hit():
    cj = _mk({"子": ([("文昌", "科", "旺")], [])})
    out = _run(detect_hua_ke_ru_ming_shen, cj)
    assert "化科入命" in _names(out)


def test_hua_ke_ru_shen_hit():
    # 命宫无化科主星，身宫午有化科主星
    cj = _mk({"午": ([("天机", "科", "旺")], [])}, shen="午")
    out = _run(detect_hua_ke_ru_ming_shen, cj)
    assert "化科入身" in _names(out)


# ── 15. 机月同梁三星会 ──────────────────────────────────────────
def test_ji_yue_tong_liang_partial_hit():
    # 三方四正 子/辰/申 放天机/太阴/天同（缺天梁）
    cj = _mk({
        "子": ([("天机", None, "旺")], []),
        "辰": ([("太阴", None, "旺")], []),
        "申": ([("天同", None, "得")], []),
    })
    out = _run(detect_ji_yue_tong_liang_partial, cj, with_ming=True)
    assert "机月同梁三星会" in _names(out)


def test_ji_yue_tong_liang_partial_miss_four_full():
    # 4 星齐 → partial 不触发（交由 detect_ji_yue_tong_liang）
    cj = _mk({
        "子": ([("天机", None, "旺")], []),
        "辰": ([("太阴", None, "旺")], []),
        "申": ([("天同", None, "得")], []),
        "午": ([("天梁", None, "庙")], []),
    })
    out = _run(detect_ji_yue_tong_liang_partial, cj, with_ming=True)
    assert "机月同梁三星会" not in _names(out)


# ── 16. 昌曲同会 ─────────────────────────────────────────────────
def test_chang_qu_tong_hui_hit():
    cj = _mk({"辰": ([], ["文昌"]), "申": ([], ["文曲"])})
    out = _run(detect_chang_qu_tong_hui, cj)
    assert "昌曲同会" in _names(out)


def test_chang_qu_zuo_ming_hit():
    cj = _mk({"子": ([], ["文昌", "文曲"])})
    out = _run(detect_chang_qu_tong_hui, cj)
    assert "昌曲坐命" in _names(out)


# ── 17. 辅弼同会 ─────────────────────────────────────────────────
def test_fu_bi_tong_hui_hit():
    cj = _mk({"辰": ([], ["左辅"]), "申": ([], ["右弼"])})
    assert "辅弼同会" in _names(_run(detect_fu_bi_tong_hui, cj))


# ── 18. 魁钺同会 ─────────────────────────────────────────────────
def test_kui_yue_tong_hui_hit():
    cj = _mk({"辰": ([], ["天魁"]), "申": ([], ["天钺"])})
    assert "魁钺同会" in _names(_run(detect_kui_yue_tong_hui, cj))


# ── 19. 科权双会 ─────────────────────────────────────────────────
def test_ke_quan_shuang_hui_hit():
    cj = _mk({"辰": ([("文昌", "科", "旺")], []), "申": ([("太阳", "权", "旺")], [])})
    assert "科权双会" in _names(_run(detect_ke_quan_shuang_hui, cj))


# ── 编排 / 注册数 / 鲁棒性 ──────────────────────────────────────
def test_all_detectors_registered():
    import app.services.ziwei.patterns as P
    detector_fns = [n for n in dir(P) if n.startswith("detect_") and n != "detect_patterns"]
    assert len(detector_fns) >= 38, f"only {len(detector_fns)} detectors registered: {detector_fns}"


def test_detect_patterns_runs_full_order():
    # 富盘：命子紫微+左辅右弼会照(君臣庆会/紫微入命)，三方三奇加会，迁移天马，财帛化禄
    cj = _mk({
        "子": ([("紫微", None, "庙")], []),
        "辰": ([("武曲", "禄", "旺")], ["左辅"]),    # 财帛: 化禄入财 + 双禄/辅
        "申": ([("太阳", "权", "旺")], ["右弼", "禄存"]),  # 官禄: 化权入官 + 禄存三方
        "午": ([("文曲", "科", "旺")], ["天马", "文昌"]),  # 迁移: 天马在迁 + 昌曲/科
    })
    out = detect_patterns(adapt_chart(cj))
    assert isinstance(out, list)
    names = _names(out)
    # 跨类目命中
    assert "君臣庆会" in names      # 上格
    assert "三奇加会" in names      # 助力格（禄+权+科 三方齐）
    assert "化禄入财" in names      # 基础
    assert "化权入官" in names      # 基础
    assert "天马在迁" in names      # 基础
    # 每个 Pattern 字段完整
    valid_levels = {"excellent", "good", "neutral", "caution"}
    for p in out:
        assert isinstance(p, Pattern)
        assert p.name
        assert p.level in valid_levels
        assert p.source
        assert isinstance(p.palaces, list)


def test_no_crash_on_empty_and_sparse():
    cj = _mk({})  # 12 宫无星
    out = detect_patterns(adapt_chart(cj))
    assert out == []
