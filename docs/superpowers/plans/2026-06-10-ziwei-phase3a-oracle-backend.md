# 紫微斗数 Phase 3a（AI 解盘师 · 后端大脑）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地 AI 解盘师的后端地基——把 Renhuai123 仓库的格局检测移植为 Python（适配 iztro chart_json）作为确定性知识地基，建对话/消息持久化，写 oracle 循环（人设 + 命盘摘要 + 命中格局 + 画像 + 事件 → Claude tool_use），并用极简面板验证大脑跑通。

**Architecture:** 后端读 `ZiweiProfile.chart_json`（iztro 排盘结果）→ 适配为内部命盘表示 → 规则引擎检测命中格局（~41 个，每个带古籍出处）→ `ziwei_oracle.py` 组装 system prompt 调 Claude（复刻 `copilot_loop.py` 的非流式 tool_use 模式），相机指令（`focus_palace`）在本期由 Claude 决定并收集、由路由返回，**消费留给 Phase 3b**。对话与消息持久化到新表。流式 SSE、三态对话坞、镜头飞入联动、人设切换 UI、历史回看全部归 **Phase 3b**。

**知识地基现实（侦察结论，务必遵守）：**
- Renhuai123/ziwei-doushu 的「论断内容库」**不存在**（`STAR_DB={}` 空占位），「51.8万样本」**未随仓库发布**。
- 真实可用：`patterns.ts`（~41 个格局**检测函数**，非数据）、四化表、14 条主星简介、MIT 协议（署名「紫微研究」）。
- 因此：移植格局检测作确定性地基（每个格局自带 `source` 古籍出处 → 免费获得「引经据典」能力）；逐星逐宫解读 prose 交给 Claude 自身知识；**不引入向量库、不提取古籍 TS 文本**。

**Spec:** `docs/superpowers/specs/2026-06-09-ziwei-3d-design.md`（§6 AI 解盘循环、§7 知识库、§11 分期第 3 条）。注意 §7 原设想「提取 patterns.json」与现实不符——本计划以「移植检测逻辑」替代，spec 勘误在 Task 9。

**既有约定（来自代码库，照此执行）：**
- 无 Alembic：新表靠 `Base.metadata.create_all()` 启动时自动建。
- Pydantic schema 内联在路由文件（参 `routes/copilot.py`）；单用户无鉴权（`db.scalar(select(User.id).limit(1))`）。
- 后端测试：临时 SQLite + `setup_module`/`teardown_module` + `TestClient`（参 `tests/test_summary_routes.py`，只建本功能表）；Claude 调用在测试里用 mock client（参 `tests/test_ai_service.py`）。
- AI 客户端：`AIService()`（`services/ai_service.py`），`svc.client` / `svc.model` / `svc.is_available`，配置 `settings.anthropic_api_key` / `settings.ai_model` / `settings.ai_daily_token_budget`。
- token 预算：调用前查 `AIFeedback` 当日累计（见 `routes/copilot.py` 模式）；调用后记一条 `AIFeedback(feature="ziwei_oracle", reference_id=profile_id, ...)`。
- Windows PowerShell（`;` 链接命令，无 `&&`）；worktree 分支 `worktree-ziwei-phase3`，只 commit 不 push。

**iztro chart_json 形状（Phase 1 既有，`frontend/src/lib/ziwei/types.ts` ZiweiChart）——后端按此 dict 读：**
```
chart_json = {
  gender, solarDate, lunarDate, chineseDate, time, timeRange, sign, zodiac,
  earthlyBranchOfSoulPalace,   # 命宫地支字符串，如 "子"
  earthlyBranchOfBodyPalace, soul, body, fiveElementsClass,
  palaces: [ {
    index, name,                # 宫名 "命宫".."父母"
    isBodyPalace, isOriginalPalace,
    heavenlyStem, earthlyBranch,  # 地支字符串
    majorStars: [ {name, type, brightness?, mutagen?} ],
    minorStars: [...], adjectiveStars: [...],
    changsheng12, decadal:{range,heavenlyStem,earthlyBranch}, ages
  } x12 ]
}
```
其中 `mutagen ∈ {禄,权,科,忌}` 或缺省；`brightness ∈ {庙,旺,得,利,平,不,陷}` 或缺省。

---

### Task 1: ZiweiConversation + ZiweiMessage 数据模型

**Files:**
- Modify: `backend/app/models/entities.py`（末尾追加两个类）
- Modify: `backend/app/models/__init__.py`（导出，按字母序）
- Test: `backend/tests/test_ziwei_oracle_models.py`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_ziwei_oracle_models.py`：

```python
from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_DIR = Path(mkdtemp(prefix="ziwei-oracle-model-tests-"))
TEST_DATABASE_URL = f"sqlite:///{(TEST_DB_DIR / 'test.db').as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def setup_module():
    from app.models.entities import ZiweiConversation, ZiweiMessage

    ZiweiConversation.__table__.create(bind=engine, checkfirst=True)
    ZiweiMessage.__table__.create(bind=engine, checkfirst=True)


def teardown_module():
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


