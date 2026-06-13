# 灵签 · 3D 求签 + AI 解签 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 新增独立「灵签」板块：3D 摇签筒，用户问一个问题→摇出一支观音灵签→AI 解签（流式 + 叙事化播放 + MiniMax 配音）。

**Architecture:** 后端镜像紫微 oracle（去掉排盘）：100 签语料 + `secrets` 服务端抽签 + 解签 prompt（单次内联标记，复用 `ziwei/oracle_tools` 解析器）+ `/qian/oracle/stream`（先吐签、再流式解签）+ `QianReading` 表。前端新 `/qian` 页 + 3D 签筒场景 + 解签面板，复用叙事化播放指挥器（本计划把指挥器的镜头执行参数化，紫微/求签各注入落点）、CloudNarration（MiniMax via 现有 `/ziwei/tts`）、术语卡、历史模式。

**Tech Stack:** FastAPI + SQLAlchemy + pytest（后端 TDD）；Next 15 + React 19 + R3F（three@0.184/fiber@9.6/drei@10.7）；前端无单测框架，验证 = `tsc --noEmit` + CI `next build` + prod 肉眼。

**配色（spec §8，全程遵守）：** 偏暖近黑底 `#140e08`；庙宇暖金/铜 `#d6a84a`（主点缀）；朱红/赭 `#b9472f`（次，强调/吉凶高亮）；暖白文字 `#f4ece0`。区别于紫微冷紫，呼应门户 ember 暖色家族。

**测试约定：** 后端有 pytest，走 TDD。前端无单测框架；`tsc` 时 `scene3d/*`、`camera-rig.tsx`、`iztro`、`chart.ts` 有**既存** module-resolution 报错（本地缺 three/iztro），只看**不引入新错**。

---

## Task 1: 签语料 `signs.py`（生成脚本）+ `draw.py`

**Files:**
- Create: `backend/scripts/build_qian_signs.py`（一次性生成脚本，入库便于复现）
- Create: `backend/app/services/qian/__init__.py`（空）
- Create: `backend/app/services/qian/signs.py`（生成产物：100 签）
- Create: `backend/app/services/qian/draw.py`
- Test: `backend/tests/test_qian_signs.py`

- [ ] **Step 1: 写生成脚本** `backend/scripts/build_qian_signs.py`

```python
"""一次性生成观音灵签 100 签语料 → app/services/qian/signs.py。
公版语料以 GitHub snjor-kii/guanyinqiuqian 的 lottery-data.js 为基线，
字段映射 id/title/type→(grade,palace)/poetry/meaning/holy。只取公版诗文。
用法：python backend/scripts/build_qian_signs.py
"""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path

SRC = "https://raw.githubusercontent.com/snjor-kii/guanyinqiuqian/main/lottery-data.js"
OUT = Path(__file__).resolve().parents[1] / "app" / "services" / "qian" / "signs.py"

# type 形如「上签子宫」→ grade「上签」+ palace「子宫」（palace = 地支+宫）
_PALACE_RE = re.compile(r"^(.*?)([子丑寅卯辰巳午未申酉戌亥]宫)$")
# 逐条对象：宽松匹配 5 个字符串字段（顺序 id,title,type,poetry,meaning,explanation）
_ENTRY_RE = re.compile(
    r"id:\s*(\d+).*?title:\s*\"([^\"]*)\".*?type:\s*\"([^\"]*)\""
    r".*?poetry:\s*\"([^\"]*)\".*?meaning:\s*\"([^\"]*)\".*?explanation:\s*\"([^\"]*)\"",
    re.S,
)


def main() -> None:
    raw = urllib.request.urlopen(SRC, timeout=60).read().decode("utf-8")
    entries = _ENTRY_RE.findall(raw)
    if len(entries) != 100:
        raise SystemExit(f"期望 100 签，实得 {len(entries)} —— 源结构可能变了，请检查 {SRC}")
    signs = []
    for _id, title, typ, poetry, meaning, holy in entries:
        m = _PALACE_RE.match(typ.strip())
        grade, palace = (m.group(1), m.group(2)) if m else (typ.strip(), "")
        signs.append({
            "id": int(_id), "grade": grade.strip(), "palace": palace,
            "title": title.strip(), "poetry": poetry.strip(),
            "meaning": meaning.strip(), "holy": holy.strip(),
        })
    signs.sort(key=lambda s: s["id"])
    body = ",\n".join(
        "    {"
        f"\"id\": {s['id']}, \"grade\": \"{s['grade']}\", \"palace\": \"{s['palace']}\", "
        f"\"title\": \"{s['title']}\", \"poetry\": \"{s['poetry']}\", "
        f"\"meaning\": \"{s['meaning']}\", \"holy\": \"{s['holy']}\""
        "}"
        for s in signs
    )
    OUT.write_text(
        '"""观音灵签 100 签（公版诗文，由 scripts/build_qian_signs.py 生成；勿手改）。"""\n'
        "from __future__ import annotations\n\n"
        "SIGNS: list[dict] = [\n" + body + ",\n]\n\n"
        "_BY_ID = {s[\"id\"]: s for s in SIGNS}\n\n\n"
        "def all_signs() -> list[dict]:\n    return SIGNS\n\n\n"
        "def get_sign(sign_id: int) -> dict | None:\n    return _BY_ID.get(sign_id)\n",
        encoding="utf-8",
    )
    print(f"✓ 写出 {OUT}（{len(signs)} 签）")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本生成 signs.py**

Run: `cd backend && python scripts/build_qian_signs.py`
Expected: `✓ 写出 .../app/services/qian/signs.py（100 签）`。打开 signs.py 抽查第 1、50、100 签：`poetry` 是四句签诗、`grade` 形如「上签/中签/下签」(或上上等)、`palace` 形如「子宫」。若 grade/palace 切分异常（如 palace 为空），微调 `_PALACE_RE` 后重跑。创建空 `backend/app/services/qian/__init__.py`。

- [ ] **Step 3: 写 `draw.py`**

```python
# backend/app/services/qian/draw.py
"""服务端抽签：加密级随机，可审计；3D 摇签只是装饰。"""
from __future__ import annotations

import secrets

from app.services.qian.signs import all_signs, get_sign  # noqa: F401  (re-export get_sign)


