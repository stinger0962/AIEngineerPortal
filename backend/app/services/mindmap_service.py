"""Mind map generation via Claude — hierarchical Markdown outline for markmap."""
from __future__ import annotations

import re
from typing import Dict

_MAX_INPUT_CHARS = 20000

_MINDMAP_PROMPT = """你是一位专业的中文知识整理专家。请阅读以下内容，输出一份用于绘制思维导图的 Markdown 大纲。

要求：
1. 用 Markdown 标题层级表示结构：
   - 一个 `#` 一级标题作为中心主题（整张图的根节点）
   - 4-7 个 `##` 二级标题作为主要分支
   - `###` 三级标题作为子分支（按需）
   - `-` 列表项作为最末端的要点
2. 整体 3-4 层，结构清晰，覆盖核心内容
3. 节点文字简洁（短语或关键词，不要整句），全部使用中文
4. 直接输出 Markdown，不要代码块标记、不要任何解释或前言

内容：
{content}"""


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw).strip()
    return raw


def generate_mindmap(text: str, anthropic_api_key: str, model: str) -> Dict:
    """Return {"title": str, "markdown": str} — a hierarchical Markdown outline.

    Raises ValueError if the output lacks a usable structure (a single `#` root and
    at least two `##` branches).
    """
    import anthropic

    client = anthropic.Anthropic(api_key=anthropic_api_key)
    prompt = _MINDMAP_PROMPT.format(content=text[:_MAX_INPUT_CHARS])
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    md = _strip_fences(message.content[0].text)

    lines = md.splitlines()
    roots = [ln for ln in lines if ln.strip().startswith("# ")]
    branches = [ln for ln in lines if ln.strip().startswith("## ")]
    if not roots or len(branches) < 2:
        raise ValueError("Mind map has no usable structure")

    title = roots[0].strip().lstrip("#").strip() or "思维导图"
    return {"title": title, "markdown": md}
