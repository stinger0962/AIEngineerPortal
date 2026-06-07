"""Summary generation via Claude — strict structured-JSON output."""
from __future__ import annotations

import json
import re
from typing import Dict

_MAX_INPUT_CHARS = 20000  # cap input to keep token cost bounded

_SUMMARY_PROMPT = """你是一位专业的中文内容编辑。请阅读以下内容，输出一份结构化中文摘要。

请根据内容类型，自行决定最合适的分节方式。例如：
- 新闻/资讯 → 背景、关键事实、影响
- 教程/方法 → 核心要点、操作步骤、行动建议
- 观点/评论 → 主要论点、支撑论据、结论
- 访谈/对话 → 核心话题、精彩观点、金句
请自由选择 2-4 个最贴合内容的小节。

严格按以下 JSON 格式输出，不要任何额外文字、说明或前言：
{{
  "title": "简洁标题（不超过20字）",
  "tldr": "一句话总结核心内容",
  "sections": [
    {{"heading": "小节标题", "points": ["要点1", "要点2"]}},
    {{"heading": "小节标题", "points": ["要点1", "要点2"]}}
  ]
}}

要求：
- sections 2-4 个，每节 2-6 条要点
- 标题与要点全部使用中文，简洁清晰

内容：
{content}"""


def _extract_json(raw: str) -> dict:
    """Pull a JSON object out of Claude's response, tolerating code fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in summary response")
    return json.loads(raw[start : end + 1])


def generate_summary(text: str, anthropic_api_key: str, model: str) -> Dict:
    """Return {title, tldr, sections[]} (all Chinese).

    Raises ValueError if the model output cannot be parsed or is missing required fields.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = _SUMMARY_PROMPT.format(content=text[:_MAX_INPUT_CHARS])
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text

    try:
        data = _extract_json(raw)
    except Exception as exc:
        raise ValueError(f"Could not parse summary: {exc}") from exc

    tldr = data.get("tldr")
    if not isinstance(tldr, str) or not tldr.strip():
        raise ValueError("Summary missing tldr")

    raw_sections = data.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise ValueError("Summary missing sections")

    sections = []
    for sec in raw_sections:
        if not isinstance(sec, dict):
            continue
        heading = str(sec.get("heading") or "").strip()
        pts = sec.get("points") or []
        if not isinstance(pts, list):
            continue
        points = [str(p).strip() for p in pts if str(p).strip()]
        if heading and points:
            sections.append({"heading": heading, "points": points})

    if not sections:
        raise ValueError("Summary has no valid sections")

    return {
        "title": (data.get("title") or "").strip(),
        "tldr": tldr.strip(),
        "sections": sections,
    }
