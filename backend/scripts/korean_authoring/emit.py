"""Render a region dict as review-ready Python to paste into content.py. Uses pprint
(Python-3 repr keeps printable Korean as-is and preserves dict insertion order)."""
from __future__ import annotations

import pprint


def render_region_python(region: dict) -> str:
    body = pprint.pformat(region, sort_dicts=False, width=88)
    return f"REGION = {body}\n"
