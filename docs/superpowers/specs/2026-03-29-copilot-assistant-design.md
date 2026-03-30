# AI Study Copilot — Conversational Assistant

**Date**: 2026-03-29
**Status**: Approved
**Phase**: 6a (first sub-project of Phase 6)

## Context

The portal has 4 dynamic AI features (grading, variations, deep-dives, interview coaching) and an agent loop with tools for querying learner state. Phase 6 adds a conversational assistant — a chat interface where the learner asks questions about AI engineering and gets answers grounded in portal content, with suggested next actions based on mastery gaps.

## Goals

1. Chat interface for asking questions about AI engineering topics
2. Answers grounded in portal content (lessons, exercises, knowledge articles)
3. Suggest concrete next actions (study this lesson, try this exercise) based on mastery
4. Reuse existing AgentLoop and tool infrastructure — no new dependencies

## Non-Goals

- Semantic/vector search (future: add as a tool when corpus grows)
- Persistent conversation history (v1 is session-only, client-side state)
- Streaming responses (synchronous JSON like existing AI features)
- Multi-user support

## Architecture

Extends the proven agent tool infrastructure. Creates a new `CopilotLoop` class (not reusing `AgentLoop` directly, which is hardcoded for variation generation) that handles multi-turn conversation and markdown+JSON parsing. Reuses `execute_tool` and tool schemas from `agent_tools.py`.

**Why a separate CopilotLoop:** The existing `AgentLoop` has hardcoded system prompts for variations, single-turn message initialization, and JSON-only parsing. The copilot needs multi-turn conversation history, a different system prompt, and markdown+optional-JSON parsing. Creating `CopilotLoop` avoids risking regressions in the working variation flow.

**CopilotLoop differences from AgentLoop:**
- Accepts full conversation history (`messages` array), not just a single user message
- System prompt is chat-oriented, not variation-oriented
- Uses all 7 tools (4 existing + 3 new), passed explicitly
- Response parsing: extracts markdown body + optional JSON block for suggested actions (not pure JSON)
- Returns `{"response": str, "suggested_actions": list}` instead of variation dict

### New Tools (added to `agent_tools.py`)

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `search_lessons` | `{query: str}` | `{lessons: [{title, slug, path_name, summary}]}` | Keyword search across lesson titles and content |
| `search_exercises` | `{query: str}` | `{exercises: [{title, category, difficulty, summary}]}` | Keyword search across exercise titles and prompts |
| `get_knowledge_article` | `{slug: str}` | `{title, category, content_md}` | Read full knowledge article content |

Search tools use SQL `ILIKE` matching on title and content fields, limited to top 5 results. `search_exercises` returns truncated `prompt_md` (first 200 chars) as `summary` since Exercise has no summary field. `search_lessons` joins to `LearningPath` for `path_name` (same pattern as `read_lesson_summary`). This is sufficient for the current corpus (~30 lessons, ~50 exercises, ~9 knowledge articles).

### Existing Tools (reused from agent_tools.py)

- `check_mastery` — learner's mastery profile per path
- `get_exercise_history` — recent exercise attempts
- `get_recent_feedback` — recent AI feedback entries
- `read_lesson_summary` — specific lesson content

### New Endpoint

`POST /api/v1/copilot/chat`

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "What are the key patterns for agent memory?"},
    {"role": "assistant", "content": "...previous response..."},
    {"role": "user", "content": "Can you give me a code example?"}
  ]
}
```

**Response:**
```json
{
  "response": "markdown string with the assistant's answer",
  "suggested_actions": [
    {"type": "lesson", "title": "Agent memory & state", "slug": "agent-memory-and-state"},
    {"type": "exercise", "title": "Build a conversation memory manager", "slug": "12"}
  ],
  "model": "claude-sonnet-4-20250514",
  "input_tokens": 2400,
  "output_tokens": 800,
  "latency_ms": 4500
}
```

- Rate limit: 5 requests/minute (Redis counter, existing pattern)
- Daily token budget: shared with other AI features (100K total)
- Cost tracked in `ai_feedback` table with `feature = "copilot"`
- `reference_id` set to NULL for copilot (no specific content reference)
- Max conversation history: last 10 messages sent to Claude (older messages trimmed)

### Copilot System Prompt

```
You are a study copilot for an AI engineer in training. This person is a senior
full-stack engineer transitioning to AI engineering on the application side —
they harness LLMs and agents, they don't train models.

