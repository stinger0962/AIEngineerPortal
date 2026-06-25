"""Call Claude to draft a region, then coerce the raw nodes into a content.py-shaped
region dict (prefix slugs, renumber order_index, default scene audio_keys)."""
from __future__ import annotations

import json
import re
from typing import Any

from .briefs import RegionBrief
from .prompt import build_generation_prompt, few_shot_example


def extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in model output")
    return json.loads(t[start:end + 1])


def coerce_region(brief: RegionBrief, nodes: list[dict]) -> dict:
    out: list[dict] = []
    for i, n in enumerate(nodes):
        slug = n.get("slug", "") or f"node{i}"
        if not slug.startswith(brief.slug + "-"):
            slug = f"{brief.slug}-{slug}"
        cj: dict[str, Any] = n.get("content_json", {})
        if n.get("kind") == "scene":
            for k, line in enumerate(cj.get("lines", [])):
                line.setdefault("audio_key", f"{slug}_{k}")
        out.append({
            "slug": slug,
            "kind": n.get("kind", ""),
            "title": n.get("title", ""),
            "order_index": i,
            "content_json": cj,
        })
    return {
        "slug": brief.slug,
        "title": brief.title,
        "theme": brief.theme,
        "order_index": brief.order_index,
        "nodes": out,
    }


def generate_region(brief: RegionBrief, client: Any, model: str, max_retries: int = 2) -> dict:
    system, user = build_generation_prompt(brief, few_shot_example())
    messages: list[dict] = [{"role": "user", "content": user}]
    last = ""
    for _ in range(max_retries + 1):
        resp = client.messages.create(model=model, max_tokens=4096, system=system, messages=messages)
        last = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        try:
            data = extract_json(last)
            return coerce_region(brief, data["nodes"])
        except (ValueError, KeyError, json.JSONDecodeError):
            messages = [
                {"role": "user", "content": user},
                {"role": "assistant", "content": last},
                {"role": "user", "content": "Return ONLY the JSON object with a top-level 'nodes' array. No prose, no code fences."},
            ]
    raise ValueError(f"could not parse generation after {max_retries + 1} attempts; last output:\n{last[:500]}")