def draw_sign() -> dict:
    return secrets.choice(all_signs())
```

- [ ] **Step 4: 写测试** `backend/tests/test_qian_signs.py`

```python
from app.services.qian.signs import all_signs, get_sign
from app.services.qian.draw import draw_sign


def test_corpus_complete():
    signs = all_signs()
    assert len(signs) == 100
    ids = sorted(s["id"] for s in signs)
    assert ids == list(range(1, 101))
    for s in signs:
        for f in ("grade", "palace", "title", "poetry", "meaning", "holy"):
            assert s[f] and isinstance(s[f], str), f"sign {s['id']} 字段 {f} 为空"


def test_get_sign():
    assert get_sign(1)["id"] == 1
    assert get_sign(999) is None


def test_draw_in_range():
    seen = set()
    for _ in range(300):
        s = draw_sign()
        assert 1 <= s["id"] <= 100
        seen.add(s["id"])
    assert len(seen) > 30  # 300 次抽样应覆盖到不少签（随机性 sanity）
```

- [ ] **Step 5: 跑测试**

Run: `cd backend && python -m pytest tests/test_qian_signs.py -q`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```
git add backend/scripts/build_qian_signs.py backend/app/services/qian/__init__.py backend/app/services/qian/signs.py backend/app/services/qian/draw.py backend/tests/test_qian_signs.py
git commit -m "feat(qian): 观音灵签 100-sign corpus (generated) + secrets-based draw"
```

---

## Task 2: 解签人设 `personas.py` + 解签 oracle `oracle.py`

**Files:**
- Create: `backend/app/services/qian/personas.py`
- Create: `backend/app/services/qian/oracle.py`
- Test: `backend/tests/test_qian_oracle.py`

参考：紫微 `backend/app/services/ziwei/oracle.py` 的单次内联标记法 + `oracle_tools.parse_markers`。

- [ ] **Step 1: 写 `personas.py`**

```python
# backend/app/services/qian/personas.py
"""解签人单一人设。"""

JIEQIAN_PERSONA = (
    "你是一位寺庙里的解签人，温厚而通达。你为求签者解读观音灵签：先念这支签的签诗，"
    "再结合 ta 的问题，把签意落到具体处境上。语气慈和、含蓄，给希望也给提醒，劝人向善、宽心；"
    "不武断吉凶、不吓唬人。点到为止，不堆砌辞藻。"
)


def persona_prompt() -> str:
    return JIEQIAN_PERSONA
```

- [ ] **Step 2: 写失败测试** `backend/tests/test_qian_oracle.py`

```python
from types import SimpleNamespace
from typing import Any

from app.services.qian.oracle import QianOracle

SIGN = {
    "id": 7, "grade": "上签", "palace": "辰宫", "title": "李世民登位",
    "poetry": "一句签诗。二句签诗。三句签诗。四句签诗。",
    "meaning": "此卦吉象。", "holy": "圣意如此。",
}


def _fake_response(text: str, in_tok=200, out_tok=120):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


class FakeClient:
    def __init__(self, response): self._r = response; self.calls = []
    class _M:
        def __init__(self, o): self._o = o
        def create(self, **k): self._o.calls.append(k); return self._o._r
    @property
    def messages(self): return FakeClient._M(self)


def test_system_prompt_has_sign_and_persona():
    client = FakeClient(_fake_response("签诗大意……宽心即可。"))
    oracle = QianOracle(client=client, model="m")
    oracle.run(sign=SIGN, question="今年事业如何？")
    system = client.calls[0]["system"]
    assert "一句签诗" in system            # 签诗进了 prompt
    assert "上签" in system and "辰宫" in system
    assert "解签人" in system               # 人设
    assert "[[term:" in system              # 标记说明
    user_msg = client.calls[0]["messages"][-1]["content"]
    assert "今年事业" in user_msg


def test_run_returns_clean_segments_cameras():
    client = FakeClient(_fake_response("此乃上签。[[term:辰宫|地支之一]] 凡事可成。"))
    oracle = QianOracle(client=client, model="m")
    result = oracle.run(sign=SIGN, question="问")
    assert result is not None
    assert "[[" not in result["response"]
    assert any(c["type"] == "explain_term" for c in result["camera_commands"])
    assert result["_meta"]["input_tokens"] == 200


def test_run_none_on_exception():
    client = FakeClient(Exception("boom"))
    oracle = QianOracle(client=client, model="m")
    assert oracle.run(sign=SIGN, question="问") is None
```

Run `cd backend && python -m pytest tests/test_qian_oracle.py -q` → FAIL（QianOracle 不存在）。

- [ ] **Step 3: 写 `oracle.py`**

```python
# backend/app/services/qian/oracle.py
"""观音灵签 AI 解签：单次 Claude 调用 + 内联标记（复用紫微的标记解析器）。"""
from __future__ import annotations

import time
from typing import Any, Optional

from app.services.qian.personas import persona_prompt
from app.services.ziwei.oracle_tools import parse_markers


class QianOracle:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def system_prompt(self, sign: dict, question: str) -> str:
        return (
            persona_prompt()
            + "\n\n下面是求签者摇到的这支签（签诗为公版原文，"
            "**不得改写或臆造签诗**，只可解读）：\n"
            f"第{sign['id']}签 · {sign['grade']} · {sign['palace']} · {sign['title']}\n"
            f"签诗：{sign['poetry']}\n"
            f"解曰：{sign['meaning']}\n"
            f"圣意：{sign['holy']}\n"
            "\n## 输出\n先用一句把签诗的意象点出来，再结合求签者的问题给出解读与宽心的建议，"
            "约 250-450 字，口语、温和。\n"
            "## 内联标记（会被前端解析、不显示给用户）\n"
            "- 解释签诗里的生僻词或典故时，插入 [[term:词|一句话白话解释]]。\n"
            "整段只在 1-3 个最关键的词上用 term，不要每词都标。除标记外正常说话，不要输出 JSON 或代码块。"
        )

    def run(self, sign: dict, question: str) -> Optional[dict]:
        system = self.system_prompt(sign, question)
        start = time.time()
        try:
            resp = self.client.messages.create(
                model=self.model, max_tokens=1200, system=system,
                messages=[{"role": "user", "content": question}], timeout=60.0,
            )
        except Exception:
            return None
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        clean, segments, cameras = parse_markers(text)
        if not clean:
            return None
        return {
            "response": clean, "camera_commands": cameras, "segments": segments,
            "_meta": {
                "model": self.model,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "total_tokens": resp.usage.input_tokens + resp.usage.output_tokens,
                "latency_ms": int((time.time() - start) * 1000),
            },
        }
