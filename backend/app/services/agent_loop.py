"""AgentLoop: multi-round tool_use orchestration for personalized exercise generation."""
import json
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.agent_tools import TOOL_SCHEMAS, execute_tool


class AgentLoop:
    """Orchestrates multi-round Claude API interactions using tool_use.

    Sends a task with tools available, processes tool_use blocks by executing
    each tool and feeding results back, then loops until Claude emits a final
    text response containing the generated exercise variation.
    """

    def __init__(self, db: Session, user_id: int, client: Any, model: str) -> None:
        self.db = db
        self.user_id = user_id
        self.client = client
        self.model = model

    def run(
        self,
        task: str,
        context: dict,
        max_rounds: int = 3,
    ) -> Optional[dict]:
        """Run the agent loop up to max_rounds, returning parsed output or None.

        Args:
            task: The variation task type (e.g. "scenario", "concept", "harder").
            context: Dict with seed exercise data and variation_type.
            max_rounds: Maximum tool-use/response cycles before giving up.

        Returns:
            Parsed variation dict with _meta attached, or None on failure.
        """
        system_prompt = self._build_system_prompt(task, context)
        user_message = self._build_user_message(task, context)

        messages: list[dict] = [{"role": "user", "content": user_message}]
        tool_calls: list[dict] = []
        total_start = time.time()

        for _round in range(max_rounds):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=system_prompt,
                messages=messages,
                tools=TOOL_SCHEMAS,
                timeout=30.0,
            )

            if response.stop_reason == "tool_use":
                # Collect assistant message first
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                # Execute each tool_use block and collect results
                tool_results = []
                for block in assistant_content:
                    if block.type != "tool_use":
                        continue

                    tool_start = time.time()
                    output = execute_tool(block.name, block.input, self.db, self.user_id)
                    latency_ms = int((time.time() - tool_start) * 1000)

                    tool_calls.append(
                        {
                            "tool": block.name,
                            "input": block.input,
                            "output": output,
                            "latency_ms": latency_ms,
                        }
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(output),
                        }
                    )

                messages.append({"role": "user", "content": tool_results})
                continue

            # stop_reason is "end_turn" or similar — find the text block
            text_block = next(
                (block for block in response.content if hasattr(block, "text")),
                None,
            )
            if text_block is None:
                return None

            parsed = self._parse_output(text_block.text)
            if parsed is None:
                return None

            total_latency_ms = int((time.time() - total_start) * 1000)
            parsed["_meta"] = {
                "model": self.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "latency_ms": total_latency_ms,
                "rounds": _round + 1,
                "tool_calls": tool_calls,
                "prompt_template": system_prompt,
            }
            return parsed

        # Exceeded max_rounds without a text response
        return None

    def _build_system_prompt(self, task: str, context: dict) -> str:
        """Build the system prompt for the agent, injecting seed and variation metadata."""
        seed = context.get("seed_exercise", {})
        variation_type = context.get("variation_type", task)

        return (
            "You are an AI engineering tutor generating a personalized exercise variation.\n\n"
            "## Your tools\n"
            "You have tools to understand this specific learner. Use them to personalize the exercise:\n"
            "1. Call `check_mastery` FIRST to understand overall gaps\n"
            "2. Optionally call `get_exercise_history` to see what's been practiced recently\n"
            "3. Optionally call `get_recent_feedback` to see recurring strengths/weaknesses\n"
            "4. Call `read_lesson_summary` only if you need specific lesson context\n\n"
            "After gathering context (1-2 tool calls is usually enough), generate the variation.\n\n"
            "## Personalization rules\n"
            "- Target the learner's WEAKEST area\n"
            "- Avoid topics from their last 5 exercises\n"
            "- If they have recurring issues in feedback, design the exercise to practice fixing those\n"
            "- Match difficulty to their mastery level\n\n"
            "## Learner profile\n"
            "Senior full-stack engineer transitioning to AI engineering (application-level, not research).\n\n"
            f"## Variation type: {variation_type}\n"
            f"## Seed exercise: {seed.get('title', '')}\n"
            f"## Seed category: {seed.get('category', '')}\n\n"
            "## Output format\n"
            "After gathering learner context, respond with ONLY valid JSON:\n"
            "{title, prompt_md, starter_code, solution_code, explanation_md}"
        )

    def _build_user_message(self, task: str, context: dict) -> str:
        """Build the user message including the full seed exercise for context."""
        seed = context.get("seed_exercise", {})
        variation_type = context.get("variation_type", task)

        parts = [
            f"Generate a **{variation_type}** variation of this exercise, personalized to my current gaps.\n",
            f"## Seed Exercise",
            f"**Title:** {seed.get('title', '')}",
            f"**Category:** {seed.get('category', '')}",
            f"**Difficulty:** {seed.get('difficulty', '')}\n",
            f"### Problem Statement\n{seed.get('prompt_md', '')}\n",
            f"### Starter Code\n```python\n{seed.get('starter_code', '')}\n```\n",
            f"### Reference Solution\n```python\n{seed.get('solution_code', '')}\n```\n",
            f"### Explanation\n{seed.get('explanation_md', '')}\n",
            "First use your tools to understand my mastery profile, then generate the personalized variation.",
        ]
        return "\n".join(parts)

    def _parse_output(self, raw: str) -> Optional[dict]:
        """Parse Claude's JSON text response into a variation dict.

        Mirrors the logic from AIService._parse_variation_response, stripping
        optional markdown fences and validating required fields.

        Returns:
            Dict with variation fields, or None if parsing fails or fields are missing.
        """
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
