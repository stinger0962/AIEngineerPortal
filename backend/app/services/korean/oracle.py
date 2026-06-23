"""Korean roleplay boss: one Claude call per turn, constrained to the learner's level
and the node's allowed vocabulary. A trailing [[goal_met]] marker signals success."""
from __future__ import annotations

import time
from typing import Any, Optional

from .personas import persona_prompt

_GOAL_MARKER = "[[goal_met]]"


class KoreanOracle:
    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def _system_prompt(self, boss: dict) -> str:
        vocab = "、".join(boss.get("allowed_vocab", []))
        return (
            f"{persona_prompt(boss.get('persona', ''))}\n\n"
            "You are roleplaying with an absolute-beginner Korean learner inside a language game.\n"
            f"The learner's level is: {boss.get('level', 'beginner')}.\n"
            f"Scene goal (in English, for you only): {boss.get('goal_en', '')}.\n"
            f"Success means: {boss.get('success_criteria', '')}.\n\n"
            "RULES:\n"
            "- Reply ONLY in short, simple Korean (1-2 sentences). No English, no romanization.\n"
            f"- Stay within this vocabulary plus tiny obvious additions: {vocab}.\n"
            "- Stay in character; gently steer the learner toward the goal.\n"
            f"- When the learner has clearly achieved the goal, append the literal marker {_GOAL_MARKER} "
            "at the very end of your reply (it is stripped before display)."
        )

    def run(self, boss: dict, messages: list[dict]) -> Optional[dict]:
        start = time.time()
        try:
            response = self.client.messages.create(
                model=self.model, max_tokens=300,
                system=self._system_prompt(boss),
                messages=messages[-12:], timeout=60.0,
            )
        except Exception:
            return None
        text = "".join(
            b.text for b in response.content if getattr(b, "type", None) == "text"
        ).strip()
        if not text:
            return None
        goal_met = _GOAL_MARKER in text
        clean = text.replace(_GOAL_MARKER, "").strip()
        return {
            "response": clean,
            "goal_met": goal_met,
            "_meta": {
                "model": self.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "latency_ms": int((time.time() - start) * 1000),
            },
        }