```

- [ ] **Step 4: 跑测试通过**

Run `cd backend && python -m pytest tests/test_qian_oracle.py -q` → 3 passed.

- [ ] **Step 5: Commit**

```
git add backend/app/services/qian/personas.py backend/app/services/qian/oracle.py backend/tests/test_qian_oracle.py
git commit -m "feat(qian): 解签人 persona + QianOracle (single-call inline-marker, reuses ziwei parser)"
```

---

## Task 3: `QianReading` 模型 + 路由 `/qian/oracle/stream` + 历史

**Files:**
- Modify: `backend/app/models/entities.py`（加 `QianReading`）
- Create: `backend/app/api/v1/routes/qian.py`
- Modify: 注册路由（找到 ziwei 路由注册处，照样注册 qian）
- Test: `backend/tests/test_qian_routes.py`

- [ ] **Step 1: 加模型**（`entities.py`，紧随 ZiweiMessage 之后）

```python
class QianReading(Base):
    __tablename__ = "qian_readings"
    __table_args__ = (Index("ix_qian_reading_created", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    sign_id: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), default="")
    response: Mapped[str] = mapped_column(Text, default="")
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)  # {sign, camera_commands, segments}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```
（确认 `JSON`/`Index`/`Mapped`/`mapped_column`/`datetime` 已在 entities.py 顶部 import——ZiweiMessage 已用同款，照抄即可。）

- [ ] **Step 2: 找路由注册处并准备注册**

Run: `grep -rn "routes.ziwei\|ziwei.router\|include_router" backend/app/api/v1/*.py backend/app/main.py | head`
记下 ziwei router 的注册方式（多半在 `app/api/v1/__init__.py` 或 `router.py`：`from .routes import ziwei` + `api_router.include_router(ziwei.router)`）。Task 步骤 5 照样加 qian。

- [ ] **Step 3: 写失败测试** `backend/tests/test_qian_routes.py`

镜像 `tests/test_ziwei_stream.py`：fake AIService + monkeypatch `qian_routes.SessionLocal`；用 per-table create + raw DDL 建 `qian_readings` + `ai_feedback`；SSE 解析。

```python
import json
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

import app.api.v1.routes.qian as qian_routes
from app.db.session import get_db
from app.main import app
from app.models.entities import QianReading

TEST_DIR = Path(mkdtemp(prefix="qian-tests-"))
engine = create_engine(f"sqlite:///{(TEST_DIR/'t.db').as_posix()}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class _FakeStream:
    def __init__(self, deltas): self._d = deltas
    def __enter__(self): return self
    def __exit__(self, *a): return False
    @property
    def text_stream(self):
        for d in self._d: yield d
    def get_final_message(self): return SimpleNamespace(usage=SimpleNamespace(input_tokens=120, output_tokens=80))


class _FakeMessages:
    def stream(self, *a, **k): return _FakeStream(["此乃上签。", "[[term:辰宫|地支]] 凡事可成。"])


class _FakeClient:
    def __init__(self): self.messages = _FakeMessages()


class _FakeAIService:
    is_available = True
    model = "test-model"
    def __init__(self, *a, **k): self.client = _FakeClient()


def override_get_db():
    db = TestingSessionLocal()
    try: yield db
    finally: db.close()


def setup_module():
    QianReading.__table__.create(bind=engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS ai_feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,"
            " feature VARCHAR(30) NOT NULL, reference_id INTEGER NOT NULL, user_input_hash TEXT NOT NULL,"
            " prompt_template TEXT, response_json TEXT, model VARCHAR(100), input_tokens INTEGER,"
            " output_tokens INTEGER, latency_ms INTEGER, created_at TIMESTAMP)"
        ))
    app.dependency_overrides[get_db] = override_get_db


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()
    rmtree(TEST_DIR, ignore_errors=True)


client = TestClient(app)


def _patch(monkeypatch):
    monkeypatch.setattr(qian_routes, "AIService", _FakeAIService)
    monkeypatch.setattr(qian_routes, "SessionLocal", TestingSessionLocal)


def _events(body: str):
    out = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            p = line[5:].strip()
            if p: out.append(json.loads(p))
    return out


def test_stream_draws_sign_text_camera_done_and_persists(monkeypatch):
    _patch(monkeypatch)
    r = client.post("/api/v1/qian/oracle/stream", json={"question": "今年事业？"})
    assert r.status_code == 200, r.text
    evs = _events(r.text)
    by = {}
    for e in evs: by.setdefault(e["type"], []).append(e)
    assert by["sign"][0]["sign"]["id"] and 1 <= by["sign"][0]["sign"]["id"] <= 100
    assert "".join(e["delta"] for e in by.get("text", [])).strip()
    assert by.get("camera") and by["camera"][0]["command"]["type"] == "explain_term"
    assert by.get("done")
    db = TestingSessionLocal()
    try:
        rows = db.scalars(select(QianReading)).all()
        assert len(rows) == 1 and rows[0].question == "今年事业？" and rows[0].response
    finally:
        db.close()


def test_stream_with_fixed_sign_id(monkeypatch):
    _patch(monkeypatch)
    r = client.post("/api/v1/qian/oracle/stream", json={"question": "问", "sign_id": 7})
    evs = _events(r.text)
    sign = next(e for e in evs if e["type"] == "sign")["sign"]
    assert sign["id"] == 7


def test_readings_list(monkeypatch):
    _patch(monkeypatch)
    client.post("/api/v1/qian/oracle/stream", json={"question": "甲"})
    r = client.get("/api/v1/qian/readings")
    assert r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) >= 1
```

Run → FAIL（路由不存在）。

- [ ] **Step 4: 写路由** `backend/app/api/v1/routes/qian.py`（镜像 ziwei stream 端点）

