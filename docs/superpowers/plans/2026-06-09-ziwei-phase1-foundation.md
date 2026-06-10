# 紫微斗数 Phase 1（基座）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AIEngineerPortal 中落地紫微斗数板块的基座——命主档案数据模型与 CRUD API、浏览器内 iztro 排盘、2D 暗夜命盘渲染、sidebar 入口。

**Architecture:** 前端用 iztro（npm）在浏览器内毫秒级排盘，归一化为自有 `ZiweiChart` JSON 后存入后端 `ZiweiProfile` 档案表；后端只做存储与校验（FastAPI + SQLAlchemy，沿用现有单用户模式）；2D 命盘为 CSS Grid 4×4 暗夜风格方盘，将来作为 WebGL 不可用时的兜底。

**Tech Stack:** iztro 2.5.x、Next.js 15 + React 19、TailwindCSS、FastAPI + SQLAlchemy 2.0、pytest。

**Spec:** `docs/superpowers/specs/2026-06-09-ziwei-3d-design.md`（§5 数据模型、§9 降级、§11 分期第 1 条）

**约定（来自代码库现状，照此执行，勿自创）：**
- 无 Alembic：新表靠 `Base.metadata.create_all()` 在应用启动时自动创建（`backend/app/main.py` lifespan 已有），**不需要写迁移**。
- Pydantic schema 内联写在路由文件里（参照 `backend/app/api/v1/routes/memory.py`）。
- 单用户系统、无鉴权。
- 后端测试用临时 SQLite + `setup_module`/`teardown_module` + `TestClient`（参照 `backend/tests/test_summary_routes.py`，只建本功能的表）。
- 前端无测试框架：用 `npx tsc --noEmit`、`npm run build` 和冒烟脚本验证。
- 前端组件文件名 kebab-case；数据获取用 `useEffect`+`useState`（不用 TanStack Query）。

---

### Task 1: ZiweiProfile 数据模型

**Files:**
- Modify: `backend/app/models/entities.py`（文件末尾追加）
- Modify: `backend/app/models/__init__.py`（导出 ZiweiProfile，照现有列表风格）
- Test: `backend/tests/test_ziwei_models.py`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_ziwei_models.py`：

```python
from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_DIR = Path(mkdtemp(prefix="ziwei-model-tests-"))
TEST_DATABASE_URL = f"sqlite:///{(TEST_DB_DIR / 'test.db').as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def setup_module():
    from app.models.entities import ZiweiProfile

    ZiweiProfile.__table__.create(bind=engine, checkfirst=True)


def teardown_module():
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


