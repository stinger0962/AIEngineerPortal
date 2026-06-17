"""评审 Critique: structured per-dimension paper/essay evaluation via Claude,
plus text extraction from uploaded .docx / .pdf / .md / .txt files.

Design note: the per-dimension scores are a DIAGNOSTIC dashboard, not a single
composite number to be maximized — the actionable critique is what drives real
improvement. (See the project discussion on reward-hacking an LLM judge.)
"""
from __future__ import annotations

import io
import json
import zipfile
from typing import Any, Dict, List, Tuple
from xml.etree import ElementTree as ET

_MIN_CHARS = 200
_MAX_CHARS = 60000  # cap input to keep token cost / latency sane (~ a long paper)

PAPER_TYPES = {
    "research": "学术 / 研究论文",
    "argument": "议论文 / Essay",
    "statement": "个人陈述 / 申请文书",
}

_REVISE_MAX_CHARS = 15000  # revise outputs the full rewritten text — keep within output limits

# Output language for critique / suggestions / revision rationale.
_LANG = {
    "zh": "用简体中文书写所有评语、建议与说明。",
    "en": "Write all critique, suggestions and notes in English.",
    "auto": "用论文本身的主要语言书写所有评语、建议与说明（英文论文 → 英文）。",
}


def _lang_instr(output_lang: str) -> str:
    return _LANG.get(output_lang, _LANG["auto"])


# Hard formatting rules — the model otherwise serializes nested fields as strings
# AND uses ASCII double-quotes inside Chinese prose, producing invalid JSON.
_FMT = (
    "【格式硬性要求】所有嵌套字段必须是真正的 JSON 对象/数组，切勿序列化成字符串。"
    "任何文字字段中如需强调或引用，一律使用中文引号「」或书名号《》，"
    "严禁使用英文双引号（会破坏结构）。"
)


def _maybe_json(v: Any) -> Any:
    """Claude's tool calls sometimes return nested object/array params as JSON
    STRINGS instead of structured values. If v looks like serialized JSON, parse it."""
    if isinstance(v, str):
        s = v.strip()
        if s[:1] in ("{", "["):
            try:
                return json.loads(s)
            except (ValueError, TypeError):
                return v
    return v


def _as_list(v: Any) -> List[Any]:
    v = _maybe_json(v)
    if isinstance(v, list):
        return v
    if v is None or v == "":
        return []
    return [v]


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "是")
    return bool(v)


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _docx_footnotes(raw: bytes) -> List[Tuple[str, str]]:
    """Pull (id, text) footnotes from a .docx — python-docx omits them. They live
    in word/footnotes.xml; skip the separator/continuationSeparator placeholders."""
    out: List[Tuple[str, str]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if "word/footnotes.xml" not in z.namelist():
                return out
            xml = z.read("word/footnotes.xml")
        root = ET.fromstring(xml)
        for fn in root.findall(f"{_W}footnote"):
            if fn.get(f"{_W}type") in ("separator", "continuationSeparator"):
                continue
            fid = fn.get(f"{_W}id") or "?"
            text = "".join(t.text or "" for t in fn.iter(f"{_W}t")).strip()
            if text:
                out.append((fid, text))
    except (zipfile.BadZipFile, ET.ParseError, KeyError):
        return []
    return out


def extract_text(filename: str, raw: bytes) -> str:
    """Extract plain text from an uploaded file. Supports .docx / .pdf / .md / .txt.
    For .docx, footnotes are appended (labeled) since they're part of the paper and
    document-level review needs to see them."""
    name = (filename or "").lower()
    if name.endswith(".docx"):
        import docx  # python-docx

        doc = docx.Document(io.BytesIO(raw))
        body = "\n".join(p.text for p in doc.paragraphs).strip()
        notes = _docx_footnotes(raw)
        if notes:
            body += "\n\n【脚注 Footnotes】\n" + "\n".join(f"[{fid}] {text}" for fid, text in notes)
        return body.strip()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if name.endswith((".md", ".markdown", ".txt", ".text")):
        return raw.decode("utf-8", errors="replace").strip()
    # Best-effort: treat unknown extensions as utf-8 text.
    try:
        return raw.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ValueError(f"不支持的文件类型：{filename}（请用 .docx / .pdf / .md / .txt）") from exc


_TOOL = {
    "name": "report_evaluation",
    "description": "Return the structured rubric evaluation of the paper.",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall": {
                "type": "object",
                "properties": {
                    "band": {"type": "string", "description": "整体档位，四选一：草稿 / 打磨中 / 可投 / 较强"},
                    "summary": {"type": "string", "description": "一句话总体诊断"},
                    "top_fix": {"type": "string", "description": "最值得先改的一件事，单点最大杠杆，具体可执行"},
                },
                "required": ["band", "summary", "top_fix"],
            },
            "dimensions": {
                "type": "array",
                "description": "5–6 个评估维度",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "维度名，如 论点 Thesis"},
                        "layer": {
                            "type": "string",
                            "enum": ["writing", "substance"],
                            "description": "层级：writing=写作层（编辑可代改：论点表达/论证组织/结构连贯/行文用词）；substance=实质层（需作者补充真材料才能改：严谨性/原创与贡献）",
                        },
                        "score": {"type": "integer", "description": "1–10 分"},
                        "critique": {"type": "string", "description": "强在哪、弱在哪，引用文中真实问题，不空泛"},
                        "suggestions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "1–3 条具体可执行的修改建议",
                        },
                    },
                    "required": ["label", "layer", "score", "critique", "suggestions"],
                },
            },
        },
        "required": ["overall", "dimensions"],
    },
}

