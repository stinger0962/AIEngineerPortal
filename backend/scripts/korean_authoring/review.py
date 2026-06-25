"""Optional second Claude pass: advisory critique of the draft's Korean. Never fails the
pipeline — returns [] if the model output can't be parsed."""
from __future__ import annotations

from typing import Any

from .briefs import RegionBrief
from .generate import extract_json
from .prompt import build_review_prompt


def review_region(brief: RegionBrief, region: dict, client: Any, model: str) -> list[dict]:
    system, user = build_review_prompt(brief, region)
    try:
        resp = client.messages.create(model=model, max_tokens=1500, system=system, messages=[{"role": "user", "content": user}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        return list(extract_json(text).get("notes", []))
    except Exception:
        return []
