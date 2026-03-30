"""CopilotLoop for multi-turn conversational AI copilot with tools."""
from __future__ import annotations

import json
import re
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.agent_tools import TOOL_SCHEMAS, execute_tool


class CopilotLoop:
    """Multi-turn conversational agent for the AI Study Copilot."""

    def __init__(self, db: Session, user_id: int, client: Any, model: str):
        self.db = db
        self.user_id = user_id
        self.client = client
        self.model = model

    def run(
        self,
        messages: list[dict[str, str]],
        max_rounds: int = 3,
    ) -> Optional[dict[str, Any]]:
        """Run copilot conversation. Returns {"response": str, "suggested_actions": list, "_meta": dict}."""
        system_prompt = self._system_prompt()

        # Convert user messages to Claude format, keep last 10 messages
        claude_messages = messages[-10:] if len(messages) > 10 else messages

        tool_calls_log: list[dict] = []
        total_input_tokens = 0
        total_output_tokens = 0
        start_time = time.time()

        for round_num in range(1, max_rounds + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    system=system_prompt,
                    messages=claude_messages,
                    tools=TOOL_SCHEMAS,
                    timeout=30.0,
                )
            except Exception:
                return None

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_start = time.time()
                        tool_output = execute_tool(
                            block.name, block.input, self.db, self.user_id
                        )
                        tool_latency = int((time.time() - tool_start) * 1000)

                        tool_calls_log.append({
                            "tool": block.name,
                            "input": block.input,
                            "output": tool_output,
                            "latency_ms": tool_latency,
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(tool_output),
                        })

                claude_messages.append({"role": "assistant", "content": response.content})
                claude_messages.append({"role": "user", "content": tool_results})
                continue

            # Final text response
            for block in response.content:
                if block.type == "text":
                    total_latency = int((time.time() - start_time) * 1000)
                    response_text, actions = self._parse_response(block.text)

                    return {
                        "response": response_text,
                        "suggested_actions": actions,
                        "_meta": {
                            "model": self.model,
                            "input_tokens": total_input_tokens,
                            "output_tokens": total_output_tokens,
                            "latency_ms": total_latency,
                            "rounds": round_num,
                            "tool_calls": tool_calls_log,
                            "total_tokens": total_input_tokens + total_output_tokens,
                        },
                    }

        return None

    def _parse_response(self, raw: str) -> tuple[str, list[dict]]:
        """Extract markdown body and optional JSON suggested_actions block."""
        # Look for a JSON array block at the end of the response
        json_pattern = r"```json\s*(\[[\s\S]*?\])\s*```"
        match = re.search(json_pattern, raw)

        actions = []
        response_text = raw

        if match:
            try:
                actions = json.loads(match.group(1))
                # Validate action structure
                actions = [
                    a for a in actions
                    if isinstance(a, dict) and "type" in a and "title" in a and "slug" in a
                ]
            except (json.JSONDecodeError, ValueError):
                actions = []
            # Remove the JSON block from the response text
            response_text = raw[:match.start()].rstrip()

        return response_text, actions

    def _system_prompt(self) -> str:
        return (
            "You are a study copilot for an AI engineer in training. This person is a senior "
            "full-stack engineer transitioning to AI engineering on the application side — "
            "they harness LLMs and agents, they don't train models.\n\n"
            "## Your role\n"
            "- Answer questions about AI engineering concepts, patterns, and best practices\n"
            "- Ground your answers in the learner's portal content when relevant\n"
            "- Suggest concrete next actions based on their mastery gaps\n"
            "- Be concise and practical — code examples over theory\n\n"
            "## Your tools\n"
            "Use tools to personalize responses:\n"
            "1. `search_lessons` or `search_exercises` — find relevant portal content for the question\n"
            "2. `check_mastery` — understand what the learner is weak at\n"
            "3. `read_lesson_summary` or `get_knowledge_article` — get specific content to reference\n"
            "4. `get_exercise_history` / `get_recent_feedback` — understand recent practice\n\n"
            "## Response format\n"
            "- Answer the question in clear markdown with code examples where helpful\n"
            "- End with 1-3 suggested actions as JSON in a ```json block:\n"
            '  [{"type": "lesson|exercise|article", "title": "...", "slug": "..."}]\n'
            "- If no actions are relevant, omit the JSON block\n"
        )