_SYSTEM = """你是一位严格、就事论事的学术写作评审，不奉承、不说空话。给定一篇{type}，按 5–6 个维度评估：
论点(Thesis) / 论证与证据(Argument & Evidence) / 结构与连贯(Structure) / 严谨性(Rigor，研究类含方法是否恰当、结论是否被支撑、有无过度声称) / 原创与贡献(Originality) / 行文(Writing)。
按论文类型调整侧重：议论文重说服力与逻辑链；个人陈述重真诚、个人声音与具体性（少讲大道理）。
每个维度标注 layer：论点 / 论证与证据 / 结构与连贯 / 行文 属 writing（写作层，编辑可代为修改）；严谨性 / 原创与贡献 属 substance（实质层，AI 不能代为编造数据、证据或新观点，须作者补充真材料）。

规则：
- 每个维度给 1–10 分 + **具体**简评（指出文中真实的强点与弱点，可引用片段），再给 1–3 条**可执行**的修改建议（落到具体段落/句子，不要泛泛说"加强论证"）。
- 分数用于诊断，不是取悦作者。宁严勿松，分数要拉开区分度，避免全是 7–8 分。
- overall.top_fix：如果只改一件事，改什么——单点最大杠杆。
- {lang}
{fmt}
只通过 report_evaluation 工具返回结构化结果，不要输出其它文字。"""


def _run_tool(anthropic_api_key: str, model: str, *, max_tokens: int, system: str, user: str, tool: dict, fail_msg: str, attempts: int = 3) -> Dict[str, Any]:
    """Forced-tool Claude call → the tool's input dict. Retries on transient API
    errors and on the model occasionally failing to emit a usable structured
    payload (it sometimes returns the tool input as a JSON string). Raises ValueError
    once attempts are exhausted."""
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    last_err: str = "模型未返回结构化结果，请重试。"
    for _ in range(max(1, attempts)):
        try:
            msg = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # transient API error → retry
            last_err = str(exc)
            continue
        types = [getattr(b, "type", "?") for b in msg.content]
        for block in msg.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
                data = _maybe_json(block.input)  # the model sometimes returns the whole input as a JSON string
                if isinstance(data, dict):
                    return data
                last_err = f"tool_use input type={type(block.input).__name__} stop={getattr(msg, 'stop_reason', '?')}"
                break
        else:
            last_err = f"no tool_use; blocks={types} stop={getattr(msg, 'stop_reason', '?')}"
    raise ValueError(f"{fail_msg}：{last_err}")


