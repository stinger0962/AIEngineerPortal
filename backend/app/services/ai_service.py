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
            "You are reviewing Python code from an experienced full-stack engineer learning "
            "AI engineering (application-level — agents, RAG, tool use, not ML research).\n\n"
            "## Review priorities (in order)\n"
            "1. **Correctness**: Does it solve the problem? Handle edge cases?\n"
            "2. **AI engineering patterns**: Does it follow current best practices for "
            "tool design, structured outputs, error handling with LLMs, token management?\n"
            "3. **Production readiness**: Proper error handling, typing, logging, cost awareness?\n"
            "4. **Code quality**: Clean, readable, idiomatic Python?\n\n"
            "## Feedback style\n"
            "- Be specific: quote the line, explain what's wrong, show the fix\n"
            "- Teach the WHY: \"This matters because in production agents, X causes Y\"\n"
            "- Give concrete code examples in `example_fixes`, not vague suggestions\n"
            "- If the solution works but isn't production-quality, say so and show the upgrade\n"
            "- Acknowledge what they did well — learning builds on strengths\n\n"
            "## Output format\n"
            "Respond with ONLY valid JSON (no markdown fences):\n"
            '{"strengths": ["specific things done well"], '
            '"issues": ["specific problems with line references"], '
            '"suggestions": ["actionable next steps to improve"], '
            '"example_fixes": "markdown with ```python code blocks showing fixes", '
            '"score": 0-100, "should_retry": true/false}\n\n'
            "Score guide: 90+ production-ready, 75-89 works but needs polish, "
            "60-74 has issues worth fixing, <60 fundamental problems — retry."
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

    # --- Deep dive ---

    def _build_deep_dive_prompt(
        self,
        question: str,
        lesson_context: Dict[str, Any],
    ) -> Dict[str, str]:
        """Build prompt for answering a deep-dive question about a lesson."""
        system = (
            "You are a senior AI engineering mentor answering a deep-dive question from a learner.\n\n"
            "## Who you are helping\n"
            "A senior full-stack engineer transitioning to AI engineering on the APPLICATION side — "
            "they build production systems with LLMs and agents, not ML research. They already know "
            "Python, APIs, and system design. They are learning: tool design, agent orchestration, "
            "RAG patterns, evaluation, prompt engineering, cost optimization, and production reliability.\n\n"
            "## Lesson context\n"
            f"**Learning path:** {lesson_context.get('path_name', 'AI Engineering')}\n"
            f"**Lesson title:** {lesson_context.get('title', '')}\n\n"
            f"### Full lesson content\n{lesson_context.get('content_md', '')}\n\n"
            "## How to answer\n"
            "Answer the learner's specific question with:\n"
            "1. **Clear explanation** — connect directly to what the lesson already taught; "
            "build on the learner's existing mental model, don't repeat the lesson verbatim\n"
            "2. **Working Python code examples** — where relevant, show runnable code with "
            "type hints, docstrings, and real imports; prefer concrete examples over pseudocode\n"
            "3. **Production context** — explain how this applies in real AI/agent systems, "
            "what can go wrong at scale, and what experienced engineers watch out for\n"
            "4. **Common misconceptions** — call out the traps that trip up developers new to "
            "AI engineering; explain why the naive approach fails\n\n"
            "## Output format\n"
            "Respond with ONLY valid JSON (no markdown fences, no commentary):\n"
            '{"answer_md": "your full answer in markdown with code blocks", '
            '"related_concepts": ["concept1", "concept2", "concept3"]}\n\n'
            "Keep related_concepts to 3-5 items — specific, actionable topics the learner should "
            "explore next given this question. Not generic advice."
        )

        user = f"## Question\n{question}"

        return {"system": system, "user": user}

    def _parse_deep_dive_response(self, raw: str) -> Optional[Dict[str, Any]]:
        """Parse Claude's JSON response into deep-dive answer dict. Returns None on failure."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            data = json.loads(cleaned)
            answer_md = data.get("answer_md", "")
            related_concepts = data.get("related_concepts", [])
            if not answer_md:
                return None
            return {
                "answer_md": answer_md,
                "related_concepts": related_concepts if isinstance(related_concepts, list) else [],
            }
        except (json.JSONDecodeError, ValueError):
            return None

    def generate_deep_dive(
        self,
        question: str,
        lesson_context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Generate a deep-dive answer for a lesson question using Claude. Returns dict or None."""
        prompt = self._build_deep_dive_prompt(question, lesson_context)
        start = time.time()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=prompt["system"],
                messages=[{"role": "user", "content": prompt["user"]}],
            )
        except (anthropic.APITimeoutError, anthropic.APIConnectionError):
            return None

        latency_ms = int((time.time() - start) * 1000)
        raw_text = response.content[0].text
        parsed = self._parse_deep_dive_response(raw_text)

        if parsed:
            parsed["_meta"] = {
                "model": self.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "latency_ms": latency_ms,
                "prompt_template": prompt["system"],
            }

        return parsed

    def _build_variation_prompt(
        self,
        seed_exercise: Dict[str, Any],
        variation_type: str,
    ) -> Dict[str, str]:
        """Build prompt for generating an exercise variation."""
        type_instructions = {
            "scenario": (
                "VARIATION TYPE: Same learning objective, DIFFERENT real-world scenario.\n"
                "- Change the domain (e.g., if original uses a search API, use a payment gateway, CI/CD pipeline, or IoT sensor feed)\n"
                "- Keep the same core pattern and difficulty\n"
                "- The new scenario must introduce its own realistic constraints (rate limits, auth, pagination, error codes)"
            ),
            "concept": (
                "VARIATION TYPE: DIFFERENT concept within the same category.\n"
                "- Teach a different pattern the learner hasn't seen in this seed exercise\n"
                "- Stay at the same difficulty level but cover NEW ground\n"
                "- Example shifts: tool registry → tool dependency graph, ReAct loop → plan-then-execute, memory manager → context window optimizer"
            ),
            "harder": (
                "VARIATION TYPE: Same topic, significantly HARDER.\n"
                "- Add production constraints: concurrent requests, graceful degradation, partial failures, token budget limits\n"
                "- Require handling edge cases: malformed responses, timeout cascades, retry storms, circular dependencies\n"
                "- Demand more sophisticated patterns: backpressure, circuit breakers, structured logging, cost tracking"
            ),
        }

        system = (
            "You are creating a practice exercise for an AI engineer who builds production agent systems.\n\n"
            "## Who this is for\n"
            "A senior full-stack engineer transitioning to AI engineering on the APPLICATION side — "
            "they harness LLMs and agents, they don't train models. They already know Python, APIs, "
            "and system design. They need to learn: tool design, agent orchestration, RAG patterns, "
            "evaluation, prompt engineering, cost optimization, and production reliability.\n\n"
            "## Current AI engineering landscape (use these in exercises)\n"
            "- Tool/function calling patterns (OpenAI, Anthropic, MCP protocol)\n"
            "- Agent frameworks: LangGraph, CrewAI, Claude Agent SDK, AutoGen\n"
            "- Structured outputs with Pydantic validation\n"
            "- Retrieval-augmented generation (vector DBs, reranking, hybrid search)\n"
            "- Evaluation: LLM-as-judge, reference-based scoring, human-in-the-loop\n"
            "- Cost control: token budgets, caching, model routing (expensive vs cheap models)\n"
            "- Observability: tracing agent steps, logging decisions, measuring latency\n"
            "- Safety: guardrails, content filtering, prompt injection defense\n\n"
            f"{type_instructions.get(variation_type, type_instructions['scenario'])}\n\n"
            "## Exercise quality requirements\n"
            "1. **Problem statement**: Real-world motivation (\"You're building X for Y because Z\"). "
            "Include specific constraints the learner must handle. No toy problems.\n"
            "2. **Starter code**: Typed Python with clear TODO markers. Include imports, type hints, "
            "dataclass/Pydantic models, and the function signatures. The learner fills in the logic, "
            "not the scaffolding.\n"
            "3. **Solution code**: Production-quality Python. Use proper error handling, logging, "
            "type hints, and docstrings. Show the BEST way to solve it, not just a working way.\n"
            "4. **Explanation**: Teach WHY each design decision was made. Cover:\n"
            "   - Why this pattern over alternatives\n"
            "   - Common mistakes and how to avoid them\n"
            "   - How this applies in production agent systems\n"
            "   - What to watch out for at scale\n\n"
            "## Output format\n"
            "Respond with ONLY valid JSON (no markdown fences, no commentary):\n"
            "{\n"
            '  "title": "Concise, specific title (not generic)",\n'
            '  "prompt_md": "Problem statement in markdown. 200-400 words. Include WHY this matters, WHAT to build, and specific CONSTRAINTS.",\n'
            '  "starter_code": "Python with imports, types, models, function signatures, and TODO comments. 30-80 lines.",\n'
            '  "solution_code": "Complete, production-quality Python. 50-150 lines.",\n'
            '  "explanation_md": "Teaching explanation in markdown. 300-600 words. Cover design decisions, mistakes to avoid, production considerations."\n'
            "}"
        )

        user = (
            f"## Seed Exercise\n"
            f"**Title:** {seed_exercise.get('title', '')}\n"
            f"**Category:** {seed_exercise.get('category', '')}\n"
            f"**Difficulty:** {seed_exercise.get('difficulty', '')}\n\n"
            f"### Problem Statement\n{seed_exercise.get('prompt_md', '')}\n\n"
            f"### Starter Code\n```python\n{seed_exercise.get('starter_code', '')}\n```\n\n"
            f"### Reference Solution\n```python\n{seed_exercise.get('solution_code', '')}\n```\n\n"
            f"### Explanation\n{seed_exercise.get('explanation_md', '')}\n\n"
            "Generate a variation that teaches something genuinely useful for building production AI agent systems."
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
