"""CLI: python -m scripts.korean_authoring.cli <slug> [--no-review] [--dry-run] [--model ID]
Flow: brief -> generate (or canned fixture) -> lint -> [review] -> emit out/<slug>.py."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .briefs import get_brief
from .generate import coerce_region, generate_region
from .lint import validate_region
from .emit import render_region_python
from .review import review_region

_HERE = Path(__file__).resolve().parent


def _load_fixture(slug: str) -> dict:
    return json.loads((_HERE / "fixtures" / f"canned_{slug}.json").read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="korean_authoring")
    parser.add_argument("slug")
    parser.add_argument("--no-review", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="claude-opus-4-8")
    args = parser.parse_args(argv)

    try:
        brief = get_brief(args.slug)
    except KeyError:
        print(f"unknown region slug: {args.slug!r}", file=sys.stderr)
        return 2

    client = None
    if args.dry_run:
        region = coerce_region(brief, _load_fixture(args.slug)["nodes"])
    else:
        from app.services.ai_service import AIService

        svc = AIService(model=args.model)
        if not svc.is_available:
            print("No Anthropic API key configured. Use --dry-run or set ANTHROPIC_API_KEY.", file=sys.stderr)
            return 2
        client = svc.client
        region = generate_region(brief, client, svc.model)

    issues = validate_region(region)
    if issues:
        print("LINT FAILED:")
        for i in issues:
            print(f"  - {i}")
        return 1

    notes: list[dict] = []
    if not args.dry_run and not args.no_review and client is not None:
        notes = review_region(brief, region, client, args.model)

    out_dir = _HERE / "out"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{args.slug}.py"
    out_path.write_text(render_region_python(region), encoding="utf-8")

    print(f"emitted {out_path}")
    for n in notes:
        print(f"review[{n.get('severity', '?')}] {n.get('node', '?')}: {n.get('note', '')}")
    print("Review the file, fix anything, then paste REGION into app/services/korean/content.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