def evaluate(text: str, paper_type: str, output_lang: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Run the rubric evaluation. Returns {overall, dimensions}. Raises ValueError
    on bad input / API failure."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字再评估。")
    truncated = len(text) > _MAX_CHARS
    if truncated:
        text = text[:_MAX_CHARS]

    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    note = "\n\n（注：正文过长，仅评估前约 6 万字。）" if truncated else ""
    result = _run_tool(
        anthropic_api_key,
        model,
        max_tokens=8000,  # 6-dim Chinese critique easily exceeds 3000 → truncated tool JSON → unusable
        system=_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"论文类型：{type_label}{note}\n\n论文正文：\n\n{text}",
        tool=_TOOL,
        fail_msg="评估失败",
    )
    # Claude may stringify the nested object/array params — coerce back to structure.
    overall = _maybe_json(result.get("overall"))
    dims = _as_list(result.get("dimensions"))
    if not isinstance(overall, dict) or not dims:
        raise ValueError("评估失败：模型未返回结构化结果，请重试。")
    _SUBSTANCE_HINTS = ("严谨", "rigor", "原创", "贡献", "originality", "contribution")
    for d in dims:
        if isinstance(d, dict):
            d["suggestions"] = _as_list(d.get("suggestions"))
            layer = str(d.get("layer") or "").strip().lower()
            if layer not in ("writing", "substance"):
                label = str(d.get("label") or "").lower()
                layer = "substance" if any(h in label for h in _SUBSTANCE_HINTS) else "writing"
            d["layer"] = layer
    return {"overall": overall, "dimensions": dims}


# ── 改进层：助攻式单轮 revise + 成对裁决 judge ──────────────────────────────

_REVISE_TOOL = {
    "name": "propose_revision",
    "description": "Return one improved revision of the paper plus what changed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "revised": {"type": "string", "description": "完整的改后正文"},
            "changes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2–5 条：这一轮改了什么、为什么",
            },
        },
        "required": ["revised", "changes"],
    },
}

_REVISE_SYSTEM = """你是一位资深学术编辑。给定一篇{type}，产出一个**改进版**：
- 只改**写作层面**：表达清晰度、结构与段落组织、论证链条、用词与语域。
- **绝不**编造事实、数据、引用、实验结果或原文没有的内容；保留作者的核心观点、论据与个人语气。
- 优先修复最影响质量的问题（论点不清、结构松散、论证跳步、行文冗余），不要大幅删改作者的实质内容，篇幅量级与原文相当。
- {lang}（注：这是评语/说明的语言；正文 revised 必须与原文保持同一种语言）。
{fmt}
通过 propose_revision 工具返回完整改后正文与改动说明。"""

_JUDGE_TOOL = {
    "name": "report_verdict",
    "description": "Judge whether version B is genuinely better than version A.",
    "input_schema": {
        "type": "object",
        "properties": {
            "better": {"type": "boolean", "description": "B 是否在整体写作质量上真的优于 A"},
            "reason": {"type": "string", "description": "为什么更好/没更好，具体"},
            "dimensions_improved": {
                "type": "array",
                "items": {"type": "string"},
                "description": "B 相比 A 有提升的维度（如 论点 / 结构 / 行文）",
            },
        },
        "required": ["better", "reason", "dimensions_improved"],
    },
}

_JUDGE_SYSTEM = """你是严格中立的写作评审。下面是同一篇{type}的两个版本 A 与 B。判断 B 在整体写作质量上是否**真的优于** A（清晰度 / 结构 / 论证 / 行文）。
实事求是：若 B 并未更好、甚至更差（丢失内容、语气走样、变空洞、引入错误），就如实判 better=false。不要因为 B 更长或措辞更花哨就判更好。
{lang}
{fmt}
通过 report_verdict 工具返回 {{better, reason, dimensions_improved}}。"""


def revise(text: str, paper_type: str, output_lang: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Produce one assisted revision (writing-layer only). Returns {revised, changes}."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字再改进。")
    if len(text) > _REVISE_MAX_CHARS:
        raise ValueError(f"正文较长，单轮改进上限约 {_REVISE_MAX_CHARS // 1000} 千字，请分段改进。")
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    result = _run_tool(
        anthropic_api_key,
        model,
        max_tokens=8000,
        system=_REVISE_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"论文类型：{type_label}\n\n原文：\n\n{text}",
        tool=_REVISE_TOOL,
        fail_msg="改进失败",
    )
    revised = _maybe_json(result.get("revised"))
    if not isinstance(revised, str) or not revised.strip():
        raise ValueError("改进失败：模型未返回改后正文，请重试。")
    return {"revised": revised, "changes": _as_list(result.get("changes"))}


