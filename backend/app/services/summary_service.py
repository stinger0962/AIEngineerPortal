"""Summary generation via Claude — strict structured-JSON output."""
from __future__ import annotations

import json
import re
from typing import Dict

_MAX_INPUT_CHARS = 20000  # cap input to keep token cost bounded

_SUMMARY_PROMPT = """你是一位专业的中文内容编辑。请阅读以下内容，并输出一份结构化中文摘要。

严格按照以下 JSON 格式输出，不要任何额外文字、说明或前言：
{{
  "title": "简洁标题（不超过20字）",
  "tldr": "一句话总结核心内容",
  "key_points": ["关键要点1", "关键要点2"],
  "takeaways": ["核心收获1", "核心收获2"]
}}

要求：
- key_points 提炼 3-7 条最重要的观点
- takeaways 提炼 2-4 条值得记住或可执行的收获
- 全部使用中文，简洁清晰

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
    """Return {title, tldr, key_points[], takeaways[]} (all Chinese).

    Raises ValueError if the model output cannot be parsed or is missing a tldr.
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

    key_points = data.get("key_points") or []
    takeaways = data.get("takeaways") or []
    if not isinstance(key_points, list) or not isinstance(takeaways, list):
        raise ValueError("Summary key_points/takeaways must be lists")

    return {
        "title": (data.get("title") or "").strip(),
        "tldr": tldr.strip(),
        "key_points": [str(k).strip() for k in key_points if str(k).strip()],
        "takeaways": [str(t).strip() for t in takeaways if str(t).strip()],
    }