```python
"""观音灵签 求签 + AI 解签 端点。"""
import json
import logging
import time
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.config import get_settings
from app.db.session import SessionLocal, get_db
from app.models.entities import AIFeedback, QianReading, User
from app.services.ai_service import AIService
from app.services.qian.draw import draw_sign
from app.services.qian.oracle import QianOracle
from app.services.qian.signs import get_sign
from app.services.ziwei.oracle_tools import StreamMarkerParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qian", tags=["qian"])


class QianRequest(BaseModel):
    question: str
    sign_id: int | None = None


def _get_user_id(db: Session) -> int:
    return db.scalar(select(User.id).limit(1)) or 1


@router.post("/oracle/stream")
def qian_oracle_stream(payload: QianRequest, db: Session = Depends(get_db)):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(400, "请先写下你的问题")

    settings = get_settings()
    svc = AIService()
    if not svc.is_available:
        raise HTTPException(503, "解签师未启用（缺少 API Key）")

    today_start = datetime.combine(date.today(), datetime.min.time())
    used_today = db.scalar(
        select(func.coalesce(func.sum(AIFeedback.input_tokens + AIFeedback.output_tokens), 0))
        .where(AIFeedback.created_at >= today_start)
    ) or 0
    if used_today >= settings.ai_daily_token_budget:
        raise HTTPException(429, "今日额度已用尽，请明日再来")

    sign = get_sign(payload.sign_id) if payload.sign_id else draw_sign()
    if sign is None:
        raise HTTPException(404, "签不存在")

    oracle = QianOracle(client=svc.client, model=svc.model)
    system_prompt = oracle.system_prompt(sign, question)
    model, client = svc.model, svc.client
    uid = _get_user_id(db)

    def _persist(clean, cameras, segments, in_tok, out_tok, start):
        if not clean and not (in_tok or out_tok):
            return
        _db = SessionLocal()
        try:
            if clean:
                _db.add(QianReading(
                    question=question, sign_id=sign["id"], grade=sign["grade"], response=clean,
                    context_json={"sign": sign, "camera_commands": cameras, "segments": segments},
                ))
            _db.add(AIFeedback(
                user_id=uid, feature="qian_oracle", reference_id=sign["id"],
                user_input_hash="", prompt_template=None,
                response_json={"response": clean, "camera_commands": cameras},
                model=model, input_tokens=in_tok, output_tokens=out_tok,
                latency_ms=int((time.time() - start) * 1000),
            ))
            _db.commit()
        finally:
            _db.close()

    def event_stream():
        parser = StreamMarkerParser()
        in_tok = out_tok = 0
        start = time.time()
        # 先把抽到的签发给前端揭示
        yield {"data": json.dumps({"type": "sign", "sign": sign}, ensure_ascii=False)}
        try:
            with client.messages.stream(model=model, max_tokens=1200, system=system_prompt,
                                        messages=[{"role": "user", "content": question}]) as stream:
                for delta in stream.text_stream:
                    for kind, val in parser.feed(delta):
                        if kind == "text":
                            yield {"data": json.dumps({"type": "text", "delta": val}, ensure_ascii=False)}
                        else:
                            yield {"data": json.dumps({"type": "camera", "command": val}, ensure_ascii=False)}
                final = stream.get_final_message()
                in_tok, out_tok = final.usage.input_tokens, final.usage.output_tokens
            trailing, clean, segments, cameras = parser.finish()
            if trailing:
                yield {"data": json.dumps({"type": "text", "delta": trailing}, ensure_ascii=False)}
            _persist(clean, cameras, segments, in_tok, out_tok, start)
            yield {"data": json.dumps({"type": "done", "meta": {"model": model, "total_tokens": in_tok + out_tok}}, ensure_ascii=False)}
        except Exception:
            logger.exception("qian oracle stream failed (sign=%s)", sign["id"])
            try:
                _, clean, segments, cameras = parser.finish()
                _persist(clean, cameras, segments, in_tok, out_tok, start)
            except Exception:
                logger.exception("qian salvage-persist failed")
            yield {"data": json.dumps({"type": "error"}, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


@router.get("/readings")
def list_readings(db: Session = Depends(get_db)):
    rows = db.scalars(select(QianReading).order_by(QianReading.id.desc())).all()
    return [{
        "id": r.id, "question": r.question, "sign_id": r.sign_id, "grade": r.grade,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]


@router.get("/readings/{reading_id}")
def get_reading(reading_id: int, db: Session = Depends(get_db)):
    r = db.get(QianReading, reading_id)
    if not r:
        raise HTTPException(404, "记录不存在")
    return {
        "id": r.id, "question": r.question, "sign_id": r.sign_id, "grade": r.grade,
        "response": r.response, "context_json": r.context_json or {},
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
```

- [ ] **Step 5: 注册路由** —— 在 Step 2 找到的注册文件里照 ziwei 加：`from .routes import qian` + `api_router.include_router(qian.router)`（前缀确保最终为 `/api/v1/qian`）。

- [ ] **Step 6: 跑测试 + 全套回归**

Run `cd backend && python -m pytest tests/test_qian_routes.py -q` → 3 passed。
Run `cd backend && python -m pytest -q 2>&1 | tail -4` → 确认仅既存 test_api.py 的 21 个 JSONB error，无新失败。

- [ ] **Step 7: Commit**

```
git add backend/app/models/entities.py backend/app/api/v1/routes/qian.py backend/app/api/v1/__init__.py backend/tests/test_qian_routes.py
git commit -m "feat(qian): QianReading model + /qian/oracle/stream (draw+stream+persist) + readings"
```
（注册文件路径以 Step 2 实际为准。）

---

## Task 4: 叙事化播放指挥器参数化（注入镜头执行器）

**Files:**
- Modify: `frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts`
- Modify: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`

目的：`useOracleTour` 现在硬调 `fireCamera(cmd, {chart, onFocusBranch, onTerm})`（紫微专用）。改成由调用方注入 `fireCommand(cmd)`，让求签复用同一指挥器（求签注入自己的「术语卡/无镜头」执行器）。紫微行为不变。

- [ ] **Step 1: 改 `TourDeps` 与 `play`**（`use-oracle-tour.ts`）

把 `TourDeps` 中的 `chart` / `onFocusBranch` / `onTerm` 三个字段**替换**为一个：
```ts
  fireCommand: (cmd: CameraCommand) => void;