def judge_pair(original: str, revised: str, paper_type: str, output_lang: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Pairwise verdict: is the revision genuinely better? Returns {better, reason, dimensions_improved}."""
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    result = _run_tool(
        anthropic_api_key,
        model,
        max_tokens=1000,
        system=_JUDGE_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"版本 A（原文）：\n\n{original}\n\n———\n\n版本 B（改后）：\n\n{revised}",
        tool=_JUDGE_TOOL,
        fail_msg="裁决失败",
    )
    return {
        "better": _as_bool(result.get("better")),
        "reason": result.get("reason") or "",
        "dimensions_improved": _as_list(result.get("dimensions_improved")),
    }


# ── 文档级审阅：通读全文 → 定位明确的编辑建议清单（不重写全文）─────────────

_DOCREVIEW_TOOL = {
    "name": "report_doc_findings",
    "description": "Document-level review findings the author applies in their own editor.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "一句话总体说明（如：发现 3 处重复脚注、2 处术语不一致）"},
            "findings": {
                "type": "array",
                "description": "逐条文档级问题，按严重度排序",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "类别：脚注引用 / 术语一致性 / 重复冗余 / 结构 / 格式 / 其它"},
                        "severity": {"type": "string", "description": "严重度：高 / 中 / 低"},
                        "location": {"type": "string", "description": "定位：脚注编号、章节、或一小段引用片段，便于作者找到"},
                        "issue": {"type": "string", "description": "问题是什么"},
                        "recommendation": {"type": "string", "description": "具体动作，如『删除脚注 7（与脚注 2 重复）』"},
                    },
                    "required": ["category", "severity", "location", "issue", "recommendation"],
                },
            },
        },
        "required": ["summary", "findings"],
    },
}

_DOCREVIEW_SYSTEM = """你是资深的文档级审阅编辑。通读整篇{type}（含末尾【脚注】区，若有），找出需要作者处理的**文档级**问题，重点：
- **脚注/引用**：重复或多余的脚注、可合并的脚注、编号或格式不一致、引文与正文对不上。
- **术语一致性**：同一概念前后用词不一（如 AI / 人工智能混用）、缩写未统一。
- **重复冗余**：内容/论点重复、可删的赘述。
- **结构**：段落顺序、标题层级、过渡缺失。
- **格式**：明显的体例不一致。

每条给出：类别 / 严重度（高·中·低）/ 定位（脚注编号或一小段引用，便于作者定位）/ 问题 / **具体动作建议**（例如『删除脚注 7，与脚注 2 内容重复』『将全文“人工智能”统一为“AI”』）。
这是**给作者执行的清单**——你只诊断与建议，绝不重写全文、绝不编造原文没有的内容。按严重度从高到低排列；没问题的类别就不列。
{lang}
{fmt}
只通过 report_doc_findings 工具返回。"""


def doc_review(text: str, paper_type: str, output_lang: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Document-level review: read the whole doc, return an actionable edit list
    (NOT a rewrite). Returns {summary, findings:[{category,severity,location,issue,recommendation}]}."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字再审阅。")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    result = _run_tool(
        anthropic_api_key,
        model,
        max_tokens=8000,
        system=_DOCREVIEW_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"论文类型：{type_label}\n\n全文（含脚注，若有）：\n\n{text}",
        tool=_DOCREVIEW_TOOL,
        fail_msg="审阅失败",
    )
    return {"summary": result.get("summary") or "", "findings": _as_list(result.get("findings"))}


# ── 深度改进管线（原型）：计划 → 分块带全局上下文改写 → 拼接 ──────────────

_DEPTH = {
    "light": "深度：轻润色——清晰度、语法、术语统一、删冗余，结构与内容基本不动。",
    "medium": "深度：中度——上面 + 调整段落组织、补过渡、重写表达薄弱处。",
    "deep": "深度：深度——上面 + 写作层结构性重排（合并/拆分段落、强化论证组织），但绝不编造内容。",
}


def _chunk_text(text: str, max_chars: int = 4200) -> List[str]:
    """Greedy split by blank-line paragraphs into chunks <= max_chars (keeps
    paragraph boundaries so revision context stays coherent)."""
    paras = [p for p in text.split("\n\n")]
    chunks: List[str] = []
    cur = ""
    for p in paras:
        if cur and len(cur) + len(p) + 2 > max_chars:
            chunks.append(cur.strip())
            cur = p
        else:
            cur = f"{cur}\n\n{p}" if cur else p
    if cur.strip():
        chunks.append(cur.strip())
    return chunks or [text]


_PLAN_TOOL = {
    "name": "report_plan",
    "description": "A document-level revision plan (NOT a rewrite).",
    "input_schema": {
        "type": "object",
        "properties": {
            "goals": {"type": "array", "items": {"type": "string"}, "description": "3–5 条总体改写目标"},
            "terminology": {"type": "array", "items": {"type": "string"}, "description": "术语统一决定，如『人工智能 → AI』"},
            "footnotes": {"type": "array", "items": {"type": "string"}, "description": "脚注处理，如『删除脚注4（与1重复）』；没有就空数组"},
            "cautions": {"type": "array", "items": {"type": "string"}, "description": "红线/必须保留项（作者观点、语气、数据、不编造）"},
        },
        "required": ["goals", "terminology", "footnotes", "cautions"],
    },
}

_PLAN_SYSTEM = """你是资深学术编辑。通读整篇{type}，产出一份**改写计划**（只规划，绝不改写正文）：
- goals：总体改写目标 3–5 条。
- terminology：全文术语/缩写统一决定（如『人工智能 → AI』）。
- footnotes：脚注的处理（删除重复、合并）；没有就空数组。
- cautions：红线——必须保留作者的观点、论据、数据与语气，绝不编造内容。
{depth}
{lang}
{fmt}
只通过 report_plan 返回。"""


def make_plan(text: str, paper_type: str, output_lang: str, depth: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字。")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    r = _run_tool(
        anthropic_api_key, model, max_tokens=2000,
        system=_PLAN_SYSTEM.format(type=type_label, depth=_DEPTH.get(depth, _DEPTH["medium"]), lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"全文：\n\n{text}", tool=_PLAN_TOOL, fail_msg="出计划失败",
    )
    return {k: _as_list(r.get(k)) for k in ("goals", "terminology", "footnotes", "cautions")}


_CHUNK_TOOL = {
    "name": "report_chunk_revision",
    "description": "Revised text of this chunk + what changed in it.",
    "input_schema": {
        "type": "object",
        "properties": {
            "revised": {"type": "string", "description": "本块改后正文"},
            "changes": {"type": "array", "items": {"type": "string"}, "description": "本块改动要点（0–4 条）"},
        },
        "required": ["revised", "changes"],
    },
}

_CHUNK_SYSTEM = """你在分块改写一篇{type}的第 {i}/{n} 块。严格遵循下面的【改写计划】（尤其术语统一与红线），保证与全文一致。
只改写作层面，保留作者实质内容与语气，绝不编造。正文语言与原文一致。
{depth}

【改写计划】
{plan}

{lang}
{fmt}
只通过 report_chunk_revision 返回本块结果。"""


def _plan_str(plan: Dict[str, Any]) -> str:
    def block(label: str, items: List[Any]) -> str:
        return f"{label}：" + ("；".join(str(x) for x in items) if items else "（无）")
    return "\n".join([
        block("总体目标", plan.get("goals", [])),
        block("术语统一", plan.get("terminology", [])),
        block("脚注处理", plan.get("footnotes", [])),
        block("红线", plan.get("cautions", [])),
    ])


def polish(text: str, paper_type: str, output_lang: str, depth: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Prototype deep-improve pipeline: plan → chunk → revise each chunk with the
    global plan injected → stitch. Returns {plan, revised, changes, chunk_count}."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字。")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    plan = make_plan(text, paper_type, output_lang, depth, anthropic_api_key, model)
    plan_text = _plan_str(plan)
    chunks = _chunk_text(text)
    parts: List[str] = []
    changes: List[str] = []
    for i, ch in enumerate(chunks, 1):
        r = _run_tool(
            anthropic_api_key, model, max_tokens=8000,
            system=_CHUNK_SYSTEM.format(type=type_label, i=i, n=len(chunks), depth=_DEPTH.get(depth, _DEPTH["medium"]), plan=plan_text, lang=_lang_instr(output_lang), fmt=_FMT),
            user=f"本块（第 {i}/{len(chunks)} 块）原文：\n\n{ch}", tool=_CHUNK_TOOL, fail_msg="改写失败",
        )
        rev = _maybe_json(r.get("revised"))
        parts.append(rev if isinstance(rev, str) and rev.strip() else ch)
        changes += [f"[第{i}块] {c}" for c in _as_list(r.get("changes"))]
    return {"plan": plan, "revised": "\n\n".join(parts), "changes": changes, "chunk_count": len(chunks)}


# ── 补丁式改进：读全文 → 只输出 find/replace 编辑 → 程序化套用 ──────────────
# 不重写整篇：输出只含改动的句子，省 5–10× token，一次调用，无长度上限，自动套用。

import re as _re

_PATCH_TOOL = {
    "name": "report_patch",
    "description": "Precise find/replace edits to apply to the paper (NOT a rewrite).",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "一句话总体说明（改了哪些方面、共多少处）"},
            "edits": {
                "type": "array",
                "description": "逐条精确编辑",
                "items": {
                    "type": "object",
                    "properties": {
                        "find": {"type": "string", "description": "从原文逐字照抄的一小段（通常一句或一短语），必须能精确定位"},
                        "replace": {"type": "string", "description": "改后文本"},
                        "reason": {"type": "string", "description": "为什么这样改"},
                        "replace_all": {"type": "boolean", "description": "是否替换全文所有出现（仅术语统一这类用 true，默认 false）"},
                    },
                    "required": ["find", "replace", "reason"],
                },
            },
            "notes": {"type": "array", "items": {"type": "string"}, "description": "无法用 find/replace 自动完成、需作者手动处理的（脚注重排、跨段结构调整等）"},
        },
        "required": ["summary", "edits", "notes"],
    },
}

_PATCH_SYSTEM = """你是资深学术编辑。通读整篇{type}，**不重写全文**，只产出一份**精确编辑清单**：
- edits：每条 = find（从原文**逐字照抄**的一小段，通常一句或一短语）+ replace（改后文本）+ reason（为什么）。只改写作层面：清晰度、语法、术语统一、删冗余、用词。
- 全文统一术语（如「人工智能」→「AI」）的那条，把 replace_all 设为 true。
- **find 必须能在原文中精确定位**：逐字复制（含标点），不要先改写再当 find，否则无法套用。每条 find 尽量唯一。
- notes：无法靠 find/replace 自动完成的（脚注去重/重排、跨段结构调整），写成给作者的建议。
- 绝不编造内容，保留作者的观点、论据、数据与语气。
{depth}
{lang}
{fmt}
只通过 report_patch 返回。"""


def _apply_edit(text: str, find: str, replace: str, replace_all: bool) -> Tuple[str, bool]:
    """Apply one find→replace. Exact first, then whitespace-tolerant. Returns
    (new_text, applied?)."""
    if find in text:
        return (text.replace(find, replace) if replace_all else text.replace(find, replace, 1)), True
    # whitespace-tolerant (handles minor spacing differences; CJK has no spaces so this
    # degrades to an exact escape match)
    pattern = _re.compile(r"\s+".join(_re.escape(tok) for tok in find.split()))
    if pattern.search(text):
        return pattern.sub(lambda _m: replace, text, count=0 if replace_all else 1), True
    return text, False


def patch(text: str, paper_type: str, output_lang: str, depth: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Patch-style improve: model returns precise find/replace edits over the WHOLE
    doc (input ≤60k, output only the changes), applied programmatically. Returns
    {patched, summary, applied, unapplied, notes}."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字。")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    result = _run_tool(
        anthropic_api_key, model, max_tokens=8000,
        system=_PATCH_SYSTEM.format(type=type_label, depth=_DEPTH.get(depth, _DEPTH["medium"]), lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"全文：\n\n{text}", tool=_PATCH_TOOL, fail_msg="改进失败",
    )
    working, applied, unapplied = _apply_edits(text, _as_list(result.get("edits")))
    return {
        "patched": working,
        "summary": result.get("summary") or "",
        "applied": applied,
        "unapplied": unapplied,
        "notes": _as_list(result.get("notes")),
    }


def _apply_edits(text: str, raw_edits: List[Any]) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Apply a list of find/replace edit dicts to text. Specific (first-occurrence)
    edits run before global term sweeps to reduce conflicts. Returns
    (patched_text, applied[], unapplied[])."""
    edits = [e for e in raw_edits if isinstance(e, dict) and str(e.get("find", "")).strip()]
    edits.sort(key=lambda e: _as_bool(e.get("replace_all")))
    working = text
    applied: List[Dict[str, Any]] = []
    unapplied: List[Dict[str, Any]] = []
    for e in edits:
        find = str(e.get("find", ""))
        replace = str(e.get("replace", ""))
        working, ok = _apply_edit(working, find, replace, _as_bool(e.get("replace_all")))
        rec = {"find": find, "replace": replace, "reason": str(e.get("reason", ""))}
        (applied if ok else unapplied).append(rec)
    return working, applied, unapplied


# ── 深挖实质（Socratic）：就实质层薄弱处提问 → 作者补真材料 → 融入论文 ─────────
# 实质层（严谨性/原创与贡献）AI 改不了——它不能替作者编造数据/证据/观点。
# 所以改成苏格拉底式：AI 提针对性问题，作者补真东西，AI 再据实融入（绝不编造）。

_PROBE_TOOL = {
    "name": "report_probes",
    "description": "Targeted probe questions on the paper's substance-layer weaknesses.",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "description": "3–5 个针对实质层薄弱处的问题",
                "items": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "文中位置：章节、或一小段引用片段，便于作者对照"},
                        "weakness": {"type": "string", "description": "这里实质上弱在哪（如：结论缺乏数据支撑、声称过强、没有对照、贡献点不清）"},
                        "question": {"type": "string", "description": "向作者提出的具体问题，引导他拿出 AI 无法编造的真材料（数据/出处/对照/机制/反驳的回应）"},
                    },
                    "required": ["location", "weakness", "question"],
                },
            },
        },
        "required": ["questions"],
    },
}

