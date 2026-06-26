"""Region briefs — the curatorial input that steers generation. Author one per region
(3-9); the generator fills natural dialogue/drills around this fixed vocab/grammar."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RegionBrief:
    slug: str
    title: str
    theme: str
    order_index: int
    setting: str
    situations: list[str]
    target_vocab: list[dict]          # [{"ko","en","romaji"}, ...]
    target_grammar: list[str]
    boss_persona: str                 # must be a key in app.services.korean.personas.PERSONAS
    boss_goal_en: str
    counts: dict = field(default_factory=lambda: {"scenes": 3, "drills": 3, "boss": 1})


BRIEFS: dict[str, RegionBrief] = {
    "getting-around": RegionBrief(
        slug="getting-around",
        title="Getting Around",
        theme="transit",
        order_index=3,
        setting="A traveler navigating Seoul's subway and buses.",
        situations=[
            "buy a T-money transit card at a convenience store",
            "ask which subway line and direction to take",
            "confirm where to get off the bus",
        ],
        target_vocab=[
            {"ko": "지하철", "en": "subway", "romaji": "jihacheol"},
            {"ko": "버스", "en": "bus", "romaji": "beoseu"},
            {"ko": "역", "en": "station", "romaji": "yeok"},
            {"ko": "어디", "en": "where", "romaji": "eodi"},
            {"ko": "내려요", "en": "get off", "romaji": "naeryeoyo"},
            {"ko": "티머니", "en": "T-money card", "romaji": "timeoni"},
        ],
        target_grammar=["~까지 (to/until a place)", "어디 + 에서/에 (where at/to)"],
        boss_persona="transit_staff",
        boss_goal_en="Get directions to the right subway line and ride one stop",
    ),
}


def get_brief(slug: str) -> RegionBrief:
    return BRIEFS[slug]