```
（保留 `onCaption`/`onReveal`/`onTourActiveChange`/`reducedMotion`。）
`play` 内把
```ts
        if (beat.command) fireCamera(beat.command, { chart: deps.chart, onFocusBranch: deps.onFocusBranch, onTerm: deps.onTerm });
```
改为
```ts
        if (beat.command) deps.fireCommand(beat.command);
```
并把收尾处的 `deps.onTerm(null); deps.onFocusBranch(null);` 改为通过 `fireCommand` 表达的「收尾指令」——为不扩大改动，**新增两条收尾**直接走 fireCommand：
```ts
      if (!isStale()) {
        deps.onReveal(full.trim());
        deps.fireCommand({ type: "overview" });            // 收尾回总览（紫微=回总览镜头；求签=可 no-op）
      }
```
（删掉原 `onTerm(null)`/`onFocusBranch(null)` 两行——清术语卡的职责移交给各自 fireCommand 处理 overview 时顺带做，见 Task 7/紫微适配。）
移除文件内对 `fireCamera`/`ZiweiChart`/`TermInfo` 的 import（若不再用）；`CameraCommand` 仍需从 `@/lib/ziwei/api` import。

- [ ] **Step 2: 紫微 `chat-dock.tsx` 适配——注入 fireCommand**

在 `chat-dock.tsx` 顶部确保 `import { fireCamera } from "./camera";` 在（Task 4 之前它已被移除；现在重新需要它来构造 fireCommand）。定义一个稳定的执行器并在两处 `tour.play(...)` 的 deps 里用它替换原来的 `chart/onFocusBranch/onTerm`：
```ts
  const fireCommand = (cmd: import("@/lib/ziwei/api").CameraCommand) => {
    if (cmd.type === "overview") { onFocusBranch(null); onTerm(null); return; }
    fireCamera(cmd, { chart, onFocusBranch, onTerm });
  };
```
两处 `tour.play(queue, { chart, onFocusBranch, onTerm, onCaption, onReveal, onTourActiveChange, reducedMotion })` →
`tour.play(queue, { fireCommand, onCaption, onReveal, onTourActiveChange, reducedMotion })`（`handleSend` 与 `replayMessage` 各一处）。
说明：原来收尾会 `onFocusBranch(null)+onTerm(null)`；现在收尾发 `{type:"overview"}` → 上面的 fireCommand 同样 `onFocusBranch(null)+onTerm(null)`，行为等价。

- [ ] **Step 3: 类型检查**

Run `cd frontend && npx tsc --noEmit 2>&1 | grep -E "use-oracle-tour|chat-dock"` → 空。

- [ ] **Step 4: Commit**

```
git add frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts frontend/src/components/ziwei/chat-dock/chat-dock.tsx
git commit -m "refactor(ziwei): parameterize tour conductor with injected fireCommand (enables qian reuse)"
```

---

## Task 5: 求签前端 API 客户端

**Files:**
- Create: `frontend/src/lib/qian/api.ts`

- [ ] **Step 1: 写 `api.ts`**（镜像 `lib/ziwei/api.ts` 的 `streamOracle` + 新增 `onSign`）

```ts
import { API_BASE } from "@/lib/api";
import type { CameraCommand } from "@/lib/ziwei/api";

export class QianApiError extends Error {
  constructor(public status: number, detail?: string) { super(detail ?? `Request failed: ${status}`); }
}

export type QianSign = {
  id: number; grade: string; palace: string; title: string;
  poetry: string; meaning: string; holy: string;
};

export type QianStreamHandlers = {
  onSign: (sign: QianSign) => void;
  onText: (delta: string) => void;
  onCamera: (command: CameraCommand) => void;
  onDone: (meta: { model?: string; total_tokens?: number }) => void;
  onError: () => void;
};

export type QianReadingOut = { id: number; question: string; sign_id: number; grade: string; created_at: string | null };

async function streamOracle(
  body: { question: string; sign_id?: number },
  handlers: QianStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/qian/oracle/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), cache: "no-store", signal,
  });
  if (!res.ok || !res.body) {
    const err = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new QianApiError(res.status, typeof err?.detail === "string" ? err.detail : undefined);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done || signal?.aborted) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const t = line.trim();
      if (!t.startsWith("data:")) continue;
      const raw = t.slice(5).trim();
      if (!raw) continue;
      let ev: { type: string; [k: string]: unknown };
      try { ev = JSON.parse(raw); } catch { continue; }
      if (ev.type === "sign") handlers.onSign(ev.sign as QianSign);
      else if (ev.type === "text") handlers.onText(ev.delta as string);
      else if (ev.type === "camera") handlers.onCamera(ev.command as CameraCommand);
      else if (ev.type === "done") handlers.onDone((ev.meta as { model?: string; total_tokens?: number }) ?? {});
      else if (ev.type === "error") handlers.onError();
    }
  }
}

export const qianApi = {
  streamOracle,
  listReadings: () => fetch(`${API_BASE}/qian/readings`, { cache: "no-store" }).then((r) => r.json() as Promise<QianReadingOut[]>),
};
```

- [ ] **Step 2: 类型检查 + Commit**

Run `cd frontend && npx tsc --noEmit 2>&1 | grep "qian/api"` → 空。
```
git add frontend/src/lib/qian/api.ts
git commit -m "feat(qian): frontend api client (streamOracle with onSign + readings)"
```

---

## Task 6: 3D 签筒场景

**Files:**
- Create: `frontend/src/components/qian/scene3d/qian-scene.tsx`（默认导出，dynamic 加载）
- Create: `frontend/src/components/qian/scene3d/sign-cylinder.tsx`（签筒 + 签条 + 摇签动画）

参考紫微 `scene3d/scene-3d.tsx`（Canvas/PerformanceMonitor/quality/context-loss 善后）与 `camera-rig.tsx`。配色用 spec §8 暖金/朱赭/暖黑。

- [ ] **Step 1: 写 `sign-cylinder.tsx`**——一个签筒（圆柱）+ 一束细签条（细长 box 阵列），`shaking` 为真时整体小幅摇摆（`useFrame` 帧无关 `1-exp(-k·dt)` 抖动）；`drawnId` 非空时一支签条升起。

```tsx
"use client";
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group } from "three";

