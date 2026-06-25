"""Build the Claude prompts: a generation prompt (brief + few-shot of real content) and
a reviewer prompt (critique the draft). The few-shot is pulled from live regions 0-2 so
the model matches the established style/format exactly."""
from __future__ import annotations

import json

from app.services.korean.content import REGIONS
from .briefs import RegionBrief

_SCHEMAS = """Node content_json shapes (return EXACTLY these keys):
- reading: {"letters":[{"jamo","sound","audio_key"}], "blocks":[{"ko","romaji"}], "words":[{"ko","en"}]}
- scene: {"setting","character","lines":[{"speaker","ko","romaji","en","audio_key"}],
    "your_turns":[{"prompt_en","options":[str...],"accepted":[{"ko","intents":[str...]}]}],
    "new_vocab":[{"ko","en","romaji"}]}
- drill: {"items":[ ... ]} where each item is TAP-ONLY, one of:
    {"type":"match","ko","answer","choices":[...]}  (choices are English meanings incl. answer)
    {"type":"listen","audio_key","answer","choices":[...]}  (choices are Korean words incl. answer)
- boss: {"goal_en","persona","level","allowed_vocab":[...],"success_criteria","max_turns"}"""


def few_shot_example() -> str:
    """One real node of each kind from live regions 0-2, as a style exemplar."""
    picked: dict[str, dict] = {}
    for r in REGIONS:
        for n in r["nodes"]:
            picked.setdefault(n["kind"], n)
    ordered = [picked[k] for k in ("reading", "scene", "drill", "boss") if k in picked]
    return json.dumps({"nodes": ordered}, ensure_ascii=False, indent=2)


def build_generation_prompt(brief: RegionBrief, few_shot: str) -> tuple[str, str]:
    system = (
        "You are an expert author of beginner Korean course content for absolute beginners "
        "(speak/listen/READ only — NO writing). Produce natural, correct, situational Korean "
        "with accurate Revised Romanization and English glosses.\n\n"
        f"{_SCHEMAS}\n\n"
        "HARD RULES:\n"
        "- Drills are TAP-ONLY: every drill item type is 'match' or 'listen'. Never 'fill'/'type'.\n"
        "- Every drill item's choices MUST include its answer.\n"
        "- Every scene line has ko, romaji, en, audio_key. Each scene has non-empty new_vocab.\n"
        "- The boss uses the given persona and goal; allowed_vocab is drawn from the region vocab.\n"
        "- Return ONLY a JSON object: {\"nodes\":[{slug,kind,title,order_index,content_json}, ...]}.\n"
        "- Interleave scenes and drills (scene, its drill, scene, its drill, ...) then the boss last.\n\n"
        "STYLE EXEMPLAR (real content — match this shape and tone):\n" + few_shot
    )
    vocab = "\n".join(f"- {v['ko']} ({v['romaji']}) = {v['en']}" for v in brief.target_vocab)
    sit = "\n".join(f"- {s}" for s in brief.situations)
    user = (
        f"Author region '{brief.slug}' — {brief.title} (theme: {brief.theme}).\n"
        f"Setting: {brief.setting}\n"
        f"Produce exactly {brief.counts['scenes']} scenes + {brief.counts['drills']} drills "
        f"+ {brief.counts['boss']} boss.\n\n"
        f"Scene situations:\n{sit}\n\n"
        f"Target vocabulary (build the content around these):\n{vocab}\n\n"
        f"Target grammar: {', '.join(brief.target_grammar)}\n\n"
        f"Boss: persona='{brief.boss_persona}', goal='{brief.boss_goal_en}'.\n"
        f"Slug-prefix every node with '{brief.slug}-'."
    )
    return system, user


def build_review_prompt(brief: RegionBrief, region: dict) -> tuple[str, str]:
    system = (
        "You are a Korean-language reviewer. Critique the draft course region ONLY for: "
        "naturalness, beginner-level appropriateness, and situational accuracy. "
        "Return ONLY JSON: {\"notes\":[{\"node\":slug,\"severity\":\"low|med|high\",\"note\":str}]}. "
        "Empty notes list means it's good."
    )
    user = (
        f"Region brief: {brief.title} (vocab: {', '.join(v['ko'] for v in brief.target_vocab)}).\n\n"
        f"Draft region JSON:\n{json.dumps(region, ensure_ascii=False, indent=2)}"
    )
    return system, user
