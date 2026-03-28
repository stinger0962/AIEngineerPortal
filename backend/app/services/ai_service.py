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

    def generate_exercise_variation(self, seed_exercise: Dict) -> Dict:
        """[Future] Generate a new exercise variation from a seed exercise."""
        raise NotImplementedError("Exercise variation generation coming in next iteration")

    def coach_interview_answer(self, question: str, user_answer: str) -> Dict:
        """[Future] Coach a user on their interview answer."""
        raise NotImplementedError("Interview coaching coming in next iteration")
