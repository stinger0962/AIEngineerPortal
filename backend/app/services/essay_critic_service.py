"""评审 Critique: structured per-dimension paper/essay evaluation via Claude,
plus text extraction from uploaded .docx / .pdf / .md / .txt files.

Design note: the per-dimension scores are a DIAGNOSTIC dashboard, not a single
composite number to be maximized — the actionable critique is what drives real
improvement. (See the project discussion on reward-hacking an LLM judge.)
"""
from __future__ import annotations

import io
from typing import Any, Dict

_MIN_CHARS = 200
_MAX_CHARS = 60000  # cap input to keep token cost / latency sane (~ a long paper)

PAPER_TYPES = {
    "research": "学术 / 研究论文",
    "argument": "议论文 / Essay",
    "statement": "个人陈述 / 申请文书",
}


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
- 用论文本身的主要语言书写全部评语（英文论文 → 英文评语）。
只通过 report_evaluation 工具返回结构化结果，不要输出其它文字。"""


def evaluate(text: str, paper_type: str, anthropic_api_key: str, model: str) -> Dict[str, Any]:
    """Run the rubric evaluation. Returns {overall, dimensions}. Raises ValueError
    on bad input / API failure."""
    text = (text or "").strip()
    if len(text) < _MIN_CHARS:
        raise ValueError(f"正文太短，至少贴入约 {_MIN_CHARS} 字再评估。")
    truncated = len(text) > _MAX_CHARS
    if truncated:
        text = text[:_MAX_CHARS]

    type_label = PAPER_TYPES.get(paper_type, PAPER_TYPES["research"])

    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    note = "\n\n（注：正文过长，仅评估前约 6 万字。）" if truncated else ""
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=3000,
            system=_SYSTEM.format(type=type_label),
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "report_evaluation"},
            messages=[{"role": "user", "content": f"论文类型：{type_label}{note}\n\n论文正文：\n\n{text}"}],
        )
    except Exception as exc:
        raise ValueError(f"评估失败：{exc}") from exc

    for block in msg.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "report_evaluation":
            result = block.input
            if isinstance(result, dict) and "overall" in result and "dimensions" in result:
                return result
    raise ValueError("评估失败：模型未返回结构化结果，请重试。")