_PROBE_SYSTEM = """你是一位严格、就事论事的学术导师。通读整篇{type}，只针对**实质层**（严谨性、原创与贡献）的薄弱处，向作者提 3–5 个**有针对性**的问题。
目的：实质问题 AI 不能替作者解决（不能编造数据、证据、出处、新观点），只能引导作者补充真材料。
规则：
- 每个问题绑定文中**具体位置**，指出实质上弱在哪（结论无数据支撑 / 声称过强 / 缺对照或反例 / 方法不足以支撑结论 / 贡献点不清或不新）。
- 问题要**具体到能让作者拿出真东西**（具体的数据、文献出处、对照组、机制解释、对反驳的回应），不要泛泛问「能否再深入」。
- **不要**问写作层（表达、结构、用词）的问题——那些另有工具处理。
- 按重要性排序，最多 5 个，宁缺勿凑。
- {lang}
{fmt}
只通过 report_probes 返回。"""


def probe(text: str, paper_type: str, output_lang: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Generate targeted probe questions on substance-layer weaknesses. Returns
    {questions:[{location, weakness, question}]}."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字。")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    result = _run_tool(
        anthropic_api_key, model, max_tokens=4000,
        system=_PROBE_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"全文：\n\n{text}", tool=_PROBE_TOOL, fail_msg="提问失败",
    )
    raw_qs = _as_list(result.get("questions"))
    questions: List[Dict[str, Any]] = []
    for q in raw_qs:
        q = _maybe_json(q)  # the model sometimes returns each item as a JSON string
        if isinstance(q, dict) and str(q.get("question", "")).strip():
            questions.append({
                "location": str(q.get("location", "")),
                "weakness": str(q.get("weakness", "")),
                "question": str(q.get("question", "")),
            })
    if not questions:
        # Enrich so a prod-only failure is diagnosable without server logs.
        keys = list(result.keys()) if isinstance(result, dict) else type(result).__name__
        sample = repr(raw_qs[:1])[:200]
        raise ValueError(f"提问失败：未解析到问题（keys={keys}, n={len(raw_qs)}, sample={sample}）")
    return {"questions": questions}


