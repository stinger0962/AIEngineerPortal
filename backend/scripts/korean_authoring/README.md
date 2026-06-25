# Korean course authoring pipeline

Offline tool to draft a course region with Claude, validate it, and emit Python for
`app/services/korean/content.py`. Never touches the running app.

## Usage (run from `backend/`)
    python -m scripts.korean_authoring.cli <region-slug>            # generate (needs ANTHROPIC_API_KEY)
    python -m scripts.korean_authoring.cli <region-slug> --no-review
    python -m scripts.korean_authoring.cli <region-slug> --dry-run  # use canned fixture, no API

Output: `scripts/korean_authoring/out/<slug>.py` (gitignored). Review it + the printed
reviewer notes, fix anything, then paste the `REGION` dict into the `REGIONS` list in
`app/services/korean/content.py`, commit, and deploy via the normal pipeline.

## Add a region
1. Add a `RegionBrief` to `briefs.py` (slug, title, theme, order_index, vocab, grammar, boss).
2. If the boss needs a new persona, add it to `app/services/korean/personas.py`.
3. Run the CLI, review, paste into `content.py`.

## Pieces
- `briefs.py` — `RegionBrief` + the per-region briefs (the curatorial input).
- `prompt.py` — generation + review prompts, with a few-shot example pulled from live regions 0-2.
- `generate.py` — Claude call + JSON extraction + coercion (slug-prefix, renumber, default audio_keys) + retry.
- `lint.py` — `validate_region` (reuses the live `validate_node_content` + author checks; drills are tap-only).
- `review.py` — advisory second-pass critique (never fails the run).
- `emit.py` — render the region as round-trip-safe Python.
- `cli.py` — wire it together; `--dry-run` uses `fixtures/canned_<slug>.json`.
