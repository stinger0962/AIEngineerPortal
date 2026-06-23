"""Authored Korean course content (regions 0-2) + per-kind content_json validation."""
from __future__ import annotations

from typing import Any

_REQUIRED_FIELDS: dict[str, set[str]] = {
    "reading": {"letters", "blocks", "words"},
    "scene": {"setting", "character", "lines", "your_turns", "new_vocab"},
    "drill": {"items"},
    "boss": {"goal_en", "persona", "level", "allowed_vocab", "success_criteria", "max_turns"},
}

VALID_KINDS = set(_REQUIRED_FIELDS)


def validate_node_content(kind: str, content: dict[str, Any]) -> None:
    if kind not in _REQUIRED_FIELDS:
        raise ValueError(f"unknown node kind: {kind!r}")
    missing = _REQUIRED_FIELDS[kind] - set(content or {})
    if missing:
        raise ValueError(f"{kind} node missing fields: {sorted(missing)}")
    if kind == "drill":
        for item in content["items"]:
            if item.get("type") not in {"match", "listen", "fill", "type"}:
                raise ValueError(f"drill item has invalid type: {item.get('type')!r}")


REGIONS: list[dict[str, Any]] = []  # populated in a later task (B2)
