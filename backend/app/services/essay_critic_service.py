"""评审 Critique: structured per-dimension paper/essay evaluation via Claude,
plus text extraction from uploaded .docx / .pdf / .md / .txt files.

Design note: the per-dimension scores are a DIAGNOSTIC dashboard, not a single
composite number to be maximized — the actionable critique is what drives real
improvement. (See the project discussion on reward-hacking an LLM judge.)
"""
from __future__ import annotations

import io
import json
from typing import Any, Dict, List

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


def extract_text(filename: str, raw: bytes) -> str:
    """Extract plain text from an uploaded file. Supports .docx / .pdf / .md / .txt."""
    name = (filename or "").lower()
    if name.endswith(".docx"):
        import docx  # python-docx

        doc = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs).strip()
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
                        "score": {"type": "integer", "description": "1–10 分"},
                        "critique": {"type": "string", "description": "强在哪、弱在哪，引用文中真实问题，不空泛"},
                        "suggestions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "1–3 条具体可执行的修改建议",
                        },
                    },
                    "required": ["label", "score", "critique", "suggestions"],
                },
            },
        },
        "required": ["overall", "dimensions"],
    },
}

_SYSTEM = """你是一位严格、就事论事的学术写作评审，不奉承、不说空话。给定一篇{type}，按 5–6 个维度评估：
论点(Thesis) / 论证与证据(Argument & Evidence) / 结构与连贯(Structure) / 严谨性(Rigor，研究类含方法是否恰当、结论是否被支撑、有无过度声称) / 原创与贡献(Originality) / 行文(Writing)。
按论文类型调整侧重：议论文重说服力与逻辑链；个人陈述重真诚、个人声音与具体性（少讲大道理）。

规则：
- 每个维度给 1–10 分 + **具体**简评（指出文中真实的强点与弱点，可引用片段），再给 1–3 条**可执行**的修改建议（落到具体段落/句子，不要泛泛说"加强论证"）。
- 分数用于诊断，不是取悦作者。宁严勿松，分数要拉开区分度，避免全是 7–8 分。
- overall.top_fix：如果只改一件事，改什么——单点最大杠杆。
- {lang}
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
        system=_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang)),
        user=f"论文类型：{type_label}{note}\n\n论文正文：\n\n{text}",
        tool=_TOOL,
        fail_msg="评估失败",
    )
    # Claude may stringify the nested object/array params — coerce back to structure.
    overall = _maybe_json(result.get("overall"))
    dims = _as_list(result.get("dimensions"))
    if not isinstance(overall, dict) or not dims:
        raise ValueError("评估失败：模型未返回结构化结果，请重试。")
    for d in dims:
        if isinstance(d, dict):
            d["suggestions"] = _as_list(d.get("suggestions"))
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
        system=_REVISE_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang)),
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
        system=_JUDGE_SYSTEM.format(type=type_label, lang=_lang_instr(output_lang)),
        user=f"版本 A（原文）：\n\n{original}\n\n———\n\n版本 B（改后）：\n\n{revised}",
        tool=_JUDGE_TOOL,
        fail_msg="裁决失败",
    )
    return {
        "better": _as_bool(result.get("better")),
        "reason": result.get("reason") or "",
        "dimensions_improved": _as_list(result.get("dimensions_improved")),
    }
