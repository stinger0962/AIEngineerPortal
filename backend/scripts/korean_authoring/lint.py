"""Lint a generated region: reuse the live schema validator + author-quality checks.
Returns a list of human-readable issues (empty = clean). Emit nothing if non-empty."""
from __future__ import annotations

from app.services.korean.content import validate_node_content
from app.services.korean.personas import PERSONAS

_TAP_TYPES = {"match", "listen"}


def validate_region(region: dict) -> list[str]:
    issues: list[str] = []
    nodes = region.get("nodes", [])
    region_slug = region.get("slug", "")

    slugs = [n.get("slug", "") for n in nodes]
    if len(slugs) != len(set(slugs)):
        issues.append("duplicate node slugs")

    for n in nodes:
        slug = n.get("slug", "")
        kind = n.get("kind", "")
        cj = n.get("content_json", {})

        if not (slug == region_slug or slug.startswith(region_slug + "-")):
            issues.append(f"node '{slug}' not prefixed with region slug '{region_slug}'")

        try:
            validate_node_content(kind, cj)
        except ValueError as exc:
            issues.append(f"node '{slug}': {exc}")
            continue

        if kind == "drill":
            for i, item in enumerate(cj["items"]):
                if item.get("type") not in _TAP_TYPES:
                    issues.append(f"node '{slug}' drill item {i}: writing type '{item.get('type')}' (tap-only)")
                elif item.get("answer") not in item.get("choices", []):
                    issues.append(f"node '{slug}' drill item {i}: choices missing answer")
        elif kind == "scene":
            if not cj.get("new_vocab"):
                issues.append(f"node '{slug}' scene: empty new_vocab")
            for j, line in enumerate(cj.get("lines", [])):
                for f_ in ("ko", "romaji", "en"):
                    if not line.get(f_):
                        issues.append(f"node '{slug}' scene line {j}: missing {f_}")
        elif kind == "boss":
            if cj.get("persona") not in PERSONAS:
                issues.append(f"node '{slug}' boss: unknown persona '{cj.get('persona')}'")
            if not cj.get("allowed_vocab"):
                issues.append(f"node '{slug}' boss: empty allowed_vocab")

    orders = [n.get("order_index") for n in nodes]
    if orders != list(range(len(nodes))):
        issues.append(f"order_index not contiguous 0..n: {orders}")

    return issues
