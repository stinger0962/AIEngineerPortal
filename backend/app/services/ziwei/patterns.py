"""格局检测（移植 Renhuai123/ziwei-doushu lib/ziwei/patterns.ts，MIT，署名 紫微研究）。
作用于内部 Chart（见 chart_model.py）。每个 Pattern 自带古籍出处 source。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

from .chart_model import BRANCH_NAMES, Chart, Palace
from .primitives import (
    SHA_HARD, SHA_KONG, dui_gong, find_star_palace, has_sha_in_palace, has_star,
    is_in_san_fang, jia_palaces, major_star_names, ming_palace, san_fang_all_stars,
    san_fang_mutagens, san_fang_palaces, san_fang_sha_count, sha_count_in_palace,
    star_mutagen, is_bright, is_dim,
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
        description="太阳、天梁、文昌、禄存四星齐会命宫三方，号称“科举之星”，主清贵显达、考运极佳，宜走学术、文教、研究、专业认证之路，一生功名易就。",
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
        description="化禄、化权、化科三吉化齐会命宫三方四正，号称“三奇加会”。主一生功名、财富、贵人三全，是紫微斗数最高吉格之一。",
        palaces=[p.name for p in san_fang_palaces(chart)], source="《紫微斗数全书·三奇加会》",
        required=["化禄、化权、化科三吉化齐会命宫三方四正"],
    ))


# ───────── 主星同宫 / 会照 / 夹 格局（batch 1：18 个）─────────

def detect_zi_fu(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """紫府同宫：紫微+天府于命宫（限寅、申宫）"""
    ziwei = find_star_palace(chart, "紫微")
    tianfu = find_star_palace(chart, "天府")
    if not ziwei or not tianfu or ziwei.branch != tianfu.branch:
        return

    in_ming = ziwei.branch == chart.ming_branch
    required = (["紫微天府同入命宫"] if in_ming
                else ["紫微天府同宫（不在命宫，会照减力）"])
    bonus: list[str] = []
    breaking: list[str] = []
    sf = san_fang_all_stars(chart)
    if "左辅" in sf and "右弼" in sf:
        bonus.append("左辅右弼同会")
    if "文昌" in sf or "文曲" in sf:
        bonus.append("再会昌曲")
    if has_sha_in_palace(ziwei, SHA_KONG):
        breaking.append("紫府宫坐空劫（破紫府之贵气）")
    if sha_count_in_palace(ziwei, SHA_HARD) >= 2:
        breaking.append("紫府宫见双煞同坐")

    out.append(Pattern(
        name="紫府同宫",
        level="excellent" if in_ming and not breaking else "good",
        description=("紫微天府同入命宫，帝相并临，尊贵之命。主品行端正、衣食无忧、有领导才能，宜担任要职。需要左右辅弼来配合方为完整大格。"
                     if in_ming
                     else "紫微天府同宫但未坐命，主一生有贵人贵气依托，但本身不一定大富贵，需看会照吉煞而定。"),
        palaces=[ziwei.name], source="《紫微斗数全书·紫府同宫格》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_fu_xiang_chao_yuan(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """府相朝垣：天府、天相分别坐守命宫的三方四正"""
    tianfu = find_star_palace(chart, "天府")
    tianxiang = find_star_palace(chart, "天相")
    if not tianfu or not tianxiang:
        return
    if not is_in_san_fang(chart, tianfu.branch) or not is_in_san_fang(chart, tianxiang.branch):
        return
    if tianfu.branch == chart.ming_branch and tianxiang.branch == chart.ming_branch:
        return
    if tianfu.branch == tianxiang.branch:
        return

    required = ["天府坐命三方", "天相坐命三方", "两星不同宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if has_star(ming, "禄存") or has_star(ming, "化禄"):
        bonus.append("命宫见禄")
    if "左辅" in san_fang_all_stars(chart):
        bonus.append("再会左辅")
    if has_sha_in_palace(ming, SHA_HARD):
        breaking.append("命宫坐煞星")
    if san_fang_sha_count(chart, SHA_HARD) >= 3:
        breaking.append("三方四正煞星过多")

    out.append(Pattern(
        name="府相朝垣",
        level="good" if breaking else "excellent",
        description="天府天相分守命宫三方四正，文武并济、权印双辉，主一生衣食丰足、地位崇高。古书云“府相朝垣千钟食禄”，常见于政界、企业管理者。",
        palaces=[tianfu.name, tianxiang.name], source="《紫微斗数全书·府相朝垣格》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_huo_tan_ling_tan(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """火贪格 / 铃贪格：贪狼+火星 或 贪狼+铃星 同宫或会照"""
    tan = find_star_palace(chart, "贪狼")
    if not tan:
        return
    huo = find_star_palace(chart, "火星")
    ling = find_star_palace(chart, "铃星")

    for sha_name, sha_palace in (("火星", huo), ("铃星", ling)):
        if not sha_palace:
            continue
        same_or_trine = (
            tan.branch == sha_palace.branch
            or (tan.branch + 4) % 12 == sha_palace.branch
            or (tan.branch + 8) % 12 == sha_palace.branch
            or (tan.branch + 6) % 12 == sha_palace.branch
        )
        if not same_or_trine:
            continue
        if not is_in_san_fang(chart, tan.branch):
            continue

        same = tan.branch == sha_palace.branch
        required = [f"贪狼{'同宫' if same else '会照'}{sha_name}", "贪狼会照命宫三方"]
        bonus: list[str] = []
        breaking: list[str] = []
        if is_bright(tan, "贪狼"):
            bonus.append("贪狼庙旺")
        if star_mutagen(tan, "贪狼") in ("禄", "权"):
            bonus.append("贪狼化禄/化权")
        if has_sha_in_palace(tan, ["擎羊", "陀罗"]):
            breaking.append("贪狼宫又见羊陀（破横发之力）")
        if has_sha_in_palace(tan, SHA_KONG):
            breaking.append("贪狼遇空劫（财来财去）")

        out.append(Pattern(
            name="火贪格" if sha_name == "火星" else "铃贪格",
            level="good" if breaking else "excellent",
            description=f"贪狼遇{sha_name}{'同宫' if same else '三方会照'}，主突发横财、突如其来的机遇。古书云“贪狼遇火铃，必发横财”，但来得快去得也快，宜见好就收。{'本盘破格条件已触发，发力打折。' if breaking else ''}",
            palaces=[tan.name, sha_palace.name], source="《紫微斗数骨髓赋》",
            required=required, bonus=bonus, breaking=breaking,
        ))


def detect_wu_tan(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """武贪格：武曲+贪狼 同宫（丑、未） 或 对照"""
    wu = find_star_palace(chart, "武曲")
    tan = find_star_palace(chart, "贪狼")
    if not wu or not tan:
        return
    same_or_oppose = wu.branch == tan.branch or (wu.branch + 6) % 12 == tan.branch
    if not same_or_oppose:
        return
    if not is_in_san_fang(chart, wu.branch) and not is_in_san_fang(chart, tan.branch):
        return

    required = [
        "武曲贪狼同宫（丑/未）" if wu.branch == tan.branch else "武曲贪狼对宫拱照",
        "会照命宫三方",
    ]
    bonus: list[str] = []
    breaking: list[str] = []
    sf = san_fang_all_stars(chart)
    if "火星" in sf or "铃星" in sf:
        bonus.append("再遇火星/铃星（火贪/铃贪叠加）")
    if star_mutagen(wu, "武曲") == "禄":
        bonus.append("武曲化禄")
    if has_sha_in_palace(wu, ["擎羊", "陀罗"]):
        breaking.append("武贪宫见羊陀")
    if has_sha_in_palace(wu, SHA_KONG):
        breaking.append("武贪宫遇空劫")

    out.append(Pattern(
        name="武贪格",
        level="good" if breaking else "excellent",
        description="武曲贪狼会命，财星与桃花欲望星交辉，古书云“武贪不发少年人”——三十岁后方能厚积薄发。主中年以后大富大贵，财源由人脉、应酬、欲望管理而来，适合金融、投机、销售、娱乐业。",
        palaces=[wu.name, tan.name], source="《紫微斗数骨髓赋》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_ji_yue_tong_liang(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """机月同梁：天机、太阴、天同、天梁四星齐入命迁财官"""
    sf = san_fang_all_stars(chart)
    has = [s for s in ("天机", "太阴", "天同", "天梁") if s in sf]
    if len(has) < 4:
        return

    required = ["天机、太阴、天同、天梁四星齐入命宫三方四正"]
    bonus: list[str] = []
    breaking: list[str] = []
    if "文昌" in sf or "文曲" in sf:
        bonus.append("再会昌曲")
    if "科" in san_fang_mutagens(chart):
        bonus.append("再会化科")
    if san_fang_sha_count(chart, SHA_HARD) >= 3:
        breaking.append("煞星过多（机月同梁忌煞）")
    if has_sha_in_palace(ming, SHA_HARD):
        breaking.append("命宫坐煞")

    out.append(Pattern(
        name="机月同梁",
        level="good" if breaking else "excellent",
        description="天机太阴天同天梁四星齐入命迁财官，文质彬彬、聪慧善谋。最适合公职、学术、文艺、医疗、服务等需稳定累积的行业，不宜大冒险大投机。",
        palaces=[p.name for p in san_fang_palaces(chart)
                 if any(s in major_star_names(p) for s in has)],
        source="《紫微斗数全书·机月同梁格》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_lian_xiang(chart: Chart, out: list[Pattern]) -> None:
    """廉贞天相：同宫"""
    lian = find_star_palace(chart, "廉贞")
    xiang = find_star_palace(chart, "天相")
    if not lian or not xiang or lian.branch != xiang.branch:
        return

    in_ming = lian.branch == chart.ming_branch
    required = ["廉贞天相同宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if has_star(lian, "禄存") or star_mutagen(lian, "廉贞") == "禄":
        bonus.append("见禄存或廉贞化禄")
    if "左辅" in san_fang_all_stars(chart):
        bonus.append("左辅会照")
    if has_sha_in_palace(lian, ["擎羊"]):
        breaking.append("廉相宫坐擎羊（廉杀羊倾向）")
    if star_mutagen(lian, "廉贞") == "忌":
        breaking.append("廉贞化忌")

    out.append(Pattern(
        name="廉贞天相格",
        level="caution" if breaking else ("good" if in_ming else "neutral"),
        description="廉贞天相同宫，印绶格局，主秉公处事、清廉之名，宜任公职、行政管理、法务、企划。怕见擎羊化忌，则反主官非。",
        palaces=[lian.name], source="《紫微斗数全书》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_wu_qi_sha(chart: Chart, out: list[Pattern]) -> None:
    """武曲七杀：同宫，将星配财星"""
    wu = find_star_palace(chart, "武曲")
    qi = find_star_palace(chart, "七杀")
    if not wu or not qi or wu.branch != qi.branch:
        return

    in_ming = wu.branch == chart.ming_branch
    required = ["武曲七杀同宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if star_mutagen(wu, "武曲") == "权":
        bonus.append("武曲化权")
    if star_mutagen(wu, "武曲") == "禄":
        bonus.append("武曲化禄")
    if star_mutagen(wu, "武曲") == "忌":
        breaking.append("武曲化忌（武曲化忌为财劫之兆）")
    if has_sha_in_palace(wu, ["擎羊", "陀罗", "火星", "铃星"]):
        breaking.append("武杀宫煞星过多")

    out.append(Pattern(
        name="武曲七杀",
        level="caution" if breaking else ("excellent" if in_ming else "good"),
        description="武曲七杀同宫，将星配财星，主果决刚毅、理财能力强，适合金融、军警、创业。但忌见化忌煞星，否则凶险。一生奋斗、积财但操心。",
        palaces=[wu.name], source="《紫微斗数全书》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_tong_liang(chart: Chart, out: list[Pattern]) -> None:
    """天同天梁：同宫"""
    tong = find_star_palace(chart, "天同")
    liang = find_star_palace(chart, "天梁")
    if not tong or not liang or tong.branch != liang.branch:
        return

    required = ["天同天梁同宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if "文昌" in san_fang_all_stars(chart):
        bonus.append("文昌会照")
    if star_mutagen(tong, "天同") == "禄":
        bonus.append("天同化禄")
    if has_sha_in_palace(tong, SHA_HARD):
        breaking.append("煞星同坐")

    out.append(Pattern(
        name="天同天梁格",
        level="neutral" if breaking else "good",
        description="天同天梁同宫，福星与荫星共会，主宽厚和善、乐于助人，宜医疗、教育、宗教、社会公益。但偏温和保守，难成大富大贵之局。",
        palaces=[tong.name], source="《紫微斗数全书》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_ri_yue_tong_gong(chart: Chart, out: list[Pattern]) -> None:
    """日月同宫：太阳太阴丑或未宫同宫"""
    sun = find_star_palace(chart, "太阳")
    moon = find_star_palace(chart, "太阴")
    if not sun or not moon or sun.branch != moon.branch:
        return
    if sun.branch != 1 and sun.branch != 7:  # 必须丑(1) 或 未(7)
        return

    in_ming = sun.branch == chart.ming_branch
    required = [f"太阳太阴同入{BRANCH_NAMES[sun.branch]}宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if sun.branch == 7:
        bonus.append("未宫日月同辉（古书云未宫日月双美）")
    sf = san_fang_all_stars(chart)
    if "文昌" in sf and "文曲" in sf:
        bonus.append("昌曲会照")
    if has_sha_in_palace(sun, SHA_HARD):
        breaking.append("日月宫煞星同坐")

    out.append(Pattern(
        name="日月同宫",
        level="good" if breaking else ("excellent" if in_ming else "good"),
        description=f"太阳太阴于{BRANCH_NAMES[sun.branch]}宫同宫，阴阳平衡，文武兼备。主异性缘佳、事业顺遂、名声远播。{'未宫日月双美尤佳。' if sun.branch == 7 else '丑宫日月同宫力量较平。'}",
        palaces=[sun.name], source="《紫微斗数全书》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_ri_yue_jia_ming(chart: Chart, out: list[Pattern]) -> None:
    """日月夹命：太阳太阴在命宫前后两宫"""
    prev, nxt = jia_palaces(chart, chart.ming_branch)
    if not prev or not nxt:
        return
    prev_has_sun = has_star(prev, "太阳")
    prev_has_moon = has_star(prev, "太阴")
    next_has_sun = has_star(nxt, "太阳")
    next_has_moon = has_star(nxt, "太阴")
    ok = (prev_has_sun and next_has_moon) or (prev_has_moon and next_has_sun)
    if not ok:
        return

    sun_palace = prev if prev_has_sun else nxt
    moon_palace = prev if prev_has_moon else nxt
    required = ["太阳太阴分居命宫前后两宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if is_bright(sun_palace, "太阳"):
        bonus.append("太阳庙旺")
    if is_bright(moon_palace, "太阴"):
        bonus.append("太阴庙旺")
    if is_dim(sun_palace, "太阳") or is_dim(moon_palace, "太阴"):
        breaking.append("日月落陷（夹命无光）")

    out.append(Pattern(
        name="日月夹命",
        level="good" if breaking else "excellent",
        description="太阳太阴分居命宫两侧夹照，光明磊落，一生贵人相助，事业蓬勃。男主官贵，女主旺夫兴家。日月须不落陷方为真夹。",
        palaces=[sun_palace.name, moon_palace.name], source="《紫微斗数全书·日月夹命》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_ju_ri_tong_gong(chart: Chart, out: list[Pattern]) -> None:
    """巨日同宫：巨门太阳同入寅或申"""
    ju = find_star_palace(chart, "巨门")
    sun = find_star_palace(chart, "太阳")
    if not ju or not sun or ju.branch != sun.branch:
        return
    if ju.branch != 2 and ju.branch != 8:  # 必须寅(2) 或 申(8)
        return

    in_ming = ju.branch == chart.ming_branch
    required = [f"巨门太阳同入{BRANCH_NAMES[ju.branch]}宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if ju.branch == 2:
        bonus.append("寅宫太阳庙旺，巨门得日光化解是非")
    if star_mutagen(ju, "巨门") in ("禄", "权"):
        bonus.append("巨门化禄/化权（口才生财）")
    if star_mutagen(ju, "巨门") == "忌":
        breaking.append("巨门化忌（口舌官非）")
    if ju.branch == 8:
        breaking.append("申宫太阳偏西，巨门暗曜更显")

    out.append(Pattern(
        name="巨日同宫",
        level="caution" if breaking else ("excellent" if in_ming and ju.branch == 2 else "good"),
        description=f"巨门太阳同{BRANCH_NAMES[ju.branch]}宫，太阳化解巨门暗曜，主以口才、传媒、外语、专业立业。寅宫为佳，申宫力减。怕巨门化忌则官非。",
        palaces=[ju.name], source="《紫微斗数全书·巨日同宫》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_shi_zhong_yin_yu(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """石中隐玉：巨门入命于子午宫"""
    if not has_star(ming, "巨门"):
        return
    if ming.branch != 0 and ming.branch != 6:  # 子(0) 或 午(6)
        return

    required = [f"巨门入命于{BRANCH_NAMES[ming.branch]}宫"]
    bonus: list[str] = []
    breaking: list[str] = []
    if star_mutagen(ming, "巨门") in ("禄", "权"):
        bonus.append("巨门化禄/化权")
    if "文昌" in san_fang_all_stars(chart):
        bonus.append("文昌会照（石中隐玉得明）")
    if star_mutagen(ming, "巨门") == "忌":
        breaking.append("巨门化忌（玉藏深泥）")
    if has_sha_in_palace(ming, SHA_HARD):
        breaking.append("命坐煞星")

    out.append(Pattern(
        name="石中隐玉",
        level="caution" if breaking else "excellent",
        description="巨门坐命子午，外表平凡而内蕴才学。早年默默无闻、中年方显贵气，宜走专业、研究、口才、传媒。需有禄权或文昌相助方能“凿石见玉”。",
        palaces=["命宫"], source="《紫微斗数骨髓赋·石中隐玉》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_ming_zhu_chu_hai(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """明珠出海：命宫在未空宫，对宫丑宫为太阳太阴"""
    if ming.branch != 7:  # 命在未
        return
    if len(major_star_names(ming)) > 0:  # 命宫为空宫
        return
    dui = dui_gong(chart, ming.branch)
    if not dui:
        return
    if not has_star(dui, "太阳") or not has_star(dui, "太阴"):
        return

    required = ["命宫在未为空宫", "对宫丑宫为太阳太阴同度"]
    bonus: list[str] = []
    breaking: list[str] = []
    sf = san_fang_all_stars(chart)
    if "文昌" in sf or "文曲" in sf:
        bonus.append("再会昌曲")
    if "左辅" in sf or "右弼" in sf:
        bonus.append("辅弼相助")
    if san_fang_sha_count(chart, SHA_HARD) >= 2:
        breaking.append("煞星会照（珠光黯淡）")

    out.append(Pattern(
        name="明珠出海",
        level="good" if breaking else "excellent",
        description="命未空宫，对宫丑宫日月同辉拱照，号“明珠出海”。主出生平凡、后天努力出头，宜远赴他乡、学术研究或大公司高位，主大富大贵。",
        palaces=["命宫", dui.name], source="《紫微斗数全集·明珠出海》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_zi_wei_in_ming(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """紫微独坐入命"""
    if not has_star(ming, "紫微") or has_star(ming, "天府"):
        return

    required = ["紫微独坐命宫（无天府同坐）"]
    bonus: list[str] = []
    breaking: list[str] = []
    sf = san_fang_all_stars(chart)
    if "左辅" in sf and "右弼" in sf:
        bonus.append("左辅右弼同会")
    if "文昌" in sf and "文曲" in sf:
        bonus.append("文昌文曲同会")
    if "左辅" not in sf and "右弼" not in sf:
        breaking.append("无辅弼（孤君无臣）")
    if has_sha_in_palace(ming, SHA_KONG):
        breaking.append("紫微遇空劫（古书最忌）")

    out.append(Pattern(
        name="紫微入命",
        level="caution" if breaking else ("excellent" if bonus else "good"),
        description="紫微独坐命宫，帝王之星，自尊心强、有领导魅力。但紫微最忌“在野孤君”——若无左右辅弼相会，反成孤高自傲、易招毁谤。",
        palaces=["命宫"], source="《紫微斗数全书》",
        required=required, bonus=bonus, breaking=breaking,
    ))


def detect_fu_bi_jia_ming(chart: Chart, out: list[Pattern]) -> None:
    """辅弼夹命"""
    prev, nxt = jia_palaces(chart, chart.ming_branch)
    if not prev or not nxt:
        return
    ok = (has_star(prev, "左辅") and has_star(nxt, "右弼")) or (has_star(prev, "右弼") and has_star(nxt, "左辅"))
    if not ok:
        return
    bonus = []
    sf = san_fang_all_stars(chart)
    if "天魁" in sf or "天钺" in sf:
        bonus.append("再会魁钺")
    out.append(Pattern(
        name="辅弼夹命", level="excellent",
        description="左辅右弼夹命，一生贵人不断、逢凶化吉。适合走仕途、大企业管理，有贵人提携之命。古书云“左辅右弼，终身福厚”。",
        palaces=["命宫", prev.name, nxt.name], source="《紫微斗数全书·辅弼夹命》",
        required=["左辅右弼分居命宫前后两宫"], bonus=bonus,
    ))


def detect_chang_qu_jia_ming(chart: Chart, out: list[Pattern]) -> None:
    """昌曲夹命"""
    prev, nxt = jia_palaces(chart, chart.ming_branch)
    if not prev or not nxt:
        return
    prev_has_chang = has_star(prev, "文昌")
    prev_has_qu = has_star(prev, "文曲")
    next_has_chang = has_star(nxt, "文昌")
    next_has_qu = has_star(nxt, "文曲")
    if not ((prev_has_chang and next_has_qu) or (prev_has_qu and next_has_chang)):
        return

    out.append(Pattern(
        name="昌曲夹命", level="excellent",
        description="文昌文曲夹命宫，主聪明俊秀、文采斐然，宜走文教、学术、艺术、写作。古书云“昌曲夹命主科甲”，最利考运。",
        palaces=["命宫", prev.name, nxt.name], source="《紫微斗数全书》",
        required=["文昌文曲分居命宫前后两宫"],
    ))


def detect_kui_yue_jia_ming(chart: Chart, out: list[Pattern]) -> None:
    """魁钺夹命"""
    prev, nxt = jia_palaces(chart, chart.ming_branch)
    if not prev or not nxt:
        return
    ok_a = has_star(prev, "天魁") and has_star(nxt, "天钺")
    ok_b = has_star(prev, "天钺") and has_star(nxt, "天魁")
    if not ok_a and not ok_b:
        return

    out.append(Pattern(
        name="魁钺夹命", level="good",
        description="天魁天钺夹命，男称天乙、女称玉堂，一生贵人提携。考试、求职、关键时刻常有意外贵人相助。",
        palaces=["命宫", prev.name, nxt.name], source="《紫微斗数全书》",
        required=["天魁天钺分居命宫前后两宫"],
    ))


def detect_shuang_lu_chao_yuan(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    """双禄朝垣：化禄 + 禄存 同会三方"""
    san_fang = san_fang_palaces(chart)
    hua_lu_found = False
    lu_cun_found = False
    for p in san_fang:
        if any(s.mutagen == "禄" for s in p.stars):
            hua_lu_found = True
        if has_star(p, "禄存"):
            lu_cun_found = True
    if not hua_lu_found or not lu_cun_found:
        return

    breaking = ["命坐空劫（双禄遇空，财来财去）"] if has_sha_in_palace(ming, SHA_KONG) else []
    out.append(Pattern(
        name="双禄朝垣", level="excellent",
        description="化禄、禄存同会命宫三方四正，财源涌动、衣食丰足。古书云“双禄朝垣，富比陶朱”，主一生不愁财，多有正财横财兼得。",
        palaces=[p.name for p in san_fang], source="《紫微斗数全书·双禄朝垣》",
        required=["化禄会照三方四正", "禄存会照三方四正"], breaking=breaking,
    ))


# 占位：Task 4 batch 2 追加其余检测器并填充 detect_patterns 的完整调用序列
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