_STANCES = {
    "evidence": "作者提供了真实材料（据此补强论文相应处）",
    "speculation": "作者声明这只是推测（不可当事实写——改为恰当的限定/弱化表述，如『可能』『初步』『有待验证』，或明确标注为假设）",
    "skip": "作者暂时跳过（不要改动论文，可在 notes 里提醒此处仍待补充）",
}

_INTEGRATE_SYSTEM = """你是资深学术编辑。作者针对论文实质层薄弱处的若干问题给出了回答。把这些回答**据实融入论文**，用补丁式 find/replace 编辑（不重写全文）。
对每条问答按作者立场处理：
- evidence（提供了真材料）：据此补强论文相应处——补上数据/出处/对照/机制等，让论证更扎实。
- speculation（只是推测）：**不可当事实写**，改为恰当的限定或弱化表述，或明确标注为假设/待验证。
- skip（暂时跳过）：不改动论文，在 notes 里提醒此处仍待补充。
铁律：
- **绝不编造**作者没有提供的事实、数据、引用、实验结果。作者没给的就不要凭空写进去。
- find 必须从原文**逐字照抄**、能精确定位；只动与回答相关的句段，保留作者其余内容与语气。
- 无法靠 find/replace 自动完成的（需新增整段、重排结构），写进 notes 给作者。
{lang}
{fmt}
只通过 report_patch 返回 {{summary, edits, notes}}。"""