## Your role
- Answer questions about AI engineering concepts, patterns, and best practices
- Ground your answers in the learner's portal content when relevant
- Suggest concrete next actions based on their mastery gaps
- Be concise and practical — code examples over theory

## Your tools
Use tools to personalize responses:
1. `search_lessons` or `search_exercises` — find relevant portal content for the question
2. `check_mastery` — understand what the learner is weak at
3. `read_lesson_summary` or `get_knowledge_article` — get specific content to reference
4. `get_exercise_history` / `get_recent_feedback` — understand recent practice

## Response format
- Answer the question in clear markdown with code examples where helpful
- End with 1-3 suggested actions as JSON in a ```json block:
  [{"type": "lesson|exercise|article", "title": "...", "slug": "..."}]
- If no actions are relevant, omit the JSON block
```

### Error Handling

- Agent timeout (30s) → return "I'm having trouble thinking right now. Try again."
- Rate limit → "You've been chatting a lot! Try again in a minute."
- Daily budget → "Daily AI limit reached, try again tomorrow."
- Parse failure → return raw text as response with empty suggested_actions

## Frontend

### New Page: `/copilot`

**Route:** `frontend/src/app/copilot/page.tsx`

**Sidebar:** New "Copilot" entry added between "Jobs" and "Settings" in SidebarNav.

**UI components:**

`CopilotChat` (client component):
- `messages` state: `Array<{role: "user" | "assistant", content: string, actions?: SuggestedAction[]}>`
- Input box at bottom with send button, Enter to send, Shift+Enter for newline
- User messages: right-aligned, ink (#14213d) background, cream text
- Assistant messages: left-aligned, cream (#f8f3e8) background, ink text
- Assistant content renders markdown (code blocks, bullet points, links)
- Suggested actions render as clickable cards below the response:
  - Lesson → links to `/learn/lesson/{slug}`
  - Exercise → links to `/practice/python/{slug}`
  - Article → links to `/knowledge/{slug}`
- Loading state: typing indicator dots while awaiting response
- Conversation state is client-side only (not persisted across page reloads)
- Max conversation shown: last 20 messages (older messages scroll off)

**Empty state:** Welcome message: "Ask me anything about AI engineering. I have access to your learning progress, lessons, exercises, and knowledge articles."

## Key Files

**New:**
- `backend/app/services/copilot_loop.py` — CopilotLoop class (multi-turn, markdown+JSON parsing)
- `backend/app/api/v1/routes/copilot.py` — chat endpoint
- `frontend/src/app/copilot/page.tsx` — copilot page
- `frontend/src/components/copilot/copilot-chat.tsx` — chat client component

**Modified:**
- `backend/app/services/agent_tools.py` — add 3 new tools + schemas
- `backend/app/api/v1/api.py` — register copilot router
- `frontend/src/components/layout/sidebar-nav.tsx` — add Copilot nav entry
- `frontend/src/lib/api/portal.ts` — add copilot API method
- `frontend/src/lib/types/portal.ts` — add copilot types

## Implementation Batches

### Batch 1: Backend (tools + CopilotLoop + endpoint)
- Add 3 new tool functions + schemas to agent_tools.py
- Create CopilotLoop class with multi-turn conversation and markdown+JSON parsing
- Create copilot endpoint
- Register router

### Batch 2: Frontend (chat UI)
- Add copilot types and API method
- Create CopilotChat component
- Create copilot page
- Add sidebar entry

### Batch 3: Deploy
- Push, tag, deploy
- Verify on production
