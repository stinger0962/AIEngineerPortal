"""Claude API wrapper for AI-powered feedback generation."""
import hashlib
import json
import time
from typing import Any, Dict, List, Optional

import anthropic

from app.core.config import get_settings


class AIService:
    """Thin wrapper around Anthropic Claude API for structured feedback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model or settings.ai_model
        self.daily_budget = settings.ai_daily_token_budget
        self._client: Optional[anthropic.Anthropic] = None

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def cache_key(self, exercise_id: int, code: str) -> str:
        """SHA-256 of exercise_id + code, scoped to prevent cross-exercise collisions."""
        raw = f"{exercise_id}:{code}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _build_grading_prompt(
        self,
        code: str,
        exercise: Dict[str, Any],
        attempts_history: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        system = (
            "You are a senior AI engineer reviewing code from a full-stack engineer "
            "who is learning AI agent patterns. You give specific, actionable feedback "
            "with example code fixes. You encourage retry when the solution needs work. "
            "Always respond with valid JSON matching this schema:\n"
            '{"strengths": ["..."], "issues": ["..."], "suggestions": ["..."], '
            '"example_fixes": "markdown string with code blocks", '
            '"score": 0-100, "should_retry": true/false}\n'
            "Score guide: 85+ solid, 70-84 needs review, <70 retry recommended."
        )

        user_parts = [
            f"## Exercise: {exercise.get('title', '')}",
            f"\n### Problem\n{exercise.get('prompt_md', '')}",
            f"\n### Reference Solution\n```python\n{exercise.get('solution_code', '')}\n```",
            f"\n### Explanation\n{exercise.get('explanation_md', '')}",
            f"\n### Student's Code\n```python\n{code}\n```",
        ]

        if attempts_history:
            recent = attempts_history[-3:]
            history_str = "\n".join(
                f"- Previous attempt (score {a.get('score', '?')}): {a.get('code', '')[:200]}"
                for a in recent
            )
            user_parts.append(f"\n### Previous Attempts\n{history_str}")

        return {"system": system, "user": "\n".join(user_parts)}

    def _parse_grading_response(self, raw: str) -> Dict[str, Any]:
        """Parse Claude's JSON response into structured feedback."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            data = json.loads(cleaned)
            return {
                "strengths": data.get("strengths", []),
                "issues": data.get("issues", []),
                "suggestions": data.get("suggestions", []),
                "example_fixes": data.get("example_fixes", ""),
                "score": int(data.get("score", 0)),
                "should_retry": bool(data.get("should_retry", True)),
            }
        except (json.JSONDecodeError, ValueError):
            return {
                "strengths": [],
                "issues": ["Could not parse AI response. Please try again."],
                "suggestions": [],
                "example_fixes": "",
                "score": 0,
                "should_retry": True,
            }

    def grade_exercise(
        self,
        code: str,
        exercise: Dict[str, Any],
        attempts_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Grade an exercise submission using Claude. Returns structured feedback."""
        prompt = self._build_grading_prompt(code, exercise, attempts_history)
        start = time.time()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=prompt["system"],
                messages=[{"role": "user", "content": prompt["user"]}],
            )
        except anthropic.APITimeoutError:
            return {
                "strengths": [],
                "issues": ["AI grading timed out. Your code was saved — try again shortly."],
                "suggestions": [],
                "example_fixes": "",
                "score": 0,
                "should_retry": True,
                "model": self.model,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": int((time.time() - start) * 1000),
                "prompt_template": prompt["system"],
            }
        except anthropic.APIConnectionError:
            return {
                "strengths": [],
                "issues": ["Could not connect to AI service. Your code was saved — try again shortly."],
                "suggestions": [],
                "example_fixes": "",
                "score": 0,
                "should_retry": True,
                "model": self.model,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": int((time.time() - start) * 1000),
                "prompt_template": prompt["system"],
            }

        latency_ms = int((time.time() - start) * 1000)
        raw_text = response.content[0].text
        parsed = self._parse_grading_response(raw_text)

        return {
            **parsed,
            "model": self.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "latency_ms": latency_ms,
            "prompt_template": prompt["system"],
        }

    # --- Future stubs ---

    def generate_deep_dive(self, topic: str, lesson_context: str) -> str:
        """[Future] Generate an on-demand deep-dive explanation."""
        raise NotImplementedError("Deep dive generation coming in next iteration")

    def _build_variation_prompt(
        self,
        seed_exercise: Dict[str, Any],
        variation_type: str,
    ) -> Dict[str, str]:
        """Build prompt for generating an exercise variation."""
        type_instructions = {
            "scenario": (
                "Generate a variation with a DIFFERENT domain/scenario but the SAME learning objective. "
                "For example, if the original uses a database, use a weather API instead. "
                "Keep the same difficulty and the same core pattern being taught."
            ),
            "concept": (
                "Generate a DIFFERENT exercise within the same category. "
                "Teach a different pattern or concept, but keep the same difficulty level. "
                "The exercise should feel fresh, not like a rephrasing."
            ),
            "harder": (
                "Generate a HARDER version of this exercise. Add constraints, edge cases, "
                "or require more sophisticated patterns. The core topic stays the same "
                "but the implementation demands more engineering skill."
            ),
        }

        system = (
            "You are a senior AI engineer creating practice exercises for a full-stack engineer "
            "learning AI agent patterns. Generate a high-quality exercise variation.\n\n"
            f"{type_instructions.get(variation_type, type_instructions['scenario'])}\n\n"
            "Respond with valid JSON matching this schema:\n"
            '{"title": "short descriptive title", '
            '"prompt_md": "200+ word problem statement in markdown", '
            '"starter_code": "Python starter with TODOs and type hints", '
            '"solution_code": "complete working Python solution", '
            '"explanation_md": "300+ word explanation with key decisions"}\n\n'
            "The exercise must feel like real engineering work, not a toy problem."
        )

        user = (
            f"## Seed Exercise: {seed_exercise.get('title', '')}\n"
            f"Category: {seed_exercise.get('category', '')}\n"
            f"Difficulty: {seed_exercise.get('difficulty', '')}\n\n"
            f"### Problem\n{seed_exercise.get('prompt_md', '')}\n\n"
            f"### Starter Code\n```python\n{seed_exercise.get('starter_code', '')}\n```\n\n"
            f"### Solution\n```python\n{seed_exercise.get('solution_code', '')}\n```\n\n"
            f"### Explanation\n{seed_exercise.get('explanation_md', '')}"
        )

        return {"system": system, "user": user}

    def _parse_variation_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Parse Claude's JSON response into a variation dict. Returns None on failure."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            data = json.loads(cleaned)
            required = ["title", "prompt_md", "starter_code", "solution_code", "explanation_md"]
            if not all(k in data and data[k] for k in required):
                return None
            return {k: data[k] for k in required}
        except (json.JSONDecodeError, ValueError):
            return None

    def generate_exercise_variation(
        self,
        seed_exercise: Dict[str, Any],
        variation_type: str = "scenario",
    ) -> Optional[Dict[str, Any]]:
        """Generate an exercise variation using Claude. Returns variation dict or None."""
        prompt = self._build_variation_prompt(seed_exercise, variation_type)
        start = time.time()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=prompt["system"],
                messages=[{"role": "user", "content": prompt["user"]}],
            )
        except (anthropic.APITimeoutError, anthropic.APIConnectionError):
            return None

        latency_ms = int((time.time() - start) * 1000)
        raw_text = response.content[0].text
        parsed = self._parse_variation_response(raw_text)

        if parsed:
            parsed["_meta"] = {
                "model": self.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "latency_ms": latency_ms,
                "prompt_template": prompt["system"],
            }

        return parsed

    def coach_interview_answer(self, question: str, user_answer: str) -> Dict:
        """[Future] Coach a user on their interview answer."""
        raise NotImplementedError("Interview coaching coming in next iteration")