def integrate(text: str, answers: List[Dict[str, Any]], paper_type: str, output_lang: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Weave the author's answers (to probe questions) into the paper as find/replace
    edits, honoring each answer's stance (evidence/speculation/skip). Never fabricates.
    Returns the same shape as patch(): {patched, summary, applied, unapplied, notes}."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字。")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    # Keep only answered items (a skipped item with no answer still conveys "leave it").
    items = []
    for a in answers or []:
        if not isinstance(a, dict):
            continue
        stance = str(a.get("stance", "")).strip().lower()
        if stance not in _STANCES:
            stance = "evidence"
        question = str(a.get("question", "")).strip()
        answer = str(a.get("answer", "")).strip()
        if not question:
            continue
        if stance != "skip" and not answer:
            continue  # nothing to integrate
        items.append({"stance": stance, "question": question, "answer": answer})
    if not items:
        raise ValueError("没有可融入的回答——请先回答问题并填写内容。")

    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    qa_block = "\n\n".join(
        f"问题 {i + 1}：{it['question']}\n作者立场：{_STANCES[it['stance']]}\n作者回答：{it['answer'] or '（无）'}"
        for i, it in enumerate(items)
    )
    result = _run_tool(
        anthropic_api_key, model, max_tokens=8000,
        system=_INTEGRATE_SYSTEM.format(lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"论文类型：{type_label}\n\n论文全文：\n\n{text}\n\n———\n\n作者的问答：\n\n{qa_block}",
        tool=_PATCH_TOOL, fail_msg="融入失败",
    )
    working, applied, unapplied = _apply_edits(text, _as_list(result.get("edits")))
    return {
        "patched": working,
        "summary": result.get("summary") or "",
        "applied": applied,
        "unapplied": unapplied,
        "notes": _as_list(result.get("notes")),
    }


# ── 按指示改写：作者下明确指令 → patch 式改（改的是传入文本=当前工作稿）─────────

_INSTRUCT_SYSTEM = """你是资深学术编辑。按作者的**明确指示**修改这篇{type}，用补丁式 find/replace 编辑（不重写全文）。
- 只做指示要求的改动：压缩 / 扩展、改语气与语域、重组段落、替换措辞、删减、统一称谓等，都照做。
- find 必须从原文**逐字照抄**、能精确定位；只动与指示相关的部分，保留其余内容与作者语气。
- 全文统一替换类（如改称谓、统一术语）把 replace_all 设为 true。
- **绝不编造**作者没有提供的事实、数据、引用、实验结果或新观点。指示若需要新的真材料（如「补一段关于 X 的文献综述」「加一个对照实验」），不要凭空生成——文字层面能做的先做，需要真材料的写进 notes 提醒作者补充。
- 指示无法用 find/replace 自动完成的（需新增整段、跨结构重排），写进 notes。
{lang}
{fmt}
只通过 report_patch 返回 {{summary, edits, notes}}。"""


def instruct(text: str, instruction: str, paper_type: str, output_lang: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Modify the paper per the author's explicit instruction, as patch-style edits
    over the passed-in text (= the caller's current worktop draft). Never fabricates.
    Returns the same shape as patch(): {patched, summary, applied, unapplied, notes}."""
    text = (text or "").strip()
    instruction = (instruction or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字。")
    if not instruction:
        raise ValueError("请先写下你想怎么改。")
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]
    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])
    result = _run_tool(
        anthropic_api_key, model, max_tokens=8000,
        system=_INSTRUCT_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang), fmt=_FMT),
        user=f"作者的修改指示：\n\n{instruction}\n\n———\n\n论文全文：\n\n{text}",
        tool=_PATCH_TOOL, fail_msg="按指示修改失败",
    )
    working, applied, unapplied = _apply_edits(text, _as_list(result.get("edits")))
    return {
        "patched": working,
        "summary": result.get("summary") or "",
        "applied": applied,
        "unapplied": unapplied,
        "notes": _as_list(result.get("notes")),
    }
