# Agent-Powered Exercise Variations (Option C Evolution)

**Date**: 2026-03-29
**Status**: Approved
**Builds on**: v0.10.0 (all 4 dynamic features live, all 6 paths enriched)

## Context

The portal's AIService currently uses direct Claude API calls (Option A) — fixed prompt templates with no awareness of the learner's state. Every generation is context-blind. This spec evolves exercise variation generation to use an agent loop with tools that query the learner's mastery, exercise history, and recent feedback before generating.

**Scope**: Exercise variations only. The other 3 dynamic features (grading, deep-dives, interview coaching) continue with Option A and can be migrated later using the same pattern.

**Constraint**: All Claude API calls must stay in the backend (hosted in Singapore). The frontend only calls FastAPI endpoints, never Anthropic directly. This is already the case and does not change.

## Goals

1. Exercise variations become personalized — targeting the learner's actual weaknesses
2. Prove the agent + tool_use pattern on one feature before expanding
3. Graceful fallback to direct generation if agent fails
4. Meta-learning: building an agent system teaches agent patterns

## Non-Goals

- Agent-powering all 4 dynamic features (future iteration)
- Separate agent microservice (overkill for single-user portal)
- Claude Agent SDK (using standard Messages API + tool_use instead)
- New frontend changes (endpoint contract stays the same)

## Architecture

### SDK Approach

Standard Anthropic Messages API with `tools` parameter. The existing `anthropic` SDK (already installed) supports this natively. No new dependencies.

### Agent Loop

**New file:** `backend/app/services/agent_loop.py`

```
AgentLoop
├── __init__(db: Session, user_id: int, client: Anthropic, model: str)
├── run(task: str, context: dict, max_rounds: int = 3) → Optional[dict]
├── _execute_tool(tool_name: str, tool_input: dict) → dict
├── _register_tools() → list[dict]  # JSON schemas for Claude tool_use
```

**Flow:**
1. Endpoint receives variation request
2. Creates `AgentLoop(db, user_id, client, model)`
3. Calls `agent.run(task="generate_variation", context={seed_exercise, variation_type})`
4. Agent loop:
   - Round 1: System prompt + task + tools → Claude responds with `tool_use` blocks
   - Execute tools against DB, feed results back as `tool_result` messages
   - Round 2: Claude may call more tools or generate final answer
   - Round 3 (max): If no final output yet, append "Now generate the variation based on what you've gathered" and force completion
5. Parse final response using existing `_parse_variation_response()`
6. Return result with `_meta` including tool calls made and total tokens across all rounds

### Tools (4 internal functions)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `check_mastery` | `{}` | `{paths: [{name, mastery_pct, practice_reps, weakest_area}]}` | Know what learner is weak at |
| `get_exercise_history` | `{limit: int}` | `{exercises: [{title, category, score, attempted_at}]}` | Know what's been practiced |
| `get_recent_feedback` | `{limit: int}` | `{feedback: [{exercise_title, strengths, issues, score}]}` | Know recurring mistakes |
| `read_lesson_summary` | `{lesson_slug: str}` | `{title, path_name, summary}` | Get context on what was taught |

Each tool is a Python function that queries the existing SQLAlchemy models. No new tables, no new endpoints. Tools are defined as JSON schemas in Anthropic's tool_use format.

### Tool JSON Schema Example

```json
{
  "name": "check_mastery",
  "description": "Get the learner's mastery profile across all learning paths. Returns mastery percentage, practice reps, and weakest area per path.",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

### Integration with AIService

`generate_exercise_variation()` gains optional `db` and `user_id` parameters:

```python
def generate_exercise_variation(self, seed_exercise, variation_type, db=None, user_id=None):
    # Try agent-powered generation
    if self.is_available and db and user_id:
        try:
            agent = AgentLoop(db, user_id, client=self.client, model=self.model)
            result = agent.run(
                task="generate_variation",
                context={"seed_exercise": seed_exercise, "variation_type": variation_type},
                max_rounds=3,
            )
            if result:
                return result
        except Exception:
            pass  # fall through

    # Fallback: direct generation (current Option A behavior)
    return self._direct_generate_variation(seed_exercise, variation_type)
```

The current `generate_exercise_variation()` logic is renamed to `_direct_generate_variation()`.

### Variation Endpoint Changes

The endpoint already has access to `db: Session` via FastAPI dependency injection and `user_id` via the helper function. These are now passed through to `AIService.generate_exercise_variation()`.

No endpoint signature changes. No frontend changes. The frontend doesn't know whether it got an agent-powered or direct variation.

### Agent System Prompt

The agent's system prompt combines:
1. The existing variation prompt (learner context, AI engineering landscape, quality requirements)
2. Agent instructions: "You have tools to understand this learner's current state. Use them to personalize the exercise variation. Call check_mastery first to understand gaps, then optionally check exercise history or recent feedback for more context."
3. Output format: same JSON schema as current variations

### Cost & Performance

- **Tokens per request**: ~2-3x current (extra rounds for tool calls). Estimated 6,000-10,000 tokens total vs current 3,000-4,000.
- **Latency**: ~2-3x current (sequential API calls). Estimated 5-10 seconds vs current 3-5 seconds.
- **Daily budget impact**: Well within 100K daily token budget for a single user doing 5-15 exercises/day.
- **Fallback**: If agent fails, direct generation takes ~3-5 seconds. User experience is never blocked.

### Error Handling

- Agent timeout (30 seconds total) → fall back to direct generation
- Tool execution failure → return error dict to Claude, let it proceed without that data
- Max rounds exceeded → force final generation with whatever context was gathered
- Claude returns no tool calls → treat as direct generation (Claude decided it doesn't need context)
- Parsing failure → fall back to direct generation

### Observability

The `ai_feedback` record for agent-powered variations includes:
- `prompt_template`: the full agent system prompt
- `response_json`: includes `_meta.tool_calls` — list of tools called and their results
- `input_tokens` / `output_tokens`: total across all rounds
- `latency_ms`: total including tool execution

Tool calls shape in `_meta`:
```json
{
  "tool_calls": [
    {"tool": "check_mastery", "input": {}, "output": {"paths": [...]}, "latency_ms": 12},
    {"tool": "get_exercise_history", "input": {"limit": 10}, "output": {"exercises": [...]}, "latency_ms": 8}
  ],
  "rounds": 2,
  "total_tokens": 8500
}
```

This enables reviewing what context the agent gathered and whether it improved variation quality.

## Key Files

**New:**
- `backend/app/services/agent_loop.py` — AgentLoop class with tool registry and execution loop
- `backend/app/services/agent_tools.py` — Tool functions (check_mastery, get_exercise_history, etc.)

**Modified:**
- `backend/app/services/ai_service.py` — generate_exercise_variation() gains agent delegation + fallback
- `backend/app/api/v1/routes/exercise_variations.py` — pass db and user_id to AIService

## Future Evolution

Once proven on variations, the same `AgentLoop` can power:
- **Grading**: agent checks what was taught before critiquing
- **Deep-dives**: agent adjusts explanation depth based on mastery
- **Interview coaching**: agent focuses on gaps identified by mastery profile

Each migration is a small change: swap the direct method call for an `AgentLoop.run()` with a different task string.