def test_conversation_and_message_roundtrip():
    from app.models.entities import ZiweiConversation, ZiweiMessage

    db = TestingSessionLocal()
    try:
        conv = ZiweiConversation(profile_id=1, scenario="natal", title="开场解读")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        assert conv.id is not None
        assert conv.scenario == "natal"
        assert conv.created_at is not None

        msg = ZiweiMessage(
            conversation_id=conv.id,
            role="assistant",
            content="命宫紫微……",
            chart_context_json={"focus": "命宫", "year": None},
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        assert msg.id is not None
        assert msg.role == "assistant"
        assert msg.chart_context_json["focus"] == "命宫"
        assert msg.created_at is not None
    finally:
        db.close()
```

- [ ] **Step 2: 运行确认失败** — `cd backend; python -m pytest tests/test_ziwei_oracle_models.py -v` → ImportError

- [ ] **Step 3: 写模型** — `backend/app/models/entities.py` 末尾追加（imports 已含 Integer/String/Text/DateTime/JSON/datetime/Mapped/mapped_column）：

```python
class ZiweiConversation(Base):
    __tablename__ = "ziwei_conversations"
    __table_args__ = (Index("ix_ziwei_conv_profile", "profile_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ZiweiProfile.id
    scenario: Mapped[str] = mapped_column(String(20), default="natal")  # natal, horoscope, synastry, report
    title: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ZiweiMessage(Base):
    __tablename__ = "ziwei_messages"
    __table_args__ = (Index("ix_ziwei_msg_conv", "conversation_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chart_context_json: Mapped[Dict] = mapped_column(JSON, default=dict)  # 当时盘面上下文：focus宫位、流年年份等
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

在 `backend/app/models/__init__.py` 两处（import 列表与 `__all__`）加 `ZiweiConversation`、`ZiweiMessage`（按字母序，在 `ZiweiProfile` 之后）。

- [ ] **Step 4: 运行确认通过** — PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/entities.py backend/app/models/__init__.py backend/tests/test_ziwei_oracle_models.py
git commit -m "feat(ziwei): conversation and message models for AI oracle"
```

---

### Task 2: 命盘适配器 + 格局检测原语

**Files:**
- Create: `backend/app/services/ziwei/__init__.py`（空）
- Create: `backend/app/services/ziwei/chart_model.py`（内部命盘表示 + 适配器）
- Create: `backend/app/services/ziwei/primitives.py`（地支环math + 三方四正等原语）
- Test: `backend/tests/test_ziwei_primitives.py`

**移植要点（务必遵守）：**
1. 仓库用 `branch:int 0-11`、`star.siHua`、`brightness:'bright'|'normal'|'dim'`；iztro 用地支字符串、`mutagen`、中文亮度。适配器负责转换。
2. 仓库把四化当成名为「化禄」的伪星塞进 `sanFangAllStars` 检测（如 `sanFangSet.has('化禄')`）；iztro 没有此伪星。移植时此类判断改用 `san_fang_mutagens(chart)`（三方四正中出现的 mutagen 集合）。**这是最易错点。**
3. 地支→int：`子丑寅卯辰巳午未申酉戌亥` 依次 0-11。
4. 亮度归一：庙/旺→`bright`；得/利/平→`normal`；不/陷→`dim`；缺省→`normal`。
5. `is_major`：来自 iztro `majorStars` 的星 `is_major=True`，其余 False。

- [ ] **Step 1: 写内部命盘表示 + 适配器** — 创建 `backend/app/services/ziwei/chart_model.py`：

```python
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
```

- [ ] **Step 2: 写原语** — 创建 `backend/app/services/ziwei/primitives.py`（忠实移植仓库 helper，但作用于内部 Chart，并补 `san_fang_mutagens`）：

```python
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
```

- [ ] **Step 3: 写测试** — 创建 `backend/tests/test_ziwei_primitives.py`：

```python
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
```

- [ ] **Step 4: 运行确认通过** — `cd backend; python -m pytest tests/test_ziwei_primitives.py -v` → 全 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ziwei/ backend/tests/test_ziwei_primitives.py
git commit -m "feat(ziwei): chart adapter and pattern-detection primitives"
```

---

### Task 3: 格局检测器移植 上半（主星 + 三方 + 四化格局）

**Files:**
- Create: `backend/app/services/ziwei/patterns.py`（Pattern dataclass + 检测器，本任务先放上半 + 占位 detect_patterns）
- Test: `backend/tests/test_ziwei_patterns_core.py`

**源：** `https://raw.githubusercontent.com/Renhuai123/ziwei-doushu/main/lib/ziwei/patterns.ts`（实现前 fetch 该文件取每个检测器的确切逻辑）。移植规则：早返回守卫 + bonus/breaking 累加 → level；`sanFangSet.has('化X')` → `'X' in san_fang_mutagens(chart)`；`s.type==='major'` → `s.is_major`；`getStarSiHua`→`star_mutagen`。**保留每个 Pattern 的 `source` 古籍出处与 `description` 原文（逐字复制，MIT 署名义务）。**

- [ ] **Step 1: 写 Pattern 结构 + 4 个模板检测器（已有逐字源码）**

创建 `backend/app/services/ziwei/patterns.py`：

```python
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
```

- [ ] **Step 2: 写测试** — 创建 `backend/tests/test_ziwei_patterns_core.py`，对每个检测器构造命中/不命中两组 chart_json，断言：

```python
from app.services.ziwei.chart_model import adapt_chart
from app.services.ziwei.patterns import detect_patterns


def _mk(palaces_spec, ming="子", shen="午"):
    """palaces_spec: {地支: ([(主星,四化,亮度)], [辅星名])}; 自动补满12宫。"""
    order = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"]
    branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
    # 让 order[0]=命宫 落在 ming 地支
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


def _names(chart_json):
    return {p.name for p in detect_patterns(adapt_chart(chart_json))}


def test_jun_chen_qing_hui_hit():
    # 命宫子紫微 + 三方(辰/申/午)含左辅右弼
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
```

（实现者：补全每个上半检测器的命中/不命中用例。）

- [ ] **Step 3: 运行确认通过** — 全 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ziwei/patterns.py backend/tests/test_ziwei_patterns_core.py
git commit -m "feat(ziwei): port core star/sihua pattern detectors"
```

---

### Task 4: 格局检测器移植 下半（夹格 + 煞格 + 基础）+ 总编排 + 名盘集成测试

**Files:**
- Modify: `backend/app/services/ziwei/patterns.py`（追加下半检测器，填满 `detect_patterns`）
- Test: `backend/tests/test_ziwei_patterns_full.py`

**实现者必读：** fetch `patterns.ts` 全文，按下表逐字移植剩余 ~37 个检测器（含上半 4 个之外的全部）。每个忠实复制其 `description`/`source`、early-return 守卫、bonus/breaking 逻辑。`sanFangSet.has('化X')`→`san_fang_mutagens`；`s.type==='major'`→`s.is_major`。`detect_patterns` 的调用顺序照 patterns.ts 的 `detectPatterns` 主函数（上格→中格→助力格→恶格→基础格局）。

**完整格局清单（~41，名/触发/level/出处）——逐条移植，不得遗漏：**

| 检测器 | 格局名 | 触发 | level | 出处 |
|---|---|---|---|---|
| jun_chen_qing_hui | 君臣庆会 | 紫微入命+左辅右弼会三方 | excellent/good | 全书·君臣庆会格 |
| zi_fu | 紫府同宫 | 紫微+天府同宫(寅/申优) | excellent/good | 全书·紫府同宫格 |
| fu_xiang_chao_yuan | 府相朝垣 | 天府天相分入三方 | excellent/good | 全书·府相朝垣格 |
| yang_liang_chang_lu | 阳梁昌禄 | 太阳天梁文昌禄存齐会三方 | excellent/good | 全书·阳梁昌禄格 |
| huo_tan_ling_tan | 火贪/铃贪格 | 贪狼+(火星\|铃星)同宫或三方 | excellent/good | 骨髓赋 |
| wu_tan | 武贪格 | 武曲+贪狼同宫(丑/未)或对宫 | excellent/good | 骨髓赋 |
| sha_po_lang | 杀破狼 | 七杀破军贪狼齐会三方 | good/caution | 全书·杀破狼 |
| ji_yue_tong_liang | 机月同梁 | 天机太阴天同天梁齐会 | excellent/good | 全书·机月同梁格 |
| lian_xiang | 廉贞天相格 | 廉贞+天相同宫 | good | 全书 |
| wu_qi_sha | 武曲七杀 | 武曲+七杀同宫 | excellent/good | 全书 |
| tong_liang | 天同天梁格 | 天同+天梁同宫 | good | 全书 |
| ri_yue_tong_gong | 日月同宫 | 太阳+太阴同宫(丑/未) | excellent/good | 全书 |
| ri_yue_jia_ming | 日月夹命 | 太阳太阴夹命前后宫 | excellent/good | 全书·日月夹命 |
| ju_ri_tong_gong | 巨日同宫 | 巨门+太阳同宫(寅/申) | excellent/good | 全书·巨日同宫 |
| shi_zhong_yin_yu | 石中隐玉 | 巨门入命(子/午) | excellent/good | 骨髓赋·石中隐玉 |
| ming_zhu_chu_hai | 明珠出海 | 命未空宫+对宫丑日月 | excellent/good | 全集·明珠出海 |
| zi_wei_in_ming | 紫微入命 | 紫微独坐命(无天府) | excellent/good | 全书 |
| fu_bi_jia_ming | 辅弼夹命 | 左辅右弼夹命前后宫 | excellent | 全书·辅弼夹命 |
| chang_qu_jia_ming | 昌曲夹命 | 文昌文曲夹命前后宫 | excellent | 全书 |
| kui_yue_jia_ming | 魁钺夹命 | 天魁天钺夹命前后宫 | good | 全书 |
| shuang_lu_chao_yuan | 双禄朝垣 | 化禄+禄存同会三方 | excellent | 全书·双禄朝垣 |
| san_qi_jia_hui | 三奇加会 | 化禄化权化科齐会三方 | excellent | 全书·三奇加会 |
| hua_lu_ru_ming | X化禄入命 | 主星化禄坐命 | good | 全书 |
| hua_ji_ru_ming_qian | X化忌入命/迁 | 主星化忌坐命或迁 | caution | 全书 |
| yang_tuo_jia_ji | 羊陀夹忌 | 化忌坐命+擎羊陀罗夹命 | caution | 骨髓赋·羊陀夹忌 |
| huo_ling_jia_ming | 火铃夹命 | 火星铃星夹命前后宫 | caution | 全书 |
| kong_jie_jia_ming | 空劫夹命 | 地空地劫夹命前后宫 | caution | 全书 |
| lian_sha_yang | 廉杀羊 | 廉贞七杀擎羊会三方 | caution | 全书·廉杀羊 |
| ju_huo_yang | 巨火羊 | 巨门火星擎羊会三方 | caution | 骨髓赋·巨火羊 |
| ling_chang_tuo_wu | 铃昌陀武 | 铃星文昌陀罗武曲会 | caution | 骨髓赋·铃昌陀武 |
| ma_tou_dai_jian | 马头带箭 | 擎羊午宫坐命 | caution/good | 骨髓赋·马头带箭 |
| lu_cun_shou_shen | 禄存守命/身 | 禄存坐命或身 | good | 全书·禄存星 |
| tian_ma_ru_ming | 天马入命/迁 | 天马坐命或迁 | neutral | 全书·天马星 |
| hua_lu_ru_cai | 化禄入财 | 财帛宫主星化禄 | good | 全书·四化论 |
| hua_quan_ru_guan | 化权入官 | 官禄宫主星化权 | good | 全书·四化论 |
| hua_ke_ru_ming_shen | 化科入命/身 | 命或身宫主星化科 | good | 全书·四化论 |
| ji_yue_tong_liang_partial | 机月同梁三星会 | 天机太阴天同天梁任3齐会 | neutral | 全书（降级版） |
| chang_qu_tong_hui | 昌曲同会 | 文昌文曲同会三方 | good | 全书·文星论 |
| fu_bi_tong_hui | 辅弼同会 | 左辅右弼同会三方 | good | 全书·辅弼论 |
| kui_yue_tong_hui | 魁钺同会 | 天魁天钺同会三方 | good | 全书·魁钺论 |
| ke_quan_shuang_hui | 科权双会 | 化科+化权同会三方 | good | 全书·四化会照 |

注：上半已实现 jun_chen_qing_hui / sha_po_lang / yang_liang_chang_lu / san_qi_jia_hui，本任务实现其余。`fu_bi_jia_ming` / `yang_tuo_jia_ji` / `hua_lu_ru_ming` 的逐字源码已在计划附录给出（见下），照其 Python 化模板移植；其余按 patterns.ts fetch 逐字移植。

**附录·三个有逐字源码的检测器（Python 移植模板）：**

```python
def detect_fu_bi_jia_ming(chart: Chart, out: list[Pattern]) -> None:
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


def detect_yang_tuo_jia_ji(chart: Chart, out: list[Pattern]) -> None:
    for palace in chart.palaces:
        if palace.branch != chart.ming_branch:
            continue
        if not any(s.mutagen == "忌" for s in palace.stars):
            continue
        prev, nxt = jia_palaces(chart, palace.branch)
        if not prev or not nxt:
            continue
        a = has_star(prev, "擎羊") and has_star(nxt, "陀罗")
        b = has_star(prev, "陀罗") and has_star(nxt, "擎羊")
        if not a and not b:
            continue
        out.append(Pattern(
            name="羊陀夹忌", level="caution",
            description="化忌坐命，左右擎羊陀罗夹命，古书云“羊陀夹忌为败局”，主一生劳碌奔波、坎坷不顺、身心俱疲。需以德行修养与积极做事化解，凡事谨慎为上。",
            palaces=["命宫", prev.name, nxt.name], source="《紫微斗数骨髓赋·羊陀夹忌》",
            required=["化忌坐命", "擎羊陀罗分居命宫前后两宫"],
        ))
        return


def detect_hua_lu_ru_ming(chart: Chart, ming: Palace, out: list[Pattern]) -> None:
    star = next((s for s in ming.stars if s.mutagen == "禄" and s.is_major), None)
    if not star:
        return
    extra = {"武曲": "武曲化禄属正财，宜实业、金融。", "太阴": "太阴化禄属阴财、不动产。",
             "贪狼": "贪狼化禄属人脉财、桃花财。"}.get(star.name, "")
    out.append(Pattern(
        name=f"{star.name}化禄入命", level="good",
        description=f"{star.name}化禄坐命，主生财顺利、人缘佳、机缘多。{extra}",
        palaces=["命宫"], source="《紫微斗数全书》",
        required=[f"{star.name}化禄坐命宫"],
    ))
```

- [ ] **Step 1: fetch patterns.ts 并移植下半全部检测器**，填满 `detect_patterns` 调用序列（照 patterns.ts 主函数顺序）。

- [ ] **Step 2: 写集成测试** — 创建 `backend/tests/test_ziwei_patterns_full.py`：

```python
import json
import subprocess
from pathlib import Path

from app.services.ziwei.chart_model import adapt_chart
from app.services.ziwei.patterns import detect_patterns


def test_detector_count_and_no_crash_on_known_chart():
    """用 iztro 真实排出的名盘（前端冒烟脚本同一盘：2000-8-16 寅时 女）跑全检测，断言不崩、返回 Pattern 列表，且每个 Pattern 字段完整。"""
    chart_json = json.loads((Path(__file__).parent / "fixtures" / "chart_2000_0816_yin_female.json").read_text(encoding="utf-8"))
    patterns = detect_patterns(adapt_chart(chart_json))
    assert isinstance(patterns, list)
    for p in patterns:
        assert p.name and p.level in {"excellent", "good", "neutral", "caution"}
        assert p.source  # 古籍出处非空
        assert isinstance(p.palaces, list)


def test_all_detectors_registered():
    """detect_patterns 注册的检测器数 ≥ 38（清单 41，容许个别合并）。"""
    import app.services.ziwei.patterns as P
    detector_fns = [n for n in dir(P) if n.startswith("detect_") and n != "detect_patterns"]
    assert len(detector_fns) >= 38
```

集成测试需要一份真实 chart_json fixture。**生成方式（实现者执行）**：临时改 `frontend/scripts/ziwei-smoke.cjs` 末尾加 `require("fs").writeFileSync("../backend/tests/fixtures/chart_2000_0816_yin_female.json", JSON.stringify(...computeChart 结果..., null, 2))`——但 smoke 脚本用的是 iztro 原始 astrolabe，不是归一化 ZiweiChart。**更可靠**：新建一次性脚本 `frontend/scripts/dump-chart.cjs`，`require` 编译后的 `computeChart`（或直接复刻其归一化逻辑，调 `astro.bySolar("2000-8-16",2,"女",true,"zh-CN")` 后按 `lib/ziwei/chart.ts` 的 toPalace 映射输出归一化 dict），写入 `backend/tests/fixtures/`。该 fixture 入库（小文件，确定性）。脚本本身可留作再生成工具。若工具链阻塞，退而用 Task 3 的 `_mk` 合成 3-4 张盘各命中已知格局并断言它们出现 + `test_all_detectors_registered` 保证移植完整性（实现者择一，在汇报中说明选了哪条及原因）。

- [ ] **Step 3: 运行确认通过** — 全 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ziwei/patterns.py backend/tests/test_ziwei_patterns_full.py backend/tests/fixtures/
git commit -m "feat(ziwei): complete pattern detector port (41 patterns) with orchestrator"
```

---

### Task 5: 三人设 prompt + 命盘摘要格式化器

**Files:**
- Create: `backend/app/services/ziwei/personas.py`
- Create: `backend/app/services/ziwei/chart_summary.py`
- Test: `backend/tests/test_ziwei_summary.py`

- [ ] **Step 1: 写人设** — 创建 `backend/app/services/ziwei/personas.py`：

```python
"""AI 解盘师三种人设 system prompt 片段。ZiweiProfile.persona ∈ {sage, taoist, analyst}。"""

PERSONAS: dict[str, dict] = {
    "sage": {
        "label": "温和智者",
        "prompt": (
            "你是一位博学而亲切的紫微斗数先生。专业术语随手用白话解释，既讲格局也讲人生建议；"
            "不装神弄秘，也不吐槽迷信。语气温润、有条理，像长辈与你围炉夜话。"
        ),
    },
    "taoist": {
        "label": "仙风道骨",
        "prompt": (
            "你是一位仙风道骨的命理隐士。用半文半白的语体，称呼对方为「命主」，适度引经据典（骨髓赋、全书）。"
            "言简意赅、点到为止，留三分余韵让命主自悟。不堆砌辞藻，重在意境与机锋。"
        ),
    },
    "analyst": {
        "label": "现代分析师",
        "prompt": (
            "你是一位理性克制的命盘分析师，像写一份结构化人格报告。用「倾向性」「能量分布」「概率」这类词，"
            "弱化吉凶断语，强调命盘是参考框架而非定论。条理清晰、善用要点，给可执行的观察与建议。"
        ),
    },
}

DEFAULT_PERSONA = "sage"


def persona_prompt(persona: str) -> str:
    return PERSONAS.get(persona, PERSONAS[DEFAULT_PERSONA])["prompt"]
```

- [ ] **Step 2: 写命盘摘要格式化器** — 创建 `backend/app/services/ziwei/chart_summary.py`（把 chart_json + 命中格局压成紧凑中文文本，供 system prompt 注入）：

```python
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
```

- [ ] **Step 3: 写测试** — `backend/tests/test_ziwei_summary.py`：断言摘要含基本信息、十二宫名、命中格局名与出处；人设 prompt 三种各返回非空且不同。

- [ ] **Step 4: 运行 + Commit**

```bash
git add backend/app/services/ziwei/personas.py backend/app/services/ziwei/chart_summary.py backend/tests/test_ziwei_summary.py
git commit -m "feat(ziwei): three personas and chart-summary formatter for oracle prompt"
```

---

### Task 6: ziwei_oracle.py —— oracle 循环（tool_use，非流式）

**Files:**
- Create: `backend/app/services/ziwei/oracle.py`
- Create: `backend/app/services/ziwei/oracle_tools.py`
- Test: `backend/tests/test_ziwei_oracle.py`

设计：复刻 `copilot_loop.py` 的多轮 tool_use 编排（`stop_reason=='tool_use'` → 执行 → 回填 → continue）。工具是**镜头/UI 指令**——执行即「记录这条指令」（本期不真正动画），结果回 ack。返回 `{response, camera_commands[], _meta}`。

- [ ] **Step 1: 写工具** — `backend/app/services/ziwei/oracle_tools.py`：

```python
"""Oracle 镜头/UI 工具：Claude 调用以驱动 3D（消费在 Phase 3b；本期仅收集指令）。"""
from __future__ import annotations

VALID_PALACES = {"命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母"}

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "focus_palace",
        "description": "把 3D 镜头飞入并聚焦到命主某一宫位。当你的解读聚焦到某宫时调用，让画面跟随你的话语。",
        "input_schema": {
            "type": "object",
            "properties": {"palace": {"type": "string", "description": "宫位名，如 命宫、官禄、夫妻"}},
            "required": ["palace"],
        },
    },
    {
        "name": "overview",
        "description": "把镜头拉回整盘总览。在开场总评、或从单宫话题回到全局时调用。",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "explain_term",
        "description": "为一个紫微术语弹出白话解释卡片，帮助不懂命理的用户。",
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "string"}, "explanation": {"type": "string", "description": "一句话白话解释"}},
            "required": ["term", "explanation"],
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> dict:
    """执行（=校验并回 ack）。真正的动画消费在前端。返回结构化指令供路由收集。"""
    if name == "focus_palace":
        palace = tool_input.get("palace", "")
        if palace not in VALID_PALACES:
            return {"ok": False, "error": f"未知宫位：{palace}"}
        return {"ok": True, "command": {"type": "focus_palace", "palace": palace}}
    if name == "overview":
        return {"ok": True, "command": {"type": "overview"}}
    if name == "explain_term":
        return {"ok": True, "command": {"type": "explain_term", "term": tool_input.get("term", ""), "explanation": tool_input.get("explanation", "")}}
    return {"ok": False, "error": f"未知工具：{name}"}
```

- [ ] **Step 2: 写 oracle 循环** — `backend/app/services/ziwei/oracle.py`：

```python
"""紫微 AI 解盘循环：仿 copilot_loop 的非流式 tool_use 编排。
组装 人设 + 命盘摘要(含命中格局) + 画像 + 近期事件 → Claude，收集镜头指令。"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from .chart_summary import format_chart_summary
from .oracle_tools import TOOL_SCHEMAS, execute_tool
from .personas import persona_prompt

SCENARIO_FRAMES = {
    "natal": "本命盘解读：以命宫与三方四正立论，兼及十二宫，给出命格总览与人生倾向。",
    "horoscope": "大限/流年解读：以大限定基调、流年看应期，结合命盘格局推演近期运势。",
    "synastry": "合盘解读：比较两人命盘，看夫妻/交友/事业宫与四化交涉，论契合与磨合。",
    "report": "结构化报告：分维度（事业/感情/财运/健康）系统梳理，条理清晰可回看。",
}


class ZiweiOracle:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def _system_prompt(self, chart_json: dict, persona: str, scenario: str, portrait: dict) -> str:
        parts = [
            persona_prompt(persona),
            "\n\n你正在为命主解读一张紫微斗数命盘。下面是排好的盘面与确定性规则检测出的命中格局——"
            "格局部分是程序精确判定的，请务必尊重、不要漏讲或臆造未命中的格局；逐星逐宫的细致论断由你的学养发挥。\n",
            SCENARIO_FRAMES.get(scenario, SCENARIO_FRAMES["natal"]),
            "\n\n" + format_chart_summary(chart_json),
        ]
        if portrait:
            parts.append("\n\n【命主画像】（往次解读沉淀，供延续语境）\n" + json.dumps(portrait, ensure_ascii=False))
        parts.append(
            "\n\n## 镜头联动\n讲到某一宫时调用 focus_palace(该宫) 让 3D 画面飞入；回到全局时 overview()；"
            "遇到生僻术语可用 explain_term 给白话卡。镜头服务于叙述，不必频繁。\n"
            "## 输出\n用清晰中文解读，可读性优先。不要输出 JSON 或代码块，正常说话即可。"
        )
        return "".join(parts)

    def run(
        self,
        chart_json: dict,
        persona: str,
        scenario: str,
        portrait: dict,
        messages: list[dict],
        max_rounds: int = 4,
    ) -> Optional[dict]:
        system_prompt = self._system_prompt(chart_json, persona, scenario, portrait)
        claude_messages = messages[-10:] if len(messages) > 10 else list(messages)
        camera_commands: list[dict] = []
        in_tok = out_tok = 0
        start = time.time()

        for round_num in range(1, max_rounds + 1):
            try:
                response = self.client.messages.create(
                    model=self.model, max_tokens=2200, system=system_prompt,
                    messages=claude_messages, tools=TOOL_SCHEMAS, timeout=40.0,
                )
            except Exception:
                return None
            in_tok += response.usage.input_tokens
            out_tok += response.usage.output_tokens

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        out = execute_tool(block.name, block.input)
                        if out.get("ok") and "command" in out:
                            camera_commands.append(out["command"])
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out, ensure_ascii=False)})
                claude_messages.append({"role": "assistant", "content": response.content})
                claude_messages.append({"role": "user", "content": tool_results})
                continue

            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return {
                "response": text,
                "camera_commands": camera_commands,
                "_meta": {
                    "model": self.model, "input_tokens": in_tok, "output_tokens": out_tok,
                    "total_tokens": in_tok + out_tok, "latency_ms": int((time.time() - start) * 1000),
                    "rounds": round_num,
                },
            }
        return None
```

- [ ] **Step 3: 写测试**（mock client，仿 `tests/test_ai_service.py`）— `backend/tests/test_ziwei_oracle.py`：构造假 Anthropic client，先返回一个 `tool_use`（focus_palace 官禄）再返回 text，断言 `camera_commands` 收集到 `{type:"focus_palace", palace:"官禄"}` 且 `response` 为文本；断言 system prompt 含命盘摘要与人设。用 fake 对象模拟 `response.content`/`stop_reason`/`usage`。

- [ ] **Step 4: 运行 + Commit**

```bash
git add backend/app/services/ziwei/oracle.py backend/app/services/ziwei/oracle_tools.py backend/tests/test_ziwei_oracle.py
git commit -m "feat(ziwei): oracle tool_use loop with camera-command collection"
```

---

### Task 7: oracle 路由（持久化 + 预算 + 人设）

**Files:**
- Modify: `backend/app/api/v1/routes/ziwei.py`（追加 oracle 端点 + 对话/消息端点）
- Test: `backend/tests/test_ziwei_oracle_routes.py`

端点：
- `POST /ziwei/profiles/{profile_id}/oracle` — body `{scenario, message, conversation_id?}`。流程：取 profile → 预算检查（AIFeedback 当日累计，超则 429）→ AIService 不可用则 503 → 取/建 conversation → 历史消息装入 → 存 user message → 调 `ZiweiOracle.run` → 存 assistant message（chart_context_json 存 camera_commands）→ 记 AIFeedback(feature="ziwei_oracle", reference_id=profile_id) → 返回 `{conversation_id, response, camera_commands, _meta}`。
- `GET /ziwei/profiles/{profile_id}/conversations` — 列出该档案会话。
- `GET /ziwei/conversations/{conversation_id}/messages` — 列出消息（供 3b 历史回看）。

- [ ] **Step 1: 写失败测试** — `backend/tests/test_ziwei_oracle_routes.py`：建 ZiweiProfile + ZiweiConversation + ZiweiMessage + User + AIFeedback 表；用 `monkeypatch` 把 `AIService` 换成 mock（`is_available=True`，`client` 返回预置 text 响应，`model="test"`）；POST oracle 断言 200、返回 response、conversation_id，且消息已持久化；再 GET conversations / messages 断言能取回。预算超限用例：预先插入 AIFeedback 使当日 token ≥ budget，断言 429。

- [ ] **Step 2: 写路由** — 在 `routes/ziwei.py` 追加（复用文件已有 imports + 加 `from app.services.ziwei.oracle import ZiweiOracle`、`from app.services.ai_service import AIService`、`from app.models.entities import ZiweiConversation, ZiweiMessage, AIFeedback, User`、`from datetime import date, datetime`、`from sqlalchemy import func`）：

```python
class OracleRequest(BaseModel):
    scenario: str = "natal"
    message: str
    conversation_id: Optional[int] = None


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1))


@router.post("/profiles/{profile_id}/oracle")
def ask_oracle(profile_id: int, payload: OracleRequest, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if not (profile.chart_json or {}).get("palaces"):
        raise HTTPException(400, "Profile has no chart data")

    from app.core.config import get_settings
    settings = get_settings()
    svc = AIService()
    if not svc.is_available:
        raise HTTPException(503, "AI oracle is not available — no API key configured")

    today_start = datetime.combine(date.today(), datetime.min.time())
    used_today = db.scalar(
        select(func.coalesce(func.sum(AIFeedback.input_tokens + AIFeedback.output_tokens), 0)).where(AIFeedback.created_at >= today_start)
    ) or 0
    if used_today >= settings.ai_daily_token_budget:
        raise HTTPException(429, "Daily AI limit reached, try again tomorrow")

    if payload.conversation_id:
        conv = db.get(ZiweiConversation, payload.conversation_id)
        if not conv or conv.profile_id != profile_id:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = ZiweiConversation(profile_id=profile_id, scenario=payload.scenario, title=payload.message[:40])
        db.add(conv)
        db.commit()
        db.refresh(conv)

    history = db.scalars(select(ZiweiMessage).where(ZiweiMessage.conversation_id == conv.id).order_by(ZiweiMessage.id.asc())).all()
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": payload.message})

    db.add(ZiweiMessage(conversation_id=conv.id, role="user", content=payload.message, chart_context_json={}))
    db.commit()

    oracle = ZiweiOracle(client=svc.client, model=svc.model)
    result = oracle.run(
        chart_json=profile.chart_json, persona=profile.persona, scenario=payload.scenario,
        portrait=profile.portrait_json or {}, messages=messages,
    )
    if result is None:
        raise HTTPException(502, "解盘师一时失神，请稍后再问。")

    meta = result["_meta"]
    db.add(ZiweiMessage(
        conversation_id=conv.id, role="assistant", content=result["response"],
        chart_context_json={"camera_commands": result["camera_commands"], "scenario": payload.scenario},
    ))
    db.add(AIFeedback(
        user_id=_get_user_id(db), feature="ziwei_oracle", reference_id=profile_id,
        user_input_hash="", prompt_template=None,
        response_json={"response": result["response"], "camera_commands": result["camera_commands"]},
        model=meta.get("model"), input_tokens=meta.get("input_tokens"),
        output_tokens=meta.get("output_tokens"), latency_ms=meta.get("latency_ms"),
    ))
    db.commit()

    return {
        "conversation_id": conv.id, "response": result["response"],
        "camera_commands": result["camera_commands"], "meta": meta,
    }


@router.get("/profiles/{profile_id}/conversations")
def list_conversations(profile_id: int, db: Session = Depends(get_db)):
    convs = db.scalars(select(ZiweiConversation).where(ZiweiConversation.profile_id == profile_id).order_by(ZiweiConversation.id.desc())).all()
    return [{"id": c.id, "scenario": c.scenario, "title": c.title, "created_at": c.created_at.isoformat() if c.created_at else None} for c in convs]


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, db: Session = Depends(get_db)):
    msgs = db.scalars(select(ZiweiMessage).where(ZiweiMessage.conversation_id == conversation_id).order_by(ZiweiMessage.id.asc())).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "chart_context_json": m.chart_context_json or {}, "created_at": m.created_at.isoformat() if m.created_at else None} for m in msgs]
```

- [ ] **Step 3: 运行确认通过 + 全量后端回归** — `cd backend; python -m pytest tests/ --ignore=tests/test_api.py -q`

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routes/ziwei.py backend/tests/test_ziwei_oracle_routes.py
git commit -m "feat(ziwei): oracle endpoint with conversation persistence and budget guard"
```

---

### Task 8: 极简「问解盘师」面板（前端验证）

**Files:**
- Modify: `frontend/src/lib/ziwei/api.ts`（加 oracle API 方法 + 类型）
- Create: `frontend/src/components/ziwei/oracle-probe.tsx`（极简：输入框 + 发送 + 回复区 + 镜头指令日志）
- Modify: `frontend/src/app/ziwei/page.tsx`（命盘下方挂 OraclePanel，仅当有 chart）

**注意：** 这是**临时验证面板**，Phase 3b 会用真正的三态对话坞替换。保持极简，别投入打磨。

- [ ] **Step 1: 加 API** — `frontend/src/lib/ziwei/api.ts` 追加：

```typescript
export type CameraCommand =
  | { type: "focus_palace"; palace: string }
  | { type: "overview" }
  | { type: "explain_term"; term: string; explanation: string };

export type OracleReply = {
  conversation_id: number;
  response: string;
  camera_commands: CameraCommand[];
  meta: { model?: string; total_tokens?: number; latency_ms?: number; rounds?: number };
};

// 在 ziweiApi 对象中追加：
//   askOracle: (profileId, body) => request<OracleReply>(`/ziwei/profiles/${profileId}/oracle`, { method: "POST", body: JSON.stringify(body) }),
// body 形如 { scenario: "natal", message, conversation_id? }
```

（实现者把 `askOracle` 加入现有 `ziweiApi` 对象，沿用 `request<T>` 包装与 `ZiweiApiError`。）

- [ ] **Step 2: 写探针面板** — `frontend/src/components/ziwei/oracle-probe.tsx`：`"use client"`，单输入框 + 「问解盘师」按钮，loading 态，回复 markdown 文本区，下方小字列出本次 `camera_commands`（如 `镜头→官禄`）。维持 `conversation_id` 续聊。错误用 `ZiweiApiError`→「解盘暂不可用」。极简 violet 暗色风格与现有一致。

- [ ] **Step 3: 接入页面** — `page.tsx` 在 `<ChartView>` 之后、有 `chart` 时渲染 `<OracleProbe profileId={selected.id} />`。

- [ ] **Step 4: 验证** — `cd frontend; npx tsc --noEmit; npm run build` 均过，`/ziwei` 仍在路由表。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/ziwei/api.ts frontend/src/components/ziwei/oracle-probe.tsx frontend/src/app/ziwei/page.tsx
git commit -m "feat(ziwei): minimal oracle probe panel for backend verification"
```

---

### Task 9: 收尾——spec 勘误 + 全量验证 + E2E + 最终审查

- [ ] **Step 1: spec 勘误** — `docs/superpowers/specs/2026-06-09-ziwei-3d-design.md` §7：把「提取 patterns.json（格局规则库）」改为「移植 patterns.ts 的格局检测逻辑为 Python（仓库提供的是检测函数而非数据；逐星逐宫论断库不存在，由 Claude 自身知识承担，格局检测器自带古籍出处提供引证）」；§6 注明知识地基为「命盘摘要 + 确定性格局检测 + 人设」。

- [ ] **Step 2: 全量验证**
```
cd backend; python -m pytest tests/ --ignore=tests/test_api.py -q     → 全 PASS
cd frontend; npx tsc --noEmit                                          → 无错误
cd frontend; npm run build                                             → 无错误
```

- [ ] **Step 3: 实盘 E2E（controller 用临时 Postgres + ANTHROPIC_API_KEY）** — 起后端（需真 key 才能调 Claude）、起前端 dev，建档后在探针面板问「这个盘事业如何？」，断言：返回中文解读、`camera_commands` 含至少一个 `focus_palace`、对话持久化（刷新后 GET messages 能取回）。若本地无 key，则跳过实盘、仅以单测覆盖 oracle 逻辑并在汇报注明。

- [ ] **Step 4: 提交遗留 + 汇报**
```bash
git add -A
git commit -m "chore(ziwei): phase 3a spec errata and final polish"
```
汇报：测试结果、格局检测器实际移植数、E2E 情况、与计划偏差。

---

## Phase 3b 衔接（不在本计划）

- **流式**：把 oracle 端点升级为 SSE（token 增量 + camera 事件），前端三态对话坞消费。
- **镜头联动**：`camera_commands` 的 `focus_palace` → 转地支 → set Phase 2 的 `selectedBranch` → 一镜到底飞入。
- **对话坞三态 + 人设切换 UI + 历史回看**：替换本期的极简探针面板。
- **记忆蒸馏**（属 Phase 4）：会话结束异步把要点蒸馏进 `portrait_json`。