export function SignCylinder({ shaking, drawn }: { shaking: boolean; drawn: boolean }) {
  const cup = useRef<Group>(null);
  const stick = useRef<Group>(null);
  const t = useRef(0);
  useFrame((_, dt) => {
    t.current += dt;
    if (cup.current) {
      const amp = shaking ? 0.18 : 0;
      cup.current.rotation.z = Math.sin(t.current * 18) * amp;
      cup.current.position.x = Math.sin(t.current * 22) * amp * 0.3;
    }
    if (stick.current) {
      const targetY = drawn ? 2.4 : 0.2;
      stick.current.position.y += (targetY - stick.current.position.y) * (1 - Math.exp(-6 * dt));
    }
  });
  return (
    <group>
      <group ref={cup}>
        <mesh position={[0, 0, 0]}>
          <cylinderGeometry args={[0.9, 1.0, 2.2, 32, 1, true]} />
          <meshStandardMaterial color="#7a3b1d" metalness={0.3} roughness={0.6} side={2} />
        </mesh>
        {/* 一束静态签条 */}
        {Array.from({ length: 14 }).map((_, i) => (
          <mesh key={i} position={[Math.cos(i) * 0.4, 1.1, Math.sin(i) * 0.4]} rotation={[0, 0, (i % 5 - 2) * 0.04]}>
            <boxGeometry args={[0.06, 1.8, 0.06]} />
            <meshStandardMaterial color="#d9c6a0" roughness={0.7} />
          </mesh>
        ))}
      </group>
      {/* 升起的那支签 */}
      <group ref={stick} position={[0, 0.2, 0.5]}>
        <mesh>
          <boxGeometry args={[0.1, 2.6, 0.1]} />
          <meshStandardMaterial color="#d6a84a" emissive="#b9472f" emissiveIntensity={drawn ? 0.35 : 0} metalness={0.4} roughness={0.4} />
        </mesh>
      </group>
    </group>
  );
}
```

- [ ] **Step 2: 写 `qian-scene.tsx`**（Canvas + 灯光 + 暖色氛围 + SignCylinder；props 透传 shaking/drawn + onRenderError）

```tsx
"use client";
import { Suspense, useState, useEffect, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { PerformanceMonitor } from "@react-three/drei";
import { SignCylinder } from "./sign-cylinder";

export type QianSceneProps = { shaking: boolean; drawn: boolean; onRenderError?: () => void };

export default function QianScene({ shaking, drawn, onRenderError }: QianSceneProps) {
  const [q, setQ] = useState<"high" | "low">("high");
  const disposed = useRef(false);
  useEffect(() => () => void (disposed.current = true), []);
  return (
    <Canvas
      dpr={q === "high" ? [1, 1.75] : 1}
      camera={{ position: [0, 1.6, 6], fov: 42 }}
      style={{ background: "#140e08" }}
      onCreated={({ gl }) => {
        if (gl.getContext().isContextLost()) onRenderError?.();
        gl.domElement.addEventListener("webglcontextlost", () => { if (!disposed.current) onRenderError?.(); }, { once: true });
      }}
    >
      <PerformanceMonitor onDecline={() => setQ("low")}>
        <color attach="background" args={["#140e08"]} />
        <fog attach="fog" args={["#140e08", 9, 22]} />
        <ambientLight intensity={0.5} color="#f0d9a8" />
        <directionalLight position={[3, 6, 4]} intensity={0.8} color="#ffcf8a" />
        <pointLight position={[0, 2, 3]} intensity={0.6} color="#b9472f" />
        <Suspense fallback={null}>
          <SignCylinder shaking={shaking} drawn={drawn} />
        </Suspense>
      </PerformanceMonitor>
    </Canvas>
  );
}
```

- [ ] **Step 3: 类型检查（看新增错误，不看既存 3D 噪声）**

Run `cd frontend && npx tsc --noEmit 2>&1 | grep -E "qian/scene3d"` —— 会有 `Cannot find module '@react-three/*'` 既存噪声（本地缺依赖），但**不得**有新的属性/类型错误（JSX intrinsic 报错与紫微 scene3d 同类，属既存环境噪声）。CI `next build` 为准。

- [ ] **Step 4: Commit**

```
git add frontend/src/components/qian/scene3d/qian-scene.tsx frontend/src/components/qian/scene3d/sign-cylinder.tsx
git commit -m "feat(qian): 3D sign-cylinder scene (shake animation + stick rise, temple palette)"
```

---

## Task 7: 求签 workspace + 解签面板（复用指挥器/CloudNarration/术语卡）

**Files:**
- Create: `frontend/src/components/qian/qian-workspace.tsx`
- Create: `frontend/src/components/qian/qian-camera.ts`（求签镜头执行器）

- [ ] **Step 1: 写 `qian-camera.ts`**（求签的 fireCommand：只管术语卡；focus/overview 对 3D 无落点 → 收尾清术语卡）

```ts
"use client";
import type { CameraCommand } from "@/lib/ziwei/api";
import type { TermInfo } from "@/components/ziwei/term-card";

/** 求签的镜头执行器：3D 是单签筒、无宫位落点，故 focus/overview 仅用于收尾清术语卡；term 弹卡。 */
export function makeQianFireCommand(onTerm: (t: TermInfo | null) => void) {
  return (cmd: CameraCommand) => {
    if (cmd.type === "explain_term") onTerm({ term: cmd.term, explanation: cmd.explanation });
    else if (cmd.type === "overview") onTerm(null); // 收尾
  };
}
```

- [ ] **Step 2: 写 `qian-workspace.tsx`**——问题输入 + 摇签按钮 + 揭签卡（签号/吉凶/签诗）+ 解签流式面板（复用 `useOracleTour` + `CloudNarration` 经由 `tour` 内部 + 术语卡 + 首次出声提示）。3D 由父页传入（见 Task 8）或在此内联 `QianScene`。这里内联场景 + 状态机：

```tsx
"use client";
import dynamic from "next/dynamic";
import { useRef, useState } from "react";
import { qianApi, QianApiError, type QianSign } from "@/lib/qian/api";
import { useOracleTour } from "@/components/ziwei/chat-dock/use-oracle-tour";
import { TermCard, type TermInfo } from "@/components/ziwei/term-card";
import { makeQianFireCommand } from "./qian-camera";

const QianScene = dynamic(() => import("./scene3d/qian-scene"), { ssr: false, loading: () => (
  <div className="flex h-full min-h-[420px] items-center justify-center"><p className="animate-pulse text-sm text-[#d6a84a]/70">正在备好签筒……</p></div>
) });

export function QianWorkspace() {
  const [question, setQuestion] = useState("");
  const [phase, setPhase] = useState<"idle" | "shaking" | "reading">("idle");
  const [sign, setSign] = useState<QianSign | null>(null);
  const [answer, setAnswer] = useState("");
  const [term, setTerm] = useState<TermInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const tour = useOracleTour();

  const shake = async () => {
    const q = question.trim();
    if (!q || phase !== "idle") return;
    abortRef.current?.abort(); tour.cancel();
    const controller = new AbortController(); abortRef.current = controller;
    setPhase("shaking"); setSign(null); setAnswer(""); setError(null); setTerm(null);
    const reduced = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const { queue, handlers } = tour.begin();
    const playPromise = tour.play(queue, {
      fireCommand: makeQianFireCommand(setTerm),
      onCaption: () => {},
      onReveal: (full) => { setAnswer(full); },
      onTourActiveChange: () => {},
      reducedMotion: reduced,
    });
    try {
      await qianApi.streamOracle({ question: q }, {
        onSign: (s) => { setSign(s); setPhase("reading"); handlers.onText(""); },
        onText: handlers.onText,
        onCamera: handlers.onCamera,
        onDone: handlers.onDone as unknown as (cid: number) => void, // onDone 签名兼容：见 note
        onError: handlers.onError,
      }, controller.signal);
    } catch (e) {
      tour.cancel();
      if (e instanceof DOMException && e.name === "AbortError") { await playPromise; return; }
      if (e instanceof QianApiError && e.status === 503) setError("解签师未启用（缺少 API Key）");
      else if (e instanceof QianApiError && e.status === 429) setError("今日额度已用尽，请明日再来");
      else setError("解签暂不可用，请稍后再试");
      await playPromise; setPhase("idle"); return;
    }
    await playPromise; setPhase("idle");
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div className="relative overflow-hidden rounded-[28px] border border-[#d6a84a]/20 bg-[#140e08] min-h-[420px] h-[64vh]">
        <QianScene shaking={phase === "shaking"} drawn={!!sign} onRenderError={() => {}} />
        {term ? <TermCard info={term} onClose={() => setTerm(null)} /> : null}
      </div>
      <div className="flex flex-col gap-4">
        <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={3}
          placeholder="写下你想问的事，例如「这段时间的事业」……"
          className="resize-none rounded-2xl border border-[#d6a84a]/30 bg-[#1b130b] px-4 py-3 text-sm text-[#f4ece0] placeholder-[#d6a84a]/40 outline-none focus:border-[#d6a84a]/60" />
        <button type="button" onClick={() => void shake()} disabled={!question.trim() || phase !== "idle"}
          className="rounded-2xl bg-gradient-to-br from-[#d6a84a] to-[#b9472f] px-4 py-3 text-sm font-semibold text-[#140e08] disabled:opacity-40">
          {phase === "idle" ? "摇 签" : phase === "shaking" ? "摇签中…" : "解签中…"}
        </button>
        {error ? <p className="text-xs text-[#e8794f]" role="alert">{error}</p> : null}
        {sign ? (
          <div className="rounded-2xl border border-[#d6a84a]/25 bg-[#1b130b] p-4">
            <p className="text-xs text-[#d6a84a]">第 {sign.id} 签 · {sign.grade} · {sign.palace}</p>
            <p className="mt-1 text-sm font-semibold text-[#f4ece0]">{sign.title}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-[#e9dcc4]">{sign.poetry}</p>
          </div>
        ) : null}
        {answer ? <div className="whitespace-pre-wrap rounded-2xl border border-[#d6a84a]/15 bg-[#1b130b]/60 p-4 text-sm leading-relaxed text-[#f4ece0]">{answer}</div> : null}
      </div>
    </div>
  );
}
```

**Note（实现时处理）：** `useOracleTour` 的 `onReveal` 是「揭全文」，求签解读期可不显大段文字、结束揭全文（与紫微一致）——本面板把 `onReveal` 写进 `answer`，解读期 `answer` 为空、签卡 + 3D + 声音为主，结束铺全文，符合 spec。`onDone` 的签名紫微是 `(cid:number)`；求签无 conversationId，传一个忽略入参的函数即可（把上面 `handlers.onDone as unknown as ...` 换成显式 `() => {}` 更干净——实现时用 `onDone: () => {}`，并让 `tour` 的 done 不依赖 cid）。**CloudNarration 声音**：`useOracleTour` 内部 `getNarration()` 已默认 CloudNarration（打 `/ziwei/tts`），求签自动有配音，无需改动。

- [ ] **Step 3: 类型检查**

Run `cd frontend && npx tsc --noEmit 2>&1 | grep -E "qian-workspace|qian-camera"` → 空（修掉 Note 里 onDone 的 as-cast，用 `onDone: () => {}`）。

- [ ] **Step 4: Commit**

```
git add frontend/src/components/qian/qian-workspace.tsx frontend/src/components/qian/qian-camera.ts
git commit -m "feat(qian): workspace — question→shake→reveal sign→streamed 解签 (reuses tour + voice + term card)"
```

---

## Task 8: `/qian` 页 + 侧边栏「灵签」+ 历史

**Files:**
- Create: `frontend/src/app/qian/page.tsx`
- Create: `frontend/src/app/qian/layout.tsx`（OG 元数据，复用 toolkits 模式，可选但建议）
- Modify: `frontend/src/components/layout/sidebar-nav.tsx`

- [ ] **Step 1: `page.tsx`**（标题区 + QianWorkspace；暖金标题）

```tsx
"use client";
import { Scroll } from "lucide-react";
import { QianWorkspace } from "@/components/qian/qian-workspace";

export default function QianPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-gradient-to-br from-[#d6a84a] to-[#b9472f] text-[#140e08] shadow-[0_6px_16px_-6px_rgba(214,168,74,0.6)]">
          <Scroll className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-[#b9472f]">观音灵签 · Oracle</span>
          <h1 className="font-display text-2xl leading-tight text-ink">灵签</h1>
        </div>
      </div>
      <p className="text-sm text-ink/55">静心默想所问之事，再摇签。签为公版古诗，解签仅供参考、博君一宽。</p>
      <QianWorkspace />
    </div>
  );
}
```

- [ ] **Step 2: `layout.tsx`**（服务端 OG，复用 toolkits 模式）

```tsx
import type { Metadata } from "next";
const title = "灵签 · 观音灵签求签";
const description = "静心问一事，摇一支观音灵签，AI 解签人为你解读签诗。";
export const metadata: Metadata = {
  title, description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary", title, description },
};
export default function QianLayout({ children }: { children: React.ReactNode }) { return <>{children}</>; }
```

- [ ] **Step 3: 侧边栏注册** —— `sidebar-nav.tsx`：import 加 `Scroll`；`items` 数组在 `紫微斗数` 之后插入 `{ href: "/qian", label: "灵签", icon: Scroll }`。

- [ ] **Step 4: 历史「我的灵签」（轻量，可并入 workspace 或独立）** —— V1 先用 `qianApi.listReadings()` 在 workspace 下方列出近几条（签号+吉凶+问题+时间），点开调 `/qian/readings/{id}` 显示存档解读。若想控制范围，本步可标记为「V1 仅列表、详情/重听留扩展」并在 `log` 式注释说明。最简：workspace 加一个折叠的「我的灵签」列表（只读）。

```tsx
// 在 QianWorkspace 顶部状态加： const [history, setHistory] = useState<QianReadingOut[]>([]);
// useEffect(() => { qianApi.listReadings().then(setHistory).catch(() => {}); }, [phase]);
// 在右栏底部渲染 history.slice(0,5) 的只读列表（签号·吉凶·问题·时间）。
```
（import `type { QianReadingOut }` from api。）

- [ ] **Step 5: 类型检查 + Commit**

Run `cd frontend && npx tsc --noEmit 2>&1 | grep -E "app/qian|sidebar-nav"` → 空。
```
git add frontend/src/app/qian/page.tsx frontend/src/app/qian/layout.tsx frontend/src/components/layout/sidebar-nav.tsx frontend/src/components/qian/qian-workspace.tsx
git commit -m "feat(qian): /qian page + 灵签 sidebar entry + readings history"
```

---

## Task 9: 收尾 + 部署 + prod 验证

- [ ] **Step 1: 全量类型检查（前端）** —— `cd frontend && npx tsc --noEmit 2>&1 | grep "error TS" | grep -vE "scene3d/|camera-rig.tsx|qian/scene3d|iztro|chart.ts"` → 空（仅 3D module-resolution 噪声）。
- [ ] **Step 2: 全套后端测试** —— `cd backend && python -m pytest -q 2>&1 | tail -4`，确认 qian 测试全绿、无新失败（test_api.py 21 个 JSONB error 既存）。
- [ ] **Step 3: 最终整体审查（spec 对照）** —— 抽签随机/公版签诗不改/流式先吐签/解签人设/叙事化播放+配音复用/配色 §8/历史。修发现的问题。
- [ ] **Step 4: 部署**（[[deployment_rules]]）—— `git push origin main && git tag vX.Y.Z && git push origin vX.Y.Z && gh run watch <id> --exit-status`（版本以 `git tag --sort=-v:refname` 当前最高 +0.1.0）。
- [ ] **Step 5: prod 验证** —— ① `POST /api/v1/qian/oracle/stream {"question":"测试"}` 看 200 + 先 `sign` 事件 + text/camera/done；② 浏览器 `/qian` 问一条：摇签动画→揭签→解签流式+配音念签诗、术语卡、配色暖金庙宇感；③ 分享 `/qian` 看 OG 标题。
- [ ] **Step 6: 更新记忆** —— 新增/更新一条记忆（灵签板块上线：观音 100 签、抽签/解签/流式/配音复用、配色、指挥器参数化、扩展位）。关联 [[ziwei_phase1_progress]]。

---

## Self-Review（计划对照 spec）
- **观音 100 签语料（§4）** → T1（生成脚本 + signs.py + draw）✓
- **解签人设 + AI 解签单次内联标记（§5）** → T2 ✓
- **`/qian/oracle/stream` 先吐签+流式+持久化 + QianReading + 历史（§5）** → T3 ✓
- **复用叙事化播放（§6）** → T4 指挥器参数化 + T7 注入求签执行器 ✓
- **复用 MiniMax 配音（§5/§6）** → CloudNarration 经 `/ziwei/tts`，T7 自动获得（useOracleTour 内置）✓
- **3D 摇签筒 + 揭签（§3/§6）** → T6 + T7 ✓
- **独立板块 + 侧边栏（§2）** → T8 ✓
- **配色 §8** → T6/T7/T8 全用暖金#d6a84a/朱赭#b9472f/暖黑#140e08 ✓
- **服务端随机抽签（§9）** → T1 draw.py secrets ✓
- **边界/免责（§11）** → T3 状态码 + T8 页面注明 ✓
- **测试（§12）** → T1/T2/T3 pytest；前端 tsc+build+prod ✓
- **类型一致**：`QianSign`/`QianStreamHandlers`(onSign+onDone)/`CameraCommand`(复用 ziwei)/`fireCommand`(TourDeps 新字段)/`makeQianFireCommand`/`QianReading`/`/qian/oracle/stream` 事件 `sign|text|camera|done|error` —— 跨任务一致 ✓
- 占位符扫描：T8 Step 4 历史为「最简只读列表」明确范围，非占位；其余代码完整 ✓
- 风险点：T4 改动已上线的紫微 chat-dock/指挥器——已给等价行为说明（收尾 overview 指令 = 原 onFocusBranch(null)+onTerm(null)），需最终审查确认紫微行为不回归。
```