def test_ziwei_profile_roundtrip():
    from app.models.entities import ZiweiProfile

    db = TestingSessionLocal()
    try:
        profile = ZiweiProfile(
            name="测试命主",
            relation="self",
            gender="female",
            birth_date="2000-08-16",
            birth_time_index=2,
            chart_json={"palaces": [{"name": "命宫"}]},
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        assert profile.id is not None
        assert profile.persona == "sage"  # 默认人设
        assert profile.is_lunar_input is False
        assert profile.is_leap_month is False
        assert profile.portrait_json == {}
        assert profile.chart_json["palaces"][0]["name"] == "命宫"
        assert profile.created_at is not None
    finally:
        db.close()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend; python -m pytest tests/test_ziwei_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'ZiweiProfile'`

- [ ] **Step 3: 写模型**

在 `backend/app/models/entities.py` 文件末尾追加（imports 已齐全，无需新增）：

```python
class ZiweiProfile(Base):
    __tablename__ = "ziwei_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    relation: Mapped[str] = mapped_column(String(20), default="self")  # self, family, friend
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # male, female
    birth_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD（农历输入时为农历 Y-M-D）
    birth_time_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 时辰 0-12（0=早子时, 12=晚子时）
    is_lunar_input: Mapped[bool] = mapped_column(Boolean, default=False)
    is_leap_month: Mapped[bool] = mapped_column(Boolean, default=False)
    chart_json: Mapped[Dict] = mapped_column(JSON, default=dict)  # 归一化 ZiweiChart（前端 iztro 排盘结果）
    persona: Mapped[str] = mapped_column(String(20), default="sage")  # sage, taoist, analyst
    portrait_json: Mapped[Dict] = mapped_column(JSON, default=dict)  # AI 蒸馏画像（Phase 4 使用）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

然后在 `backend/app/models/__init__.py` 中加入 `ZiweiProfile`（两处，均按字母序插在 `UserExerciseAttempt` 之后）：

```python
from app.models.entities import (
    ...,
    UserExerciseAttempt,
    ZiweiProfile,
)

__all__ = [
    ...,
    "UserExerciseAttempt",
    "ZiweiProfile",
]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend; python -m pytest tests/test_ziwei_models.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/entities.py backend/app/models/__init__.py backend/tests/test_ziwei_models.py
git commit -m "feat(ziwei): ZiweiProfile model for natal chart archives"
```

---

### Task 2: 档案 CRUD 路由

**Files:**
- Create: `backend/app/api/v1/routes/ziwei.py`
- Modify: `backend/app/api/v1/api.py`（导入并注册 router）
- Test: `backend/tests/test_ziwei_routes.py`

- [ ] **Step 1: 写失败测试**

创建 `backend/tests/test_ziwei_routes.py`：

```python
from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import get_db
from app.main import app
from app.models.entities import ZiweiProfile

TEST_DB_DIR = Path(mkdtemp(prefix="ziwei-route-tests-"))
TEST_DATABASE_URL = f"sqlite:///{(TEST_DB_DIR / 'test.db').as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module():
    # 只建 ziwei_profiles 表——其他表含 SQLite 不支持的列类型
    ZiweiProfile.__table__.create(bind=engine, checkfirst=True)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


client = TestClient(app)

VALID_PAYLOAD = {
    "name": "妈妈",
    "relation": "family",
    "gender": "female",
    "birth_date": "1965-03-12",
    "birth_time_index": 4,
    "is_lunar_input": False,
    "is_leap_month": False,
    "chart_json": {"palaces": [{"name": "命宫", "earthlyBranch": "子"}], "fiveElementsClass": "水二局"},
}


def test_list_profiles_empty():
    response = client.get("/api/v1/ziwei/profiles")
    assert response.status_code == 200
    assert response.json() == []


def test_create_profile():
    response = client.post("/api/v1/ziwei/profiles", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] > 0
    assert body["name"] == "妈妈"
    assert body["persona"] == "sage"
    assert body["chart_json"]["fiveElementsClass"] == "水二局"


def test_create_profile_rejects_bad_time_index():
    response = client.post("/api/v1/ziwei/profiles", json={**VALID_PAYLOAD, "birth_time_index": 13})
    assert response.status_code == 400


def test_create_profile_rejects_bad_gender():
    response = client.post("/api/v1/ziwei/profiles", json={**VALID_PAYLOAD, "gender": "other"})
    assert response.status_code == 400


def test_create_profile_rejects_bad_birth_date():
    response = client.post("/api/v1/ziwei/profiles", json={**VALID_PAYLOAD, "birth_date": "not-a-date"})
    assert response.status_code == 400


def test_get_update_delete_profile():
    created = client.post("/api/v1/ziwei/profiles", json=VALID_PAYLOAD).json()
    pid = created["id"]

    got = client.get(f"/api/v1/ziwei/profiles/{pid}")
    assert got.status_code == 200
    assert got.json()["name"] == "妈妈"

    updated = client.put(f"/api/v1/ziwei/profiles/{pid}", json={"persona": "taoist", "name": "母亲"})
    assert updated.status_code == 200
    assert updated.json()["persona"] == "taoist"
    assert updated.json()["name"] == "母亲"

    bad_persona = client.put(f"/api/v1/ziwei/profiles/{pid}", json={"persona": "wizard"})
    assert bad_persona.status_code == 400

    deleted = client.delete(f"/api/v1/ziwei/profiles/{pid}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/ziwei/profiles/{pid}").status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend; python -m pytest tests/test_ziwei_routes.py -v`
Expected: FAIL — `test_list_profiles_empty` 返回 404（路由不存在）

- [ ] **Step 3: 写路由**

创建 `backend/app/api/v1/routes/ziwei.py`：

```python
"""Ziwei Dou Shu (紫微斗数) profile endpoints."""
import re
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import ZiweiProfile

router = APIRouter(prefix="/ziwei", tags=["ziwei"])

VALID_RELATIONS = {"self", "family", "friend"}
VALID_GENDERS = {"male", "female"}
VALID_PERSONAS = {"sage", "taoist", "analyst"}
BIRTH_DATE_PATTERN = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")


class ProfileCreate(BaseModel):
    name: str
    relation: str = "self"
    gender: str
    birth_date: str
    birth_time_index: int
    is_lunar_input: bool = False
    is_leap_month: bool = False
    chart_json: Dict = {}


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    relation: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    birth_time_index: Optional[int] = None
    is_lunar_input: Optional[bool] = None
    is_leap_month: Optional[bool] = None
    chart_json: Optional[Dict] = None
    persona: Optional[str] = None


def _validate(field: str, value, allowed=None) -> None:
    if field == "birth_time_index" and not 0 <= value <= 12:
        raise HTTPException(400, "birth_time_index must be 0-12")
    if field == "birth_date" and not BIRTH_DATE_PATTERN.match(value):
        raise HTTPException(400, "birth_date must be YYYY-M-D")
    if allowed is not None and value not in allowed:
        raise HTTPException(400, f"{field} must be one of {sorted(allowed)}")


def _profile_out(p: ZiweiProfile) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "relation": p.relation,
        "gender": p.gender,
        "birth_date": p.birth_date,
        "birth_time_index": p.birth_time_index,
        "is_lunar_input": p.is_lunar_input,
        "is_leap_month": p.is_leap_month,
        "chart_json": p.chart_json or {},
        "persona": p.persona,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.scalars(select(ZiweiProfile).order_by(ZiweiProfile.id.asc())).all()
    return [_profile_out(p) for p in profiles]


@router.post("/profiles")
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    _validate("relation", payload.relation, VALID_RELATIONS)
    _validate("gender", payload.gender, VALID_GENDERS)
    _validate("birth_time_index", payload.birth_time_index)
    _validate("birth_date", payload.birth_date)

    profile = ZiweiProfile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_out(profile)


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return _profile_out(profile)


@router.put("/profiles/{profile_id}")
def update_profile(profile_id: int, payload: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    updates = payload.model_dump(exclude_unset=True)
    if "relation" in updates:
        _validate("relation", updates["relation"], VALID_RELATIONS)
    if "gender" in updates:
        _validate("gender", updates["gender"], VALID_GENDERS)
    if "persona" in updates:
        _validate("persona", updates["persona"], VALID_PERSONAS)
    if "birth_time_index" in updates:
        _validate("birth_time_index", updates["birth_time_index"])
    if "birth_date" in updates:
        _validate("birth_date", updates["birth_date"])

    for key, value in updates.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return _profile_out(profile)


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    profile = db.get(ZiweiProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    db.delete(profile)
    db.commit()
    return {"deleted": profile_id}
```

注册路由——在 `backend/app/api/v1/api.py`：把 `ziwei` 加进现有的 `from app.api.v1.routes import ...` 一行（按字母序放在 `summary` 之后），并在文件末尾追加：

```python
api_router.include_router(ziwei.router)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend; python -m pytest tests/test_ziwei_routes.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: 跑全量后端测试防回归**

Run: `cd backend; python -m pytest tests/ -v`
Expected: 全部 PASS（如有与本改动无关的既有失败，记录但不修）

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/routes/ziwei.py backend/app/api/v1/api.py backend/tests/test_ziwei_routes.py
git commit -m "feat(ziwei): profile CRUD API"
```

---

### Task 3: 前端 iztro 排盘封装

**Files:**
- Modify: `frontend/package.json`（安装 iztro）
- Create: `frontend/src/lib/ziwei/types.ts`
- Create: `frontend/src/lib/ziwei/constants.ts`
- Create: `frontend/src/lib/ziwei/chart.ts`
- Create: `frontend/scripts/ziwei-smoke.cjs`（冒烟脚本）

- [ ] **Step 1: 安装 iztro**

Run: `cd frontend; npm install iztro`
Expected: package.json dependencies 出现 `"iztro": "^2.5.8"`（或更新的 2.x）

- [ ] **Step 2: 冒烟脚本验证 iztro 真实可用**

创建 `frontend/scripts/ziwei-smoke.cjs`：

```javascript
// 验证 iztro 排盘核心 API（文档示例盘：2000-8-16 寅时 女）
const { astro } = require("iztro");

const a = astro.bySolar("2000-8-16", 2, "女", true, "zh-CN");
console.log("palaces:", a.palaces.length);
console.log("fiveElementsClass:", a.fiveElementsClass);
console.log("soul/body:", a.soul, a.body);
console.log("palace0:", a.palaces[0].name, a.palaces[0].earthlyBranch, a.palaces[0].majorStars.map((s) => s.name + (s.mutagen || "")).join(","));

const h = a.horoscope("2026-6-9");
console.log("decadal:", h.decadal.name, h.decadal.mutagen.join(","));
console.log("yearly:", h.yearly.name, h.yearly.mutagen.join(","));

if (a.palaces.length !== 12) throw new Error("expected 12 palaces");
console.log("SMOKE OK");
```

Run: `cd frontend; node scripts/ziwei-smoke.cjs`
Expected: 输出 12 个宫、五行局、命主/身主、大限流年四化，最后 `SMOKE OK`

- [ ] **Step 3: 写类型**

创建 `frontend/src/lib/ziwei/types.ts`：

```typescript
/** 归一化命盘 JSON —— 存入后端 ZiweiProfile.chart_json，渲染与 AI 共用此结构 */

export type ZiweiStar = {
  name: string;
  /** major | soft | tough | adjective | flower | helper | lucun | tianma */
  type: string;
  /** 庙|旺|得|利|平|不|陷，可能为空 */
  brightness?: string;
  /** 禄|权|科|忌（生年四化），无则为空 */
  mutagen?: string;
};

export type ZiweiPalace = {
  index: number;
  name: string;
  isBodyPalace: boolean;
  isOriginalPalace: boolean;
  heavenlyStem: string;
  earthlyBranch: string;
  majorStars: ZiweiStar[];
  minorStars: ZiweiStar[];
  adjectiveStars: ZiweiStar[];
  changsheng12: string;
  decadal: { range: [number, number]; heavenlyStem: string; earthlyBranch: string };
  ages: number[];
};

export type ZiweiChart = {
  gender: string;
  solarDate: string;
  lunarDate: string;
  chineseDate: string;
  time: string;
  timeRange: string;
  sign: string;
  zodiac: string;
  earthlyBranchOfSoulPalace: string;
  earthlyBranchOfBodyPalace: string;
  soul: string;
  body: string;
  fiveElementsClass: string;
  palaces: ZiweiPalace[];
};

export type BirthInput = {
  /** 公历或农历日期，YYYY-M-D */
  dateStr: string;
  /** 时辰 0-12（0=早子时, 12=晚子时） */
  timeIndex: number;
  gender: "male" | "female";
  isLunar: boolean;
  isLeapMonth?: boolean;
};
```

- [ ] **Step 4: 写常量**

创建 `frontend/src/lib/ziwei/constants.ts`：

```typescript
/** 时辰序号 0-12 对应的标签（与 iztro timeIndex 语义一致） */
export const TIME_LABELS = [
  "早子时 00:00-01:00",
  "丑时 01:00-03:00",
  "寅时 03:00-05:00",
  "卯时 05:00-07:00",
  "辰时 07:00-09:00",
  "巳时 09:00-11:00",
  "午时 11:00-13:00",
  "未时 13:00-15:00",
  "申时 15:00-17:00",
  "酉时 17:00-19:00",
  "戌时 19:00-21:00",
  "亥时 21:00-23:00",
  "晚子时 23:00-00:00",
] as const;

export const RELATION_LABELS: Record<string, string> = {
  self: "自己",
  family: "家人",
  friend: "朋友",
};

export const PERSONA_LABELS: Record<string, string> = {
  sage: "温和智者",
  taoist: "仙风道骨",
  analyst: "现代分析师",
};

/** 四化徽标配色 */
export const MUTAGEN_STYLES: Record<string, string> = {
  禄: "bg-emerald-500/90 text-white",
  权: "bg-amber-500/90 text-white",
  科: "bg-sky-500/90 text-white",
  忌: "bg-rose-500/90 text-white",
};
```

- [ ] **Step 5: 写排盘封装**

创建 `frontend/src/lib/ziwei/chart.ts`：

```typescript
import { astro } from "iztro";
import type { BirthInput, ZiweiChart, ZiweiPalace, ZiweiStar } from "./types";

type IztroStar = { name: string; type: string; brightness?: string; mutagen?: string };

function toStar(star: IztroStar): ZiweiStar {
  return {
    name: star.name,
    type: star.type,
    brightness: star.brightness || undefined,
    mutagen: star.mutagen || undefined,
  };
}

/** 浏览器内排盘：iztro 星盘 → 归一化 ZiweiChart（可 JSON 序列化，存入档案） */
export function computeChart(input: BirthInput): ZiweiChart {
  const gender = input.gender === "female" ? "女" : "男";
  const astrolabe = input.isLunar
    ? astro.byLunar(input.dateStr, input.timeIndex, gender, input.isLeapMonth ?? false, true, "zh-CN")
    : astro.bySolar(input.dateStr, input.timeIndex, gender, true, "zh-CN");

  const palaces: ZiweiPalace[] = astrolabe.palaces.map((p) => ({
    index: p.index,
    name: p.name,
    isBodyPalace: p.isBodyPalace,
    isOriginalPalace: p.isOriginalPalace,
    heavenlyStem: p.heavenlyStem,
    earthlyBranch: p.earthlyBranch,
    majorStars: p.majorStars.map(toStar),
    minorStars: p.minorStars.map(toStar),
    adjectiveStars: p.adjectiveStars.map(toStar),
    changsheng12: p.changsheng12,
    decadal: {
      range: [p.decadal.range[0], p.decadal.range[1]],
      heavenlyStem: p.decadal.heavenlyStem,
      earthlyBranch: p.decadal.earthlyBranch,
    },
    ages: [...p.ages],
  }));

  return {
    gender: astrolabe.gender,
    solarDate: astrolabe.solarDate,
    lunarDate: astrolabe.lunarDate,
    chineseDate: astrolabe.chineseDate,
    time: astrolabe.time,
    timeRange: astrolabe.timeRange,
    sign: astrolabe.sign,
    zodiac: astrolabe.zodiac,
    earthlyBranchOfSoulPalace: astrolabe.earthlyBranchOfSoulPalace,
    earthlyBranchOfBodyPalace: astrolabe.earthlyBranchOfBodyPalace,
    soul: astrolabe.soul,
    body: astrolabe.body,
    fiveElementsClass: String(astrolabe.fiveElementsClass),
    palaces,
  };
}
```

- [ ] **Step 6: 类型检查**

Run: `cd frontend; npx tsc --noEmit`
Expected: 无错误（若 iztro 类型与上面字段有出入，以 `node_modules/iztro/lib` 里的 .d.ts 为准修正 `chart.ts`，不要用 `any` 糊掉）

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/lib/ziwei/ frontend/scripts/ziwei-smoke.cjs
git commit -m "feat(ziwei): iztro chart computation wrapper with normalized ZiweiChart"
```

---

### Task 4: 前端 API client

**Files:**
- Create: `frontend/src/lib/ziwei/api.ts`

- [ ] **Step 1: 写 API client**

创建 `frontend/src/lib/ziwei/api.ts`：

```typescript
import { API_BASE } from "@/lib/api";
import type { ZiweiChart } from "./types";

export type ZiweiProfileOut = {
  id: number;
  name: string;
  relation: string;
  gender: string;
  birth_date: string;
  birth_time_index: number;
  is_lunar_input: boolean;
  is_leap_month: boolean;
  chart_json: ZiweiChart | Record<string, never>;
  persona: string;
  created_at: string | null;
  updated_at: string | null;
};

export type ZiweiProfileCreate = {
  name: string;
  relation: string;
  gender: string;
  birth_date: string;
  birth_time_index: number;
  is_lunar_input: boolean;
  is_leap_month: boolean;
  chart_json: ZiweiChart;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const ziweiApi = {
  listProfiles: () => request<ZiweiProfileOut[]>("/ziwei/profiles"),
  createProfile: (payload: ZiweiProfileCreate) =>
    request<ZiweiProfileOut>("/ziwei/profiles", { method: "POST", body: JSON.stringify(payload) }),
  updateProfile: (id: number, payload: Partial<ZiweiProfileCreate> & { persona?: string }) =>
    request<ZiweiProfileOut>(`/ziwei/profiles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProfile: (id: number) =>
    request<{ deleted: number }>(`/ziwei/profiles/${id}`, { method: "DELETE" }),
};
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend; npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/ziwei/api.ts
git commit -m "feat(ziwei): typed frontend API client for profiles"
```

---

### Task 5: 2D 暗夜命盘组件

**Files:**
- Create: `frontend/src/components/ziwei/chart-grid-2d.tsx`

**布局规则（传统紫微方盘，十二地支固定占据 4×4 外圈）：**

```
巳 午 未 申
辰 [中宫] 酉
卯 [中宫] 戌
寅 丑 子 亥
```

- [ ] **Step 1: 写组件**

创建 `frontend/src/components/ziwei/chart-grid-2d.tsx`：

```tsx
"use client";

import { MUTAGEN_STYLES } from "@/lib/ziwei/constants";
import type { ZiweiChart, ZiweiPalace, ZiweiStar } from "@/lib/ziwei/types";

/** 地支 → 4×4 网格位置（row / col，从 1 开始） */
const BRANCH_GRID: Record<string, { row: number; col: number }> = {
  巳: { row: 1, col: 1 },
  午: { row: 1, col: 2 },
  未: { row: 1, col: 3 },
  申: { row: 1, col: 4 },
  辰: { row: 2, col: 1 },
  酉: { row: 2, col: 4 },
  卯: { row: 3, col: 1 },
  戌: { row: 3, col: 4 },
  寅: { row: 4, col: 1 },
  丑: { row: 4, col: 2 },
  子: { row: 4, col: 3 },
  亥: { row: 4, col: 4 },
};

function StarBadge({ star, major }: { star: ZiweiStar; major: boolean }) {
  return (
    <span className={`inline-flex items-center gap-0.5 ${major ? "text-[13px] font-semibold text-violet-100" : "text-[11px] text-violet-300/80"}`}>
      {star.name}
      {star.brightness ? <sup className="text-[9px] text-violet-300/60">{star.brightness}</sup> : null}
      {star.mutagen ? (
        <span className={`rounded px-0.5 text-[9px] leading-tight ${MUTAGEN_STYLES[star.mutagen] ?? "bg-violet-500/80 text-white"}`}>
          {star.mutagen}
        </span>
      ) : null}
    </span>
  );
}

function PalaceCell({ palace, isSoulPalace }: { palace: ZiweiPalace; isSoulPalace: boolean }) {
  const pos = BRANCH_GRID[palace.earthlyBranch];
  if (!pos) return null;
  return (
    <div
      style={{ gridRow: pos.row, gridColumn: pos.col }}
      className={`relative flex flex-col rounded-lg border p-1.5 transition-colors ${
        isSoulPalace
          ? "border-amber-400/60 bg-gradient-to-br from-violet-900/60 to-[#160b38] shadow-[0_0_14px_rgba(251,191,36,0.25)]"
          : "border-violet-500/25 bg-gradient-to-br from-violet-950/40 to-[#0d0722]"
      }`}
    >
      <div className="flex flex-wrap gap-x-1.5 gap-y-0.5">
        {palace.majorStars.map((s) => (
          <StarBadge key={s.name} star={s} major />
        ))}
      </div>
      <div className="mt-0.5 flex flex-wrap gap-x-1 gap-y-0">
        {palace.minorStars.map((s) => (
          <StarBadge key={s.name} star={s} major={false} />
        ))}
      </div>
      <div className="mt-auto flex items-end justify-between pt-1">
        <span className="text-[10px] text-violet-300/50">
          {palace.decadal.range[0]}-{palace.decadal.range[1]}
        </span>
        <div className="text-right">
          <span className="text-[12px] font-semibold text-violet-100">
            {palace.name}
            {palace.isBodyPalace ? <span className="ml-0.5 rounded bg-amber-500/80 px-0.5 text-[9px] text-white">身</span> : null}
          </span>
          <div className="text-[10px] text-violet-300/50">
            {palace.heavenlyStem}
            {palace.earthlyBranch}
          </div>
        </div>
      </div>
    </div>
  );
}

function CenterCell({ chart }: { chart: ZiweiChart }) {
  return (
    <div
      style={{ gridRow: "2 / 4", gridColumn: "2 / 4" }}
      className="flex flex-col items-center justify-center gap-1 rounded-lg border border-amber-400/30 bg-[#08041a] p-3 text-center"
    >
      <p className="text-sm font-semibold tracking-[0.2em] text-amber-200/90">{chart.fiveElementsClass}</p>
      <p className="text-[11px] text-violet-200/70">{chart.chineseDate}</p>
      <p className="text-[11px] text-violet-200/70">
        公历 {chart.solarDate} · 农历 {chart.lunarDate}
      </p>
      <p className="text-[11px] text-violet-200/70">
        {chart.time}（{chart.timeRange}）
      </p>
      <p className="text-[11px] text-violet-300/60">
        命主 {chart.soul} · 身主 {chart.body}
      </p>
      <p className="text-[11px] text-violet-300/60">
        {chart.zodiac} · {chart.sign}
      </p>
    </div>
  );
}

export function ChartGrid2D({ chart }: { chart: ZiweiChart }) {
  return (
    <div className="rounded-[28px] border border-violet-500/20 bg-[#0a0618] p-2 shadow-panel sm:p-3">
      <div className="grid aspect-square grid-cols-4 grid-rows-4 gap-1">
        {chart.palaces.map((palace) => (
          <PalaceCell
            key={palace.earthlyBranch}
            palace={palace}
            isSoulPalace={palace.earthlyBranch === chart.earthlyBranchOfSoulPalace}
          />
        ))}
        <CenterCell chart={chart} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend; npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ziwei/chart-grid-2d.tsx
git commit -m "feat(ziwei): 2D dark-cosmos natal chart grid component"
```

---

### Task 6: 建档表单组件

**Files:**
- Create: `frontend/src/components/ziwei/profile-form.tsx`

- [ ] **Step 1: 写组件**

创建 `frontend/src/components/ziwei/profile-form.tsx`：

```tsx
"use client";

import { useState } from "react";
import { computeChart } from "@/lib/ziwei/chart";
import { TIME_LABELS, RELATION_LABELS } from "@/lib/ziwei/constants";
import { ziweiApi, type ZiweiProfileOut } from "@/lib/ziwei/api";

const inputCls =
  "w-full rounded-xl border border-violet-500/30 bg-[#120a2e] px-3 py-2 text-sm text-violet-100 placeholder:text-violet-300/30 focus:border-violet-400 focus:outline-none";
const labelCls = "block text-xs font-semibold text-violet-300/70 mb-1";

export function ProfileForm({ onCreated, onCancel }: { onCreated: (p: ZiweiProfileOut) => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [relation, setRelation] = useState("self");
  const [gender, setGender] = useState<"male" | "female">("female");
  const [isLunar, setIsLunar] = useState(false);
  const [isLeapMonth, setIsLeapMonth] = useState(false);
  const [birthDate, setBirthDate] = useState("");
  const [timeIndex, setTimeIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    if (!name.trim()) return setError("请填写姓名/称呼");
    if (!/^\d{4}-\d{1,2}-\d{1,2}$/.test(birthDate)) return setError("生日格式应为 YYYY-M-D，例如 1990-8-16");
    setSubmitting(true);
    try {
      // 浏览器内排盘——失败（极端生辰）会 throw，在此兜住
      const chart = computeChart({ dateStr: birthDate, timeIndex, gender, isLunar, isLeapMonth });
      const profile = await ziweiApi.createProfile({
        name: name.trim(),
        relation,
        gender,
        birth_date: birthDate,
        birth_time_index: timeIndex,
        is_lunar_input: isLunar,
        is_leap_month: isLeapMonth,
        chart_json: chart,
      });
      onCreated(profile);
    } catch (e) {
      setError(e instanceof Error && e.message.startsWith("Request failed") ? "保存失败，请稍后重试" : "排盘失败，请检查生辰是否正确");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 rounded-[28px] border border-violet-500/20 bg-[#0d0722] p-5">
      <h3 className="text-sm font-semibold tracking-[0.2em] text-violet-200">新建命主档案</h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>姓名 / 称呼</label>
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="如：妈妈" />
        </div>
        <div>
          <label className={labelCls}>关系</label>
          <select className={inputCls} value={relation} onChange={(e) => setRelation(e.target.value)}>
            {Object.entries(RELATION_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>性别</label>
          <select className={inputCls} value={gender} onChange={(e) => setGender(e.target.value as "male" | "female")}>
            <option value="female">女</option>
            <option value="male">男</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>历法</label>
          <select
            className={inputCls}
            value={isLunar ? "lunar" : "solar"}
            onChange={(e) => {
              setIsLunar(e.target.value === "lunar");
              if (e.target.value !== "lunar") setIsLeapMonth(false);
            }}
          >
            <option value="solar">公历（阳历）</option>
            <option value="lunar">农历（阴历）</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>出生日期（{isLunar ? "农历" : "公历"} YYYY-M-D）</label>
          <input className={inputCls} value={birthDate} onChange={(e) => setBirthDate(e.target.value)} placeholder="1990-8-16" />
        </div>
        <div>
          <label className={labelCls}>出生时辰</label>
          <select className={inputCls} value={timeIndex} onChange={(e) => setTimeIndex(Number(e.target.value))}>
            {TIME_LABELS.map((label, index) => (
              <option key={label} value={index}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLunar ? (
        <label className="flex items-center gap-2 text-xs text-violet-300/70">
          <input type="checkbox" checked={isLeapMonth} onChange={(e) => setIsLeapMonth(e.target.checked)} />
          出生月为闰月
        </label>
      ) : null}

      {error ? <p className="text-xs text-rose-400">{error}</p> : null}

      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="flex-1 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 py-2.5 text-sm font-semibold text-white shadow-[0_4px_14px_rgba(139,92,246,0.4)] transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "排盘中……" : "排盘建档"}
        </button>
        <button onClick={onCancel} className="rounded-xl border border-violet-500/30 px-4 py-2.5 text-sm text-violet-300">
          取消
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend; npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ziwei/profile-form.tsx
git commit -m "feat(ziwei): profile creation form with in-browser chart computation"
```

---

### Task 7: /ziwei 页面 + sidebar 入口

**Files:**
- Create: `frontend/src/app/ziwei/page.tsx`
- Modify: `frontend/src/components/layout/sidebar-nav.tsx`（items 数组加一项）

- [ ] **Step 1: 写页面**

创建 `frontend/src/app/ziwei/page.tsx`：

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Sparkles, Trash2 } from "lucide-react";
import { ChartGrid2D } from "@/components/ziwei/chart-grid-2d";
import { ProfileForm } from "@/components/ziwei/profile-form";
import { ziweiApi, type ZiweiProfileOut } from "@/lib/ziwei/api";
import { RELATION_LABELS } from "@/lib/ziwei/constants";
import type { ZiweiChart } from "@/lib/ziwei/types";

export default function ZiweiPage() {
  const [profiles, setProfiles] = useState<ZiweiProfileOut[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    ziweiApi
      .listProfiles()
      .then((data) => {
        setProfiles(data);
        if (data.length > 0) setSelectedId(data[0].id);
        else setShowForm(true);
      })
      .catch(() => setLoadError(true));
  }, []);

  const selected = useMemo(() => profiles.find((p) => p.id === selectedId) ?? null, [profiles, selectedId]);
  const chart = selected && "palaces" in selected.chart_json ? (selected.chart_json as ZiweiChart) : null;

  const handleCreated = (profile: ZiweiProfileOut) => {
    setProfiles((prev) => [...prev, profile]);
    setSelectedId(profile.id);
    setShowForm(false);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("删除档案将一并删除其全部解读记录，确定？")) return;
    await ziweiApi.deleteProfile(id);
    setProfiles((prev) => {
      const next = prev.filter((p) => p.id !== id);
      if (selectedId === id) setSelectedId(next[0]?.id ?? null);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-[14px] bg-gradient-to-br from-violet-600 via-violet-700 to-[#2d1a6e] text-white shadow-[0_6px_16px_-6px_rgba(124,58,237,0.6)]">
          <Sparkles className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-600">星垣 · Astrolabe</span>
          <h1 className="font-display text-2xl leading-tight text-ink">紫微斗数</h1>
        </div>
      </div>

      {loadError ? <p className="text-sm text-rose-500">加载档案失败，请确认后端已启动。</p> : null}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* 档案列表 */}
        <div className="space-y-3">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              onClick={() => setSelectedId(profile.id)}
              className={`group flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition-colors ${
                profile.id === selectedId
                  ? "border-violet-500/60 bg-violet-600/10"
                  : "border-ink/10 bg-white/85 hover:border-violet-400/40"
              }`}
            >
              <div>
                <p className="text-sm font-semibold text-ink">{profile.name}</p>
                <p className="text-xs text-ink/50">
                  {RELATION_LABELS[profile.relation] ?? profile.relation} · {profile.gender === "female" ? "女" : "男"} ·{" "}
                  {profile.birth_date}
                </p>
              </div>
              <Trash2
                size={16}
                className="text-ink/20 opacity-0 transition-opacity hover:text-rose-500 group-hover:opacity-100"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleDelete(profile.id);
                }}
              />
            </button>
          ))}

          {showForm ? (
            <ProfileForm onCreated={handleCreated} onCancel={() => setShowForm(false)} />
          ) : (
            <button
              onClick={() => setShowForm(true)}
              className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-violet-400/40 py-3 text-sm text-violet-600 transition-colors hover:bg-violet-600/5"
            >
              <Plus size={16} /> 新建命主档案
            </button>
          )}
        </div>

        {/* 命盘 */}
        <div>
          {chart ? (
            <ChartGrid2D chart={chart} />
          ) : (
            <div className="flex min-h-[400px] items-center justify-center rounded-[28px] border border-ink/10 bg-[#0a0618]">
              <p className="text-sm text-violet-300/50">{profiles.length === 0 ? "建立第一个档案，开启星盘" : "档案缺少命盘数据"}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 加 sidebar 入口**

在 `frontend/src/components/layout/sidebar-nav.tsx`：

1. 在 lucide-react 导入中追加 `Sparkles`；
2. 在 `items` 数组中 `{ href: "/toolkits", ... }` 之后插入：

```typescript
  { href: "/ziwei", label: "紫微斗数", icon: Sparkles },
```

- [ ] **Step 3: 类型检查 + 构建**

Run: `cd frontend; npx tsc --noEmit; npm run build`
Expected: 两者都无错误，build 输出包含 `/ziwei` 路由

- [ ] **Step 4: 端到端手动验证**

1. 启动本地栈：项目根目录 `docker compose up -d postgres redis`，然后 `cd backend; uvicorn app.main:app --reload`，另开终端 `cd frontend; npm run dev`
2. 打开 `http://localhost:3000/ziwei`
3. 验证清单：
   - sidebar 出现「紫微斗数」入口，点击进入
   - 新建档案：填「测试 / 自己 / 女 / 公历 2000-8-16 / 寅时」→ 排盘建档
   - 暗夜方盘渲染出 12 宫 + 中宫；命宫有金色高亮；身宫有「身」标；生年四化（禄权科忌彩色徽标）出现在对应星曜上
   - 对照验证：iztro 文档示例此盘为水二局——中宫应显示「水二局」
   - 刷新页面档案仍在（已持久化）；删除档案后列表清空

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/ziwei/page.tsx frontend/src/components/layout/sidebar-nav.tsx
git commit -m "feat(ziwei): /ziwei page with profile management and 2D chart, sidebar entry"
```

---

### Task 8: 收尾验证

- [ ] **Step 1: 全量后端测试**

Run: `cd backend; python -m pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 前端构建**

Run: `cd frontend; npm run build`
Expected: 无错误

- [ ] **Step 3: 冒烟脚本复跑**

Run: `cd frontend; node scripts/ziwei-smoke.cjs`
Expected: `SMOKE OK`

- [ ] **Step 4: 提交遗留改动（如有）并汇报**

```bash
git status
git add -A
git commit -m "chore(ziwei): phase 1 foundation complete"
```

汇报内容：测试结果、手动验证清单完成情况、与计划的偏差。

---

## 后续阶段（各自独立计划，spec §11）

- Phase 2：3D 主体验（R3F 星空 + 玄殿方盘 + 飞入单宫）——依赖本阶段的 `ZiweiChart` 结构与页面骨架
- Phase 3：AI 解盘师（oracle 循环 + 知识库提取 + 镜头联动 + 对话坞）
- Phase 4：记忆系统（画像蒸馏 + 人生事件 + 历史回看）
- Phase 5：流年 + 合盘 + 报告
