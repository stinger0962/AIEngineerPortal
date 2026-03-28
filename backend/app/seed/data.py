from __future__ import annotations

from datetime import date

DEFAULT_USER = {
    "name": "Alex Builder",
    "email": "alex@local.portal",
    "target_role": "AI Engineer",
    "skill_profile_json": {
        "strengths": ["React", "TypeScript", "product delivery", "backend systems"],
        "growth_areas": ["Python", "RAG", "evaluation", "deployment"],
    },
    "preferences_json": {
        "focus_style": "project-first",
        "preferred_topics": ["llm-apps", "rag", "agents", "observability"],
    },
}

LEARNING_LIBRARY = [
    {
        "title": "Python for AI Engineers",
        "slug": "python-for-ai-engineers",
        "description": "Build practical Python fluency for APIs, pipelines, evaluation scripts, and debugging in applied AI systems.",
        "level": "beginner",
        "estimated_hours": 6,
        "lessons": [
            {
                "title": "Python runtime habits that matter in AI work",
                "summary": "Focus on data modeling, IO boundaries, debugging, and iteration speed rather than syntax memorization.",
                "content_md": """## Why this path starts with Python

For an experienced full-stack engineer, the Python gap is usually not syntax. The real gap is confidence under pressure while moving through provider SDKs, JSON payloads, scripts, evaluation loops, and one-off debugging sessions.

If JavaScript and TypeScript taught you how to ship product features, Python should now become your fast execution language for:

- API integrations
- ingestion and ETL scripts
- evaluation tooling
- retrieval pipelines
- experiment harnesses
- lightweight services

## The operating principle

In AI work, Python is the language that sits closest to the messy boundary between an idea and a working system. That means your Python habits should optimize for:

- readable control flow
- explicit inputs and outputs
- lightweight validation
- fast debugging
- safe serialization
- rerunnable scripts

## What good Python feels like in AI work

A good Python module in an AI system should feel calm to read. You should be able to answer:

1. What comes in?
2. What gets validated?
3. What gets transformed?
4. What leaves the boundary?
5. What happens when something fails?

When those answers are unclear, AI systems get fragile quickly because the payloads are semi-structured and the failure modes are messy.

## Runtime habits that compound

### 1. Name the boundary clearly

A provider response, uploaded file, benchmark row, or retrieved chunk is a boundary. Treat it like one.

Bad habit:

- pass the raw payload everywhere and let downstream code guess structure

Better habit:

- normalize once at the edge
- raise or record errors early
- keep the middle of the system boring

### 2. Log enough to debug, not enough to drown

In AI systems, debugging often means inspecting:

- request identifiers
- provider or model name
- retry count
- latency
- prompt or context version
- schema mismatch reason

If your logs do not preserve the path of failure, you will keep changing prompts when the real issue is payload shape or retrieval quality.

### 3. Prefer small functions with obvious return shapes

Many Python bugs in AI projects come from helper functions that quietly return different shapes in different branches. Keep return values stable.

```python
from typing import TypedDict


class NormalizedResponse(TypedDict):
    request_id: str
    content: str
    status: str


def normalize_provider_payload(payload: dict) -> NormalizedResponse:
    return {
        "request_id": str(payload.get("id", "missing")),
        "content": str(payload.get("content", "")).strip(),
        "status": str(payload.get("status", "ok")),
    }
```

This is not fancy. That is the point. In AI engineering, boring boundaries are a competitive advantage.

### 4. Make scripts rerunnable

Many high-leverage AI tasks live in scripts:

- dataset preparation
- benchmark generation
- document cleanup
- ingestion backfills
- prompt experiment exports

If a script is not idempotent, you cannot trust it after the first run.

Practical rules:

- use explicit input and output paths
- do not silently overwrite valuable artifacts
- print summary stats at the end
- make failure conditions visible

## A concrete mental model

When you write Python for AI systems, think in layers:

- boundary layer: requests, files, provider responses, queue payloads
- transformation layer: shaping, cleaning, scoring, filtering
- orchestration layer: retries, sequencing, branching, persistence
- review layer: logs, traces, metrics, evaluation output

Your speed improves once each layer has a clean responsibility.

## Common failure patterns

Watch for these early:

- one function fetching data, validating it, logging, retrying, and formatting the UI payload all at once
- hidden mutation of shared dicts
- magical string keys sprinkled across the codebase
- scripts that only work from one local directory
- exception handling that swallows the failure reason

## What to practice after this lesson

- normalize one loose payload into a typed internal shape
- rewrite one AI script so it is safe to rerun
- add one log line that would actually help you debug a provider failure

## Takeaway

The win is not becoming a Python trivia expert. The win is becoming fast and trustworthy when AI systems hand you messy inputs, weak guarantees, and operational ambiguity.
""",
                "estimated_minutes": 50,
            },
            {
                "title": "Modeling data with dicts, dataclasses, and Pydantic",
                "summary": "Use strict validation at boundaries and keep the middle of the system simple.",
                "content_md": """## Data modeling choices

AI systems move semi-structured data around constantly. That does not mean everything should stay an untyped dict forever.

The practical question is not which modeling approach is best. It is where you need speed and where you need trust.

## A useful rule of thumb

- use dicts for fast exploration
- use dataclasses for stable internal objects
- use Pydantic for boundaries you cannot afford to guess at

## Dicts: good for discovery, risky as a long-term contract

Dicts are perfect when:

- the payload shape is still changing
- you are prototyping an integration
- you are inspecting raw documents or responses

But if a dict crosses too many layers, the whole system becomes a rumor about structure instead of a contract.

## Dataclasses: good for internal clarity

Dataclasses work well when you already know the shape and want readable internal code.

```python
from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    doc_id: str
    text: str
    score: float
    source: str
```

This is great for the middle of the system where you want:

- readable attributes
- low ceremony
- clear intent

## Pydantic: use it where trust matters

Pydantic is strongest at system boundaries:

- request validation
- response normalization
- persistence contracts
- config parsing

Why? Because these are the places where bad assumptions become production bugs.

```python
from pydantic import BaseModel, Field


class ProviderResult(BaseModel):
    request_id: str = Field(min_length=1)
    content: str
    model: str
    latency_ms: int
```

If the provider returns nonsense, you find out immediately instead of carrying silent damage downstream.

## A layered pattern that works well

Try this pattern:

1. receive raw payload as dict
2. validate and normalize with Pydantic
3. convert to simpler internal objects when helpful
4. emit stable shapes at the next boundary

This keeps your code flexible without becoming vague.

## How this shows up in real portal work

Examples:

- news ingestion starts as raw remote payloads
- jobs ingestion normalizes inconsistent fields across sources
- learning and interview APIs return stable shapes to the frontend
- project data should stay explicit so scoring and recommendations remain trustworthy

## Decision guide

Use a dict when:

- you are exploring
- the schema is not stable
- the value of speed is higher than the value of guarantees

Use a dataclass when:

- the shape is stable inside your application
- you want clean, readable internal code

Use Pydantic when:

- external systems are involved
- bad input would be expensive
- you need reliable validation, parsing, and error messages

## Mistakes to avoid

- validating nowhere
- validating everywhere
- using Pydantic models deep in the middle of code that only needs simple objects
- pretending a dict is temporary for months

## Practice prompt

Take one portal payload and decide:

- what is raw input?
- what is the normalized boundary model?
- what is the simplest internal shape after validation?

## Takeaway

Good Python data modeling is not about purity. It is about being strict where ambiguity is dangerous and lightweight where speed matters.
""",
                "estimated_minutes": 55,
            },
            {
                "title": "Async IO for provider calls and ingestion work",
                "summary": "Use async where network waiting dominates and make timeout and retry behavior explicit.",
                "content_md": """## Async patterns that pay off

Async matters in AI work because many valuable operations are waiting problems, not CPU problems.

Examples:

- provider calls
- multi-document fetches
- crawling and ingestion
- retrieval fan-out
- health checks across dependencies

## The decision rule

Use async when network waiting dominates. Do not use it just because it sounds more advanced.

If you are doing mostly CPU-bound data transforms, async may add complexity without speeding anything up.

## Where async really helps

### Provider integrations

You may need to:

- call a model provider
- fetch citations
- store traces
- query a cache

Those waits stack up quickly if they happen serially.

### Ingestion pipelines

News, jobs, or document pipelines often need to fetch many remote resources in parallel. Async lets you improve throughput without starting with a heavy worker architecture.

## What to make explicit

Async code becomes trustworthy when four things are visible:

- timeout policy
- retry policy
- concurrency limits
- failure logging

If those are hidden, the system may look fast when healthy and become impossible to debug when degraded.

## Example shape

```python
import asyncio


async def fetch_with_timeout(client, url: str) -> dict:
    return await asyncio.wait_for(client.get(url), timeout=8)
```

That line is simple, but it expresses an operational decision: this fetch should not hang forever.

## Concurrency is a budget, not a badge

Calling 100 upstream services at once is not maturity. It is often a missing control surface.

Prefer:

- small bounded batches
- explicit semaphores
- measured retries

This matters especially when working with provider rate limits or unstable external feeds.

## Mixing sync and async

Two common mistakes:

- calling blocking libraries inside async code
- forcing async into parts of the system that do not need it

If a dependency is blocking, either keep the path synchronous or isolate the blocking work so the async layer stays honest.

## Debugging async code

You need logs that preserve:

- which task failed
- which request or URL was involved
- whether it timed out, retried, or gave up

Without that, async failures feel random even when they are systematic.

## Portal-specific examples

Async is a good fit here for:

- external signal refresh
- provider-backed assistants in later phases
- document ingestion and retrieval fan-out

It is not automatically the best fit for:

- every lesson endpoint
- simple CRUD routes
- local transformations that are already fast

## Practice prompt

Take one sync network call in your head and ask:

1. What is the timeout?
2. What is retryable?
3. What is the concurrency limit?
4. What gets logged when it fails?

If you cannot answer those, you do not have an operational async design yet.

## Takeaway

Async is valuable when it makes waiting explicit and controlled. It is not a goal on its own.
""",
                "estimated_minutes": 50,
            },
            {
                "title": "File handling, serialization, and safe evaluation scripts",
                "summary": "Write scripts you can trust repeatedly for dataset prep, prompt experiments, and benchmark runs.",
                "content_md": """## Script quality matters

Some of the most important AI engineering work never appears in the user-facing product. It happens in scripts:

- data cleanup
- benchmark creation
- export jobs
- prompt experiment runners
- trace analysis

Weak scripts create invisible instability. Strong scripts create leverage.

## The bar for a good script

A good AI script should be:

- explicit about inputs
- explicit about outputs
- safe to rerun
- easy to inspect after execution

## Prefer pathlib and stable paths

Use `pathlib` so file behavior is readable and portable.

```python
from pathlib import Path


INPUT_PATH = Path("data/raw/eval.jsonl")
OUTPUT_PATH = Path("data/processed/eval-clean.jsonl")
```

Hard-coded ad hoc paths make scripts fragile, especially when you revisit them weeks later.

## JSONL is often the right default

For AI experiments, JSONL works well because:

- each row is inspectable
- partial writes are easier to reason about
- downstream tools can stream it

Use full JSON when the artifact is naturally one object. Use JSONL when you are processing records.

## Idempotence matters

If a script cannot be rerun safely, it is not ready.

Strategies:

- write to a new output file
- support overwrite explicitly, not silently
- include a dry-run mode when useful
- print counts for processed, skipped, and failed rows

## Make failures actionable

Do not just say failed. Capture:

- which input row or file failed
- why it failed
- how many items were skipped

That turns a broken run into a debugging task instead of a mystery.

## Evaluation script checklist

Before trusting an evaluation script, check:

- where do inputs come from?
- what version of prompt or rubric is being used?
- where are outputs stored?
- can I compare this run to a previous run?
- what happens if one row is malformed?

## A small reliable pattern

```python
def process_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    cleaned = []
    failures = []
    for row in rows:
        try:
            cleaned.append(transform_row(row))
        except Exception as exc:
            failures.append({"row_id": row.get("id"), "error": str(exc)})
    return cleaned, failures
```

This is simple, but it creates the foundation for honest reruns and post-run review.

## Portal-specific leverage

In this portal, strong script habits matter for:

- seeding durable content
- refreshing intelligence feeds
- building future evaluation packs
- generating practice artifacts

## Practice prompt

Take one script you would trust least in production and improve it by adding:

- explicit paths
- summary output
- non-destructive write behavior
- row-level failure capture

## Takeaway

Good scripts are not glamorous, but they are one of the clearest signs that your AI work can survive beyond a single demo run.
""",
                "estimated_minutes": 45,
            },
            {
                "title": "Turning Python fluency into portfolio leverage",
                "summary": "Use Python skills to make every project more credible through APIs, tooling, and repeatability.",
                "content_md": """## Portfolio move

Python fluency becomes valuable in your transition when it changes how your projects feel to another engineer or hiring manager.

The question is not Did I use Python.

The question is:

Did Python make this project look more engineered, more testable, and more production-shaped?

## What Python can signal in a portfolio

Done well, Python can show:

- clean API boundaries
- typed request and response models
- scriptable evaluation workflows
- ingestion or retrieval tooling
- deployment-ready service structure
- debugging-friendly logs and traces

## What weak portfolio Python looks like

- one notebook with no clean interface
- scripts with no stable inputs or outputs
- provider code scattered across the project
- no explanation of runtime tradeoffs

That may still demonstrate curiosity, but it does not yet demonstrate AI engineering.

## What stronger portfolio Python looks like

### 1. A clean service boundary

Even a small FastAPI surface helps. It shows:

- inputs
- outputs
- validation
- separation between UI and backend logic

### 2. Evaluation or benchmark tooling

This is especially valuable because it signals maturity. Many demo projects can answer a question once; fewer can measure quality across runs.

### 3. Useful internal scripts

Examples:

- `prepare_eval_set.py`
- `replay_failed_cases.py`
- `backfill_chunks.py`
- `score_run.py`

Those filenames communicate discipline immediately.

### 4. Debuggable operational behavior

If your project logs useful runtime details and exposes health assumptions clearly, it feels more like a real system than a prototype.

## A practical portfolio checklist

For each project, ask:

- Is there at least one stable Python boundary?
- Is there at least one script or utility that makes the project repeatable?
- Is there evidence of validation and failure handling?
- Can I explain the architecture in interview language?

## How this applies to your portal

Good candidates for Python-heavy portfolio proof include:

- the evaluation dashboard
- a retrieval-backed assistant
- a jobs or signal ingestion service
- future adaptive practice generation

## Practice prompt

Take one current project and add one Python artifact that makes it more credible:

- an API route
- a typed boundary model
- an evaluation script
- a replay or debug utility

## Takeaway

Python becomes portfolio leverage when it demonstrates engineering discipline, not just model access.
""",
                "estimated_minutes": 45,
            },
        ],
    },
    {
        "title": "LLM App Foundations",
        "slug": "llm-app-foundations",
        "description": "Learn the product and systems primitives behind useful LLM applications.",
        "level": "intermediate",
        "estimated_hours": 16,
        "lessons": [
            {"title": "Prompt, context, tools, and memory", "summary": "Map the core components of an LLM application before choosing frameworks.", "content_md": "## Foundations\n\nUnderstand how prompt construction, context assembly, tool access, and memory each shape system behavior.", "estimated_minutes": 35},
            {"title": "Request lifecycle of an LLM feature", "summary": "Trace a user request from UI input to final response and logging.", "content_md": "## Request lifecycle\n\nTrack context loading, provider calls, post-processing, and persistence.", "estimated_minutes": 40},
            {"title": "Guardrails and structured outputs", "summary": "Constrain outputs with schemas, system prompts, and approval boundaries.", "content_md": "## Guardrails\n\nReliability improves when format expectations and fallback behavior are explicit.", "estimated_minutes": 40},
            {"title": "Cost, latency, and failure budgets", "summary": "Make tradeoffs visible instead of treating providers like magical black boxes.", "content_md": "## Operational tradeoffs\n\nTrack token cost, timeout behavior, retries, and perceived UX latency.", "estimated_minutes": 35},
            {"title": "Portfolio slice: ship one narrow assistant well", "summary": "Design a focused feature instead of a vague chatbot.", "content_md": "## Portfolio move\n\nChoose one workflow where good context and strong UX produce obvious value.", "estimated_minutes": 35},
        ],
    },
    {
        "title": "RAG Systems",
        "slug": "rag-systems",
        "description": "Build retrieval systems that are explainable, measurable, and debuggable.",
        "level": "intermediate",
        "estimated_hours": 18,
        "lessons": [
            {"title": "Why retrieval fails in practice", "summary": "Separate indexing, chunking, ranking, and prompting failures.", "content_md": "## Retrieval failures\n\nMost bad RAG answers come from the pipeline before generation even starts.", "estimated_minutes": 40},
            {"title": "Chunking and metadata design", "summary": "Choose chunk size and metadata fields to support retrieval and evaluation later.", "content_md": "## Chunking\n\nChunk boundaries should preserve meaning and provenance.", "estimated_minutes": 45},
            {"title": "Ranking, re-ranking, and citations", "summary": "Improve answer grounding with better document selection and explicit provenance.", "content_md": "## Ranking\n\nGood citations depend on both retrieval quality and prompt structure.", "estimated_minutes": 40},
            {"title": "Evaluation loops for RAG", "summary": "Measure answer quality, faithfulness, and retrieval usefulness separately.", "content_md": "## Evaluation\n\nInspect retrieval traces, not just final answers.", "estimated_minutes": 40},
            {"title": "Portfolio slice: domain research assistant", "summary": "Turn RAG into a credible product artifact with sources and review controls.", "content_md": "## Portfolio move\n\nA strong RAG project shows ingestion, retrieval transparency, and evaluation discipline.", "estimated_minutes": 35},
        ],
    },
    {
        "title": "AI Agents and Tools",
        "slug": "ai-agents-and-tools",
        "description": "Understand when agentic patterns help and how to keep them safe.",
        "level": "intermediate",
        "estimated_hours": 14,
        "lessons": [
            {
                "title": "Tool design for LLM agents",
                "summary": "Design function schemas, input validation, return contracts, and error envelopes that LLMs can call reliably.",
                "estimated_minutes": 40,
                "content_md": """## Tool design for LLM agents

### Why this matters

Every agentic system lives or dies by the quality of its tools. When a model decides to call a function, it relies entirely on the schema you gave it — the name, the description, the parameter types, and what comes back. Sloppy tool definitions create cascading failures: the model hallucinates parameters, misinterprets results, or retries endlessly. If you are building agent systems professionally, tool design is the single highest-leverage skill you can sharpen.

In production, a well-designed tool means fewer wasted tokens, fewer retries, lower latency, and more predictable behavior. A poorly designed tool means debugging sessions where you stare at traces wondering why the model called `search_database` with a date string where an integer was expected.

### Core concepts

**JSON Schema for function definitions.** Every major LLM provider (OpenAI, Anthropic, Google) uses JSON Schema to describe tools. The schema tells the model what parameters exist, their types, which are required, and what the function does. The model generates a JSON object matching this schema, and your code executes the function.

Key principles for good tool schemas:

- **Descriptive names and descriptions.** The model reads these. `search_orders` is better than `query_db`. Add a description that explains *when* to use it, not just *what* it does.
- **Minimal required parameters.** Every required field the model must fill is a chance for it to hallucinate. Keep the interface tight.
- **Enum constraints.** If a parameter has known valid values, use an enum. The model will pick from the list instead of inventing values.
- **No nested complexity.** Flat parameter objects work best. Deeply nested schemas confuse models and increase error rates.

**Return contracts.** Your tool should always return a structured response the model can parse. Never return raw HTML, giant blobs of text, or unstructured error messages. Define a return shape and stick to it.

**Error envelopes.** When a tool fails, the model needs to understand what happened so it can decide whether to retry, try a different approach, or report the failure. Wrap errors in a consistent envelope with a status, error type, and human-readable message.

### Working example

Here is a complete tool definition with validation, retry logic, and structured error handling — the kind of function you would register with an agent framework.

```python
import json
import time
import httpx
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

# --- Return contract ---
class ToolStatus(str, Enum):
    success = "success"
    error = "error"

class ToolResult(BaseModel):
    status: ToolStatus
    data: Optional[dict] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None

# --- The tool function ---
def lookup_order(order_id: str, include_items: bool = False) -> dict:
    \"\"\"Look up an order by its ID. Use this when the user asks about
    a specific order status, shipment, or order details.

    Args:
        order_id: The order ID (format: ORD-XXXXX)
        include_items: Whether to include line items in the response
    \"\"\"
    # Input validation
    if not order_id.startswith("ORD-") or len(order_id) != 9:
        return ToolResult(
            status=ToolStatus.error,
            error_type="validation_error",
            error_message=f"Invalid order ID format: {order_id}. Expected ORD-XXXXX.",
        ).model_dump()

    # Retry logic for transient failures
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            resp = httpx.get(
                f"https://api.internal.co/orders/{order_id}",
                params={"items": include_items},
                timeout=5.0,
            )
            resp.raise_for_status()
            return ToolResult(
                status=ToolStatus.success,
                data=resp.json(),
            ).model_dump()
        except httpx.TimeoutException:
            if attempt < max_retries:
                time.sleep(1.5 ** attempt)
                continue
            return ToolResult(
                status=ToolStatus.error,
                error_type="timeout",
                error_message="Order service timed out after retries.",
            ).model_dump()
        except httpx.HTTPStatusError as e:
            return ToolResult(
                status=ToolStatus.error,
                error_type=f"http_{e.response.status_code}",
                error_message=f"Order service returned {e.response.status_code}.",
            ).model_dump()

# --- JSON Schema for the LLM provider ---
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_order",
        "description": (
            "Look up an order by its ID. Use when the user asks about "
            "a specific order's status, shipment tracking, or line items."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID in the format ORD-XXXXX",
                    "pattern": "^ORD-[A-Z0-9]{5}$",
                },
                "include_items": {
                    "type": "boolean",
                    "description": "Include line items in the response",
                    "default": False,
                },
            },
            "required": ["order_id"],
        },
    },
}
```

Notice the pattern: validate inputs *before* doing any work, retry on transient failures only, and always return the same `ToolResult` shape. The model sees `status: error` and can decide what to do next — it never has to parse a Python traceback.

### Common mistakes

1. **Returning raw exceptions.** If your tool returns `"ConnectionError: [Errno 111] Connection refused"`, the model will try to interpret that string creatively. Use structured error envelopes.
2. **Giant return payloads.** Returning 50KB of JSON eats your context window. Trim results to what the model actually needs to answer the user's question.
3. **Vague descriptions.** `"Searches the database"` tells the model nothing about *when* to use this tool. Be specific about the use case.
4. **Missing validation.** If the model can pass a string where you expect an integer, it will — eventually. Validate early and return a clear error.
5. **No retry for transient errors.** Network calls fail. A single retry with backoff prevents the agent from giving up on a momentary blip.

### Try it yourself

Take an API you already use (weather, GitHub, a database) and wrap it as an agent tool. Define the JSON Schema, add input validation, implement retry logic, and return structured results. Then feed the schema to an LLM and see if it calls the tool correctly on the first try. If it does not, look at what confused it — that is where your schema needs work.
""",
            },
            {
                "title": "Planning and reasoning loops",
                "summary": "Implement ReAct, plan-then-execute, and reflection patterns so agents can decompose and solve multi-step tasks.",
                "estimated_minutes": 40,
                "content_md": """## Planning and reasoning loops

### Why this matters

A single LLM call can answer a question, but it cannot reliably complete a multi-step task. If you ask a model to "find the cheapest flight from NYC to London next Tuesday and book it," a single call will hallucinate an answer. An agent with a reasoning loop will break that into steps: search flights, compare prices, confirm details, then act. The reasoning loop is what separates a chatbot from an agent.

In production AI engineering, you will implement these loops constantly. Whether you are building a research assistant, a code generation pipeline, or an internal workflow tool, the pattern is always the same: think, act, observe, repeat. Getting this loop right determines whether your agent completes tasks or spirals into expensive, useless iterations.

### Core concepts

**ReAct (Reason + Act).** The most widely used agent loop. On each iteration the model produces a thought (reasoning about what to do next), an action (a tool call), and then receives an observation (the tool result). The loop continues until the model decides it has enough information to produce a final answer.

**Plan-then-execute.** Instead of interleaving reasoning and action, the model first generates a complete plan (a list of steps), then executes each step sequentially. This works well when the task structure is predictable and you want to show the user a plan before executing it.

**Reflection.** After producing an output, the model critiques its own work and decides whether to revise. This is useful for writing, code generation, and any task where quality improves with self-review.

**Stop conditions matter more than the loop itself.** Every agent loop needs explicit termination criteria: a maximum number of iterations, a token budget, or a confidence signal. Without stop conditions, agents will loop forever, burning money and producing garbage.

### Working example

Here is a working ReAct loop that decomposes a multi-step research question using tools.

```python
import json
from openai import OpenAI

client = OpenAI()

# Define available tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression to evaluate"}
                },
                "required": ["expression"],
            },
        },
    },
]

def execute_tool(name: str, args: dict) -> str:
    \"\"\"Execute a tool and return the result as a string.\"\"\"
    if name == "web_search":
        # In production, call a real search API
        return json.dumps({"results": [f"Result for: {args['query']}"]})
    elif name == "calculate":
        try:
            result = eval(args["expression"])  # Use a safe math parser in production
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})
    return json.dumps({"error": f"Unknown tool: {name}"})

def react_loop(question: str, max_iterations: int = 6) -> str:
    \"\"\"Run a ReAct loop to answer a multi-step question.\"\"\"
    messages = [
        {
            "role": "system",
            "content": (
                "You are a research assistant. Break complex questions into steps. "
                "Use tools to gather information. When you have enough information "
                "to answer confidently, provide your final answer directly."
            ),
        },
        {"role": "user", "content": question},
    ]

    for i in range(max_iterations):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg)

        # If the model produced a final answer (no tool calls), we are done
        if not msg.tool_calls:
            return msg.content

        # Execute each tool call and feed results back
        for tool_call in msg.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = execute_tool(tool_call.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        print(f"[Iteration {i + 1}] Called: {[tc.function.name for tc in msg.tool_calls]}")

    # Hit max iterations — return whatever we have
    final = client.chat.completions.create(
        model="gpt-4o",
        messages=messages + [
            {"role": "user", "content": "Please provide your best answer now with what you have."}
        ],
    )
    return final.choices[0].message.content

# Usage
answer = react_loop(
    "What is the population of France and Germany combined, "
    "and what percentage of the EU total does that represent?"
)
print(answer)
```

The key structural choices: the loop has a hard iteration cap, tool results go back as `tool` role messages, and when the model stops calling tools the loop exits. In production you would add token counting, cost tracking, and logging at each iteration.

### Common mistakes

1. **No iteration limit.** The agent gets confused and loops forever. Always set `max_iterations` and handle the case where you hit it.
2. **Letting the model plan in its head.** If you skip the system prompt guidance to break things into steps, the model will try to answer in one shot and hallucinate.
3. **Not logging intermediate steps.** When the agent gives a wrong final answer, you need the trace of thoughts and tool calls to debug it. Log every iteration.
4. **Overly complex plans.** Plan-then-execute works poorly when the model generates 15 steps. Encourage short plans (3-5 steps) and allow re-planning.
5. **Ignoring cost.** Each iteration is an LLM call. A 10-iteration loop on GPT-4o with long context can cost dollars per query. Track and budget.

### Try it yourself

Build a ReAct loop that answers a question requiring two different tools — for example, "What is the current stock price of AAPL multiplied by the number of employees at Apple?" Make the agent search for each fact separately and then combine them with a calculation tool. Watch the trace to see how the model decomposes the problem.
""",
            },
            {
                "title": "Multi-agent orchestration",
                "summary": "Coordinate multiple specialized agents using supervisor patterns, handoffs, and structured message passing.",
                "estimated_minutes": 40,
                "content_md": """## Multi-agent orchestration

### Why this matters

A single agent with ten tools gets confused. It forgets which tool to use, mixes up contexts, and makes poor decisions as complexity grows. The solution is the same one we use in software engineering: decompose. Instead of one agent doing everything, you build specialized agents — a researcher, a coder, a reviewer — and orchestrate them with a supervisor.

Multi-agent patterns are how production AI systems handle complex workflows. Customer support bots route to specialist agents. Code generation pipelines have separate planning, writing, and review stages. Data analysis systems decompose into query builders, executors, and interpreters. If you are building agent systems at work, you will encounter multi-agent orchestration within months.

### Core concepts

**Supervisor pattern.** One agent (the supervisor) receives the user request, decides which specialist to delegate to, reviews the result, and either returns it or delegates again. The supervisor does not do the work itself — it routes and quality-checks.

**Handoffs.** When one agent transfers control to another, it passes a structured context object — not the entire conversation history. A handoff includes: what the next agent needs to do, what context it needs, and what a good result looks like.

**Message passing vs shared state.** Agents can communicate by passing messages through the supervisor (hub-and-spoke) or by reading/writing to shared state (blackboard pattern). Hub-and-spoke is simpler to debug. Shared state is more flexible but creates race conditions and ordering issues.

**Specialist agent design.** Each sub-agent should have a narrow system prompt, a limited set of tools, and a clear output contract. A research agent has search tools and returns structured findings. A code agent has a sandbox and returns tested code. Narrow scope means better performance.

### Working example

Here is a supervisor agent that delegates to specialist sub-agents for a research-and-summarize workflow.

```python
import json
from dataclasses import dataclass, field
from openai import OpenAI

client = OpenAI()

@dataclass
class AgentResult:
    agent_name: str
    content: str
    metadata: dict = field(default_factory=dict)

def run_agent(name: str, system_prompt: str, user_message: str, model: str = "gpt-4o") -> AgentResult:
    \"\"\"Run a single specialist agent and return its result.\"\"\"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    return AgentResult(
        agent_name=name,
        content=response.choices[0].message.content,
        metadata={"model": model, "tokens": response.usage.total_tokens},
    )

# --- Specialist agents ---

def research_agent(topic: str) -> AgentResult:
    return run_agent(
        name="researcher",
        system_prompt=(
            "You are a research specialist. Given a topic, produce a structured "
            "research brief with key facts, statistics, and source references. "
            "Output valid JSON with keys: facts (list of strings), "
            "statistics (list of strings), sources (list of strings)."
        ),
        user_message=f"Research this topic thoroughly: {topic}",
    )

def writer_agent(research_brief: str, task: str) -> AgentResult:
    return run_agent(
        name="writer",
        system_prompt=(
            "You are a technical writer. Given research material and a writing "
            "task, produce clear, well-structured content. Use the research "
            "provided — do not invent facts."
        ),
        user_message=f"Writing task: {task}\\n\\nResearch material:\\n{research_brief}",
    )

def reviewer_agent(draft: str, criteria: str) -> AgentResult:
    return run_agent(
        name="reviewer",
        system_prompt=(
            "You are an editorial reviewer. Evaluate the draft against the "
            "given criteria. Output JSON with keys: approved (bool), "
            "score (1-10), issues (list of strings), suggestions (list of strings)."
        ),
        user_message=f"Criteria: {criteria}\\n\\nDraft to review:\\n{draft}",
    )

# --- Supervisor ---

def supervisor(task: str, max_revisions: int = 2) -> str:
    \"\"\"Orchestrate research, writing, and review agents.\"\"\"
    print(f"[Supervisor] Received task: {task}")

    # Step 1: Research
    print("[Supervisor] Delegating to researcher...")
    research = research_agent(task)
    print(f"[Supervisor] Research complete ({research.metadata['tokens']} tokens)")

    # Step 2: Write
    print("[Supervisor] Delegating to writer...")
    draft = writer_agent(research.content, task)
    print(f"[Supervisor] Draft complete ({draft.metadata['tokens']} tokens)")

    # Step 3: Review loop
    for revision in range(max_revisions):
        print(f"[Supervisor] Delegating to reviewer (revision {revision + 1})...")
        review = reviewer_agent(
            draft.content,
            criteria="Accuracy, clarity, completeness, and proper use of research.",
        )

        # Parse review result
        try:
            review_data = json.loads(review.content)
        except json.JSONDecodeError:
            print("[Supervisor] Reviewer returned non-JSON, accepting draft.")
            break

        if review_data.get("approved", False) or review_data.get("score", 0) >= 8:
            print(f"[Supervisor] Draft approved (score: {review_data.get('score')})")
            break

        # Revise based on feedback
        print(f"[Supervisor] Revision needed (score: {review_data.get('score')})")
        feedback = "\\n".join(review_data.get("suggestions", []))
        draft = writer_agent(
            research.content,
            f"{task}\\n\\nRevise based on this feedback:\\n{feedback}",
        )

    total_tokens = sum(r.metadata["tokens"] for r in [research, draft, review])
    print(f"[Supervisor] Complete. Total tokens: {total_tokens}")
    return draft.content

# Usage
result = supervisor("Explain the tradeoffs of using LLMs for code review in CI pipelines")
print(result)
```

The supervisor controls the flow, each specialist has a narrow job, and the review loop has a bounded number of revisions. Each agent result carries metadata for cost tracking.

### Common mistakes

1. **Passing full conversation history between agents.** Each specialist should receive only the context it needs. Passing everything wastes tokens and confuses the specialist.
2. **No output contracts.** If the research agent returns free-form text one time and JSON another time, the writer agent cannot reliably consume it. Enforce output structure.
3. **Unbounded review loops.** The reviewer and writer can ping-pong forever. Always cap revision rounds.
4. **Supervisor does specialist work.** If the supervisor starts writing content or doing research, you have lost the decomposition benefit. Keep it as a router.
5. **No cost tracking.** Multi-agent flows multiply costs. Track tokens per agent per run from day one.

### Try it yourself

Build a three-agent system for a task relevant to your work. For example: an agent that takes a bug report, delegates to a "reproducer" agent to write a test case, then delegates to a "fixer" agent to propose a patch, with a "reviewer" agent checking the result. Keep each agent's system prompt under 200 words and give each agent at most two tools.
""",
            },
            {
                "title": "Agent memory and state",
                "summary": "Manage conversation history, sliding window memory, summarization, and state persistence to keep agents effective across long interactions.",
                "estimated_minutes": 40,
                "content_md": """## Agent memory and state

### Why this matters

LLMs are stateless. Every API call starts with no memory of previous interactions — you supply the entire context in the messages array. For short conversations this is fine. For agents that run multi-step tasks, interact over hours, or serve returning users, memory management becomes a core engineering problem.

Without memory management, your agent will hit context window limits mid-task, lose track of earlier decisions, or spend most of its token budget re-reading old messages. In production, you will encounter all three problems. The techniques in this lesson — sliding windows, summarization, and persistence — are how you keep agents functional and affordable over long interactions.

### Core concepts

**Context window budgeting.** Every model has a context limit (128K tokens for GPT-4o, 200K for Claude). Your budget splits into: system prompt, memory/history, current tool results, and space for the model's response. If history consumes 90% of your window, the model has no room to think. Budget explicitly.

**Sliding window.** Keep the most recent N messages and drop older ones. Simple, fast, and works well for conversations where recent context matters most. The risk is losing important early context — the user's original goal, key decisions, or constraints stated at the start.

**Summarization.** Periodically compress older messages into a summary. The agent sees: `[summary of turns 1-20] + [full turns 21-30]`. This preserves important context while staying within token limits. The tradeoff is that summarization itself costs tokens and can lose details.

**Sliding window + summary (hybrid).** The most practical production pattern. Keep recent messages in full, maintain a running summary of everything before that, and include key facts extracted from the conversation. This gives the model both detailed recent context and compressed long-term memory.

**Persistence.** For agents that serve returning users, store conversation summaries and extracted facts in a database. On the next session, load the relevant state into the system prompt. This creates continuity across sessions without replaying entire conversation histories.

### Working example

Here is a memory manager that implements the hybrid sliding window + summarization pattern with explicit token budgeting.

```python
import tiktoken
from dataclasses import dataclass, field
from openai import OpenAI

client = OpenAI()
encoder = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(text: str) -> int:
    return len(encoder.encode(text))

def count_message_tokens(messages: list[dict]) -> int:
    return sum(count_tokens(m.get("content", "")) for m in messages)

@dataclass
class MemoryConfig:
    max_context_tokens: int = 120_000   # Leave headroom below model limit
    system_prompt_tokens: int = 500      # Reserved for system prompt
    response_tokens: int = 4_000         # Reserved for model output
    recent_window: int = 10              # Keep last N messages in full
    summary_trigger: int = 15            # Summarize when history exceeds this

@dataclass
class AgentMemory:
    config: MemoryConfig = field(default_factory=MemoryConfig)
    messages: list[dict] = field(default_factory=list)
    summary: str = ""
    key_facts: list[str] = field(default_factory=list)
    total_tokens_used: int = 0

    @property
    def available_tokens(self) -> int:
        reserved = self.config.system_prompt_tokens + self.config.response_tokens
        return self.config.max_context_tokens - reserved

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.total_tokens_used += count_tokens(content)

        # Trigger summarization when history gets long
        if len(self.messages) > self.config.summary_trigger:
            self._compress()

    def _compress(self):
        \"\"\"Summarize older messages, keep recent window.\"\"\"
        if len(self.messages) <= self.config.recent_window:
            return

        old_messages = self.messages[:-self.config.recent_window]
        old_text = "\\n".join(
            f"{m['role']}: {m['content']}" for m in old_messages
        )

        # Ask the model to summarize and extract key facts
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use a cheap model for summarization
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Summarize the following conversation segment. "
                        "Preserve: decisions made, user preferences, task progress, "
                        "and any constraints. Output JSON with keys: "
                        "summary (string), key_facts (list of strings)."
                    ),
                },
                {"role": "user", "content": old_text},
            ],
            temperature=0.1,
        )

        import json
        try:
            result = json.loads(response.choices[0].message.content)
            self.summary = result.get("summary", "")
            new_facts = result.get("key_facts", [])
            # Deduplicate key facts
            for fact in new_facts:
                if fact not in self.key_facts:
                    self.key_facts.append(fact)
        except json.JSONDecodeError:
            self.summary = response.choices[0].message.content

        # Keep only the recent window
        self.messages = self.messages[-self.config.recent_window:]

    def build_context(self, system_prompt: str) -> list[dict]:
        \"\"\"Build the full message list for the next API call.\"\"\"
        context = [{"role": "system", "content": system_prompt}]

        # Inject memory context if we have it
        if self.summary or self.key_facts:
            memory_block = "## Conversation Memory\\n"
            if self.summary:
                memory_block += f"**Summary of earlier conversation:**\\n{self.summary}\\n\\n"
            if self.key_facts:
                memory_block += "**Key facts:**\\n"
                memory_block += "\\n".join(f"- {f}" for f in self.key_facts)
            context.append({"role": "system", "content": memory_block})

        # Add recent messages
        context.extend(self.messages)

        # Final token check — trim if over budget
        while count_message_tokens(context) > self.available_tokens and len(context) > 2:
            context.pop(1)  # Remove oldest non-system message

        return context

    def get_stats(self) -> dict:
        context = self.build_context("test")
        return {
            "messages_in_window": len(self.messages),
            "summary_length": count_tokens(self.summary),
            "key_facts": len(self.key_facts),
            "context_tokens": count_message_tokens(context),
            "available_tokens": self.available_tokens,
            "total_tokens_used": self.total_tokens_used,
        }

# Usage
memory = AgentMemory()
memory.add_message("user", "I want to build a RAG system for legal documents.")
memory.add_message("assistant", "Great choice. What document formats will you ingest?")
memory.add_message("user", "PDFs and Word docs, about 10,000 documents total.")
# ... after many more turns, older messages get summarized automatically

stats = memory.get_stats()
print(f"Context tokens: {stats['context_tokens']} / {memory.available_tokens}")
```

The key design choices: summarization uses a cheap model (gpt-4o-mini) to save cost, key facts are deduplicated and persist across summaries, and there is a hard token budget enforced at build time.

### Common mistakes

1. **No token budgeting.** You send the full history until the API returns a context length error. By then you have already paid for the failed request.
2. **Summarizing with the expensive model.** Summarization is a low-stakes task. Use a cheap, fast model and save your budget for the agent's actual reasoning.
3. **Losing the user's original goal.** If the user's first message states the objective, make sure it survives summarization — either as a key fact or by always including the first message.
4. **No persistence layer.** When the agent restarts, all memory is lost. Store summaries and key facts in a database keyed by session or user ID.
5. **Over-summarizing.** If you summarize every 5 messages, you spend as much on summarization as on the actual task. Find the right trigger threshold for your use case.

### Try it yourself

Build a chatbot with the hybrid memory manager above. Have a 30-turn conversation with it about a technical topic, then check the stats. Can the agent still recall decisions from turn 3 at turn 30? Experiment with different `recent_window` and `summary_trigger` values to find the sweet spot for your use case.
""",
            },
            {
                "title": "Benchmarking and guardrails",
                "summary": "Build evaluation harnesses to score agent task completion and implement safety guardrails for production agent systems.",
                "estimated_minutes": 40,
                "content_md": """## Benchmarking and guardrails

### Why this matters

An agent that works in your demo might fail 40% of the time in production. Without benchmarks, you will not know until users complain. Without guardrails, failures can mean the agent sends the wrong email, deletes the wrong file, or generates harmful content. Evaluation and safety are not nice-to-haves — they are the difference between a demo and a product.

As an AI engineer, you will spend a significant portion of your time on evaluation. Not because it is glamorous, but because it is the only way to make changes confidently. When you swap a model, adjust a prompt, or add a new tool, benchmarks tell you whether things got better or worse. Guardrails tell you the system stays safe regardless.

### Core concepts

**Task-level evaluation.** For agents, accuracy on individual responses is not enough. You care about task completion: did the agent achieve the user's goal across all steps? This requires test cases with defined inputs, expected outcomes, and scoring criteria.

**Scoring dimensions.** A single pass/fail is too coarse. Score separately on:
- **Correctness** — Did the agent produce the right answer or take the right action?
- **Efficiency** — How many steps and tokens did it take?
- **Tool use accuracy** — Did it call the right tools with the right arguments?
- **Safety** — Did it stay within bounds and avoid harmful outputs?

**Cost tracking.** Every agent run has a dollar cost. Track tokens per model per run, and compute a cost-per-task metric. When you optimize, you want to know if you saved 30% on cost without losing accuracy.

**Input guardrails.** Filter user inputs before they reach the agent. Detect prompt injection attempts, off-topic requests, and inputs that would trigger expensive or dangerous operations.

**Output guardrails.** Validate agent outputs before they reach the user or external systems. Check for PII leakage, harmful content, and responses that violate business rules.

**Action guardrails.** For agents that take real-world actions (sending emails, modifying databases, calling APIs), require confirmation for high-risk actions, set rate limits, and maintain an audit log.

### Working example

Here is a test harness that scores agent task completion across multiple dimensions, with cost tracking.

```python
import json
import time
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class TestCase:
    name: str
    input: str
    expected_outcome: str
    expected_tool_calls: list[str] = field(default_factory=list)
    max_steps: int = 10
    max_cost_usd: float = 0.50

@dataclass
class RunResult:
    output: str
    tool_calls_made: list[str]
    steps: int
    total_tokens: int
    cost_usd: float
    duration_seconds: float

@dataclass
class Score:
    test_name: str
    correctness: float     # 0.0 to 1.0
    efficiency: float      # 0.0 to 1.0
    tool_accuracy: float   # 0.0 to 1.0
    safety_pass: bool
    cost_usd: float
    duration_seconds: float

    @property
    def overall(self) -> float:
        if not self.safety_pass:
            return 0.0
        return (self.correctness * 0.5 + self.efficiency * 0.25 + self.tool_accuracy * 0.25)

# --- Cost calculation ---
COST_PER_1K = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_PER_1K.get(model, COST_PER_1K["gpt-4o"])
    return (input_tokens / 1000 * rates["input"]) + (output_tokens / 1000 * rates["output"])

# --- Guardrails ---
BLOCKED_PATTERNS = [
    "DROP TABLE", "DELETE FROM", "rm -rf",
    "password", "credit card", "SSN",
]

def check_input_guardrail(user_input: str) -> tuple[bool, str]:
    \"\"\"Return (is_safe, reason).\"\"\"
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in user_input.lower():
            return False, f"Blocked pattern detected: {pattern}"
    if len(user_input) > 10_000:
        return False, "Input too long (max 10,000 chars)"
    return True, "OK"

def check_output_guardrail(output: str) -> tuple[bool, str]:
    \"\"\"Check agent output for safety issues.\"\"\"
    import re
    # Check for PII patterns
    if re.search(r'\\b\\d{3}-\\d{2}-\\d{4}\\b', output):  # SSN pattern
        return False, "Potential SSN detected in output"
    if re.search(r'\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b', output):
        return False, "Potential credit card number in output"
    return True, "OK"

# --- Scoring ---
def score_run(test: TestCase, result: RunResult, judge_fn: Callable) -> Score:
    \"\"\"Score a single test run across all dimensions.\"\"\"
    # Correctness: use an LLM judge or deterministic check
    correctness = judge_fn(test.expected_outcome, result.output)

    # Efficiency: ratio of actual steps to max allowed
    efficiency = max(0.0, 1.0 - (result.steps / test.max_steps))

    # Tool accuracy: overlap between expected and actual tool calls
    if test.expected_tool_calls:
        expected_set = set(test.expected_tool_calls)
        actual_set = set(result.tool_calls_made)
        if expected_set:
            precision = len(expected_set & actual_set) / max(len(actual_set), 1)
            recall = len(expected_set & actual_set) / len(expected_set)
            tool_accuracy = 2 * (precision * recall) / max(precision + recall, 0.001)
        else:
            tool_accuracy = 1.0
    else:
        tool_accuracy = 1.0

    # Safety: check output guardrails
    safety_pass, _ = check_output_guardrail(result.output)

    return Score(
        test_name=test.name,
        correctness=correctness,
        efficiency=efficiency,
        tool_accuracy=tool_accuracy,
        safety_pass=safety_pass,
        cost_usd=result.cost_usd,
        duration_seconds=result.duration_seconds,
    )

# --- Test harness ---
def run_benchmark(
    agent_fn: Callable[[str], RunResult],
    test_cases: list[TestCase],
    judge_fn: Callable[[str, str], float],
) -> dict:
    \"\"\"Run all test cases and return aggregate results.\"\"\"
    scores = []
    for test in test_cases:
        # Input guardrail
        is_safe, reason = check_input_guardrail(test.input)
        if not is_safe:
            print(f"  SKIP {test.name}: {reason}")
            continue

        print(f"  Running: {test.name}...", end=" ")
        start = time.time()
        result = agent_fn(test.input)
        result.duration_seconds = time.time() - start

        score = score_run(test, result, judge_fn)
        scores.append(score)
        print(f"score={score.overall:.2f} cost=${score.cost_usd:.4f}")

    # Aggregate
    if not scores:
        return {"error": "No tests completed"}

    return {
        "total_tests": len(scores),
        "avg_overall": sum(s.overall for s in scores) / len(scores),
        "avg_correctness": sum(s.correctness for s in scores) / len(scores),
        "avg_efficiency": sum(s.efficiency for s in scores) / len(scores),
        "avg_tool_accuracy": sum(s.tool_accuracy for s in scores) / len(scores),
        "safety_pass_rate": sum(s.safety_pass for s in scores) / len(scores),
        "total_cost_usd": sum(s.cost_usd for s in scores),
        "avg_duration_s": sum(s.duration_seconds for s in scores) / len(scores),
        "scores": [
            {"name": s.test_name, "overall": s.overall, "cost": s.cost_usd}
            for s in scores
        ],
    }

# --- Example usage ---
test_suite = [
    TestCase(
        name="simple_lookup",
        input="What is the status of order ORD-12345?",
        expected_outcome="Order status with tracking information",
        expected_tool_calls=["lookup_order"],
        max_steps=3,
    ),
    TestCase(
        name="multi_step_research",
        input="Compare the pricing of AWS and GCP for hosting a vector database",
        expected_outcome="Comparison with specific pricing data from both providers",
        expected_tool_calls=["web_search", "web_search"],
        max_steps=6,
    ),
]

# Run with your agent function and a judge
# results = run_benchmark(my_agent, test_suite, my_judge_fn)
# print(json.dumps(results, indent=2))
```

This harness separates concerns cleanly: test cases define expectations, guardrails filter inputs and outputs, scoring covers multiple dimensions, and cost tracking is built in from the start. In production, you would store results in a database, track them over time, and trigger alerts when scores drop.

### Common mistakes

1. **Testing only the happy path.** Your benchmark should include edge cases, ambiguous inputs, and adversarial inputs. If you only test "What is 2+2?", you will not find the real failures.
2. **No cost tracking.** You ship an agent that costs $2 per query without realizing it until the invoice arrives. Track cost per test from day one.
3. **Binary scoring.** Pass/fail misses nuance. An agent that gets 80% of the answer right should score differently from one that is completely wrong.
4. **Guardrails as an afterthought.** Adding safety checks after deployment means unsafe outputs already reached users. Build guardrails into the evaluation pipeline from the start.
5. **Not running benchmarks on every change.** Evaluation only works if you run it consistently. Add your benchmark suite to CI so every prompt change, model swap, or tool update gets scored automatically.

### Try it yourself

Create a test suite of 5 cases for an agent you are building (or plan to build). Include at least one edge case and one adversarial input. Implement the scoring harness above and run your agent against the suite. Then change something — the model, a prompt, a tool — and re-run. Did the scores change? That is the feedback loop that makes agent development systematic instead of ad hoc.
""",
            },
        ],
    },
    {
        "title": "Evaluation and Observability",
        "slug": "evaluation-and-observability",
        "description": "Measure behavior before scaling usage and complexity.",
        "level": "intermediate",
        "estimated_hours": 12,
        "lessons": [
            {"title": "What to measure in AI systems", "summary": "Break evaluation into answer quality, retrieval quality, latency, and cost.", "content_md": "## Measurement\n\nA single score rarely tells you where a system is actually failing.", "estimated_minutes": 35},
            {"title": "Designing benchmark datasets", "summary": "Create a small but representative dataset you can trust for regressions.", "content_md": "## Benchmarks\n\nCurated edge cases beat large but noisy evaluation sets.", "estimated_minutes": 40},
            {"title": "Tracing requests end to end", "summary": "Capture enough runtime data to debug bad outputs later.", "content_md": "## Tracing\n\nWithout traces, AI bugs become anecdotes instead of engineering work.", "estimated_minutes": 35},
            {"title": "Human review workflows", "summary": "Use spot checks and approvals where automation confidence is weak.", "content_md": "## Human review\n\nA human-in-the-loop design can be a production strength.", "estimated_minutes": 35},
            {"title": "Portfolio slice: evaluation dashboard", "summary": "Package your metrics and traces into a compelling project story.", "content_md": "## Portfolio move\n\nEvaluation work signals production readiness better than generic demos.", "estimated_minutes": 30},
        ],
    },
    {
        "title": "AI Deployment and MLOps",
        "slug": "ai-deployment-and-mlops",
        "description": "Make AI systems operable beyond the first successful demo.",
        "level": "advanced",
        "estimated_hours": 18,
        "lessons": [
            {"title": "Deployment shapes for AI products", "summary": "Compare monolith APIs, workers, queues, and evaluation jobs.", "content_md": "## Deployment shapes\n\nChoose the simplest runtime that still respects latency and reliability needs.", "estimated_minutes": 35},
            {"title": "Secrets, environments, and provider configuration", "summary": "Manage credentials, feature flags, and environment drift safely.", "content_md": "## Configuration\n\nAI systems often fail because environments are ambiguous.", "estimated_minutes": 35},
            {"title": "Caching and throughput management", "summary": "Use caching where it reduces cost without hiding bugs.", "content_md": "## Throughput\n\nCaching is powerful only if invalidation and observability remain clear.", "estimated_minutes": 35},
            {"title": "Scheduled jobs and background processing", "summary": "Separate user-facing APIs from indexing, evaluation, and ingestion work.", "content_md": "## Background work\n\nQueues and scheduled jobs protect UX and make operations predictable.", "estimated_minutes": 40},
            {"title": "Portfolio slice: deployable AI service", "summary": "Show that your project survives outside localhost.", "content_md": "## Portfolio move\n\nA production-shaped deployment story increases credibility immediately.", "estimated_minutes": 30},
        ],
    },
    {
        "title": "AI Engineer Interview Readiness",
        "slug": "ai-engineer-interview-readiness",
        "description": "Translate execution experience into role-aligned interview performance.",
        "level": "intermediate",
        "estimated_hours": 10,
        "lessons": [
            {"title": "Tell the transition story clearly", "summary": "Frame your move from full-stack work into AI engineering as leverage, not reset.", "content_md": "## Narrative\n\nPosition your transition around system ownership, shipping skill, and product judgment.", "estimated_minutes": 25},
            {"title": "System design for applied AI", "summary": "Prepare to discuss retrieval, evaluation, providers, and deployment tradeoffs.", "content_md": "## System design\n\nInterviewers want engineering judgment, not only model familiarity.", "estimated_minutes": 30},
            {"title": "Python and backend refresh under pressure", "summary": "Practice the implementation questions likely to show up in loops.", "content_md": "## Coding prep\n\nThe goal is confidence and clarity.", "estimated_minutes": 30},
            {"title": "Role-specific concept review", "summary": "Map topic depth to AI engineer, applied AI, and LLM engineer roles.", "content_md": "## Role targeting\n\nPrepare deeper answers where the target role expects them.", "estimated_minutes": 25},
            {"title": "Portfolio proof and follow-through", "summary": "Use your portal projects as evidence in interviews.", "content_md": "## Portfolio move\n\nA project is only valuable if you can explain the tradeoffs behind it.", "estimated_minutes": 20},
        ],
    },
]

COURSES = [
    {
        "title": "AI Engineer Foundations",
        "slug": "ai-engineer-foundations",
        "description": "A guided transition track that turns software engineering strength into visible AI engineering proof.",
        "difficulty": "beginner",
        "estimated_hours": 18,
        "track_focus": "foundations",
        "status": "active",
        "milestones_json": [
            {
                "label": "Week 1: Build Python execution confidence",
                "status": "active",
                "goal": "Learn the runtime habits, boundary modeling, and async instincts that applied AI work depends on.",
                "outcome": "You can explain and implement safer provider boundaries, cleaner scripts, and rerunnable Python workflows.",
                "path_slug": "python-for-ai-engineers",
                "path_title": "Python for AI Engineers",
                "lesson_slugs": [
                    "python-for-ai-engineers-1",
                    "python-for-ai-engineers-2",
                    "python-for-ai-engineers-3",
                ],
                "exercise_slugs": [
                    "normalize-provider-payloads",
                    "retry-provider-call-timeout-backoff",
                ],
                "project_slug": "evaluation-dashboard",
                "deliverable": "Refactor one project boundary or utility into a typed, rerunnable Python module.",
                "why_it_matters": "This is the fastest way to stop feeling like Python is the bottleneck in AI work.",
            },
            {
                "label": "Week 2: Understand the LLM application shape",
                "status": "planned",
                "goal": "Learn how prompt, context, tools, memory, latency, and guardrails interact in a real product feature.",
                "outcome": "You can map the request lifecycle of an LLM feature and explain the major tradeoffs clearly.",
                "path_slug": "llm-app-foundations",
                "path_title": "LLM App Foundations",
                "lesson_slugs": [
                    "llm-app-foundations-1",
                    "llm-app-foundations-2",
                    "llm-app-foundations-3",
                ],
                "exercise_slugs": [
                    "render-safe-prompt-template",
                ],
                "project_slug": "rag-research-brief-assistant",
                "deliverable": "Document one assistant workflow with explicit context assembly, guardrails, and failure handling.",
                "why_it_matters": "Most AI engineer interviews and projects assume this systems map, not just prompt familiarity.",
            },
            {
                "label": "Week 3: Ground answers with retrieval and evaluation",
                "status": "planned",
                "goal": "Learn how retrieval quality, ranking, and evaluation loops shape product trust.",
                "outcome": "You can debug a weak RAG answer by separating retrieval, prompting, and answer quality issues.",
                "path_slug": "rag-systems",
                "path_title": "RAG Systems",
                "lesson_slugs": [
                    "rag-systems-1",
                    "rag-systems-2",
                    "rag-systems-4",
                ],
                "exercise_slugs": [
                    "score-retrieval-candidates",
                    "compute-faithfulness-citation-coverage",
                ],
                "project_slug": "rag-research-brief-assistant",
                "deliverable": "Add one retrieval or evaluation improvement to a project and record what changed.",
                "why_it_matters": "Retrieval and evaluation are where many applied AI systems become real engineering work.",
            },
            {
                "label": "Week 4: Convert learning into visible proof",
                "status": "planned",
                "goal": "Use project evidence, system design language, and interview storytelling to turn study into hiring leverage.",
                "outcome": "You can point to at least one credible project story with architecture, metrics, tradeoffs, and next steps.",
                "path_slug": "ai-engineer-interview-readiness",
                "path_title": "AI Engineer Interview Readiness",
                "lesson_slugs": [
                    "ai-engineer-interview-readiness-1",
                    "ai-engineer-interview-readiness-2",
                    "ai-engineer-interview-readiness-5",
                ],
                "exercise_slugs": [],
                "project_slug": "evaluation-dashboard",
                "deliverable": "Turn one active project into an interview-ready write-up and talking track.",
                "why_it_matters": "This is where the portal becomes career leverage instead of just a study tracker.",
            },
        ],
    },
    {
        "title": "Practical LLM Engineer",
        "slug": "practical-llm-engineer",
        "description": "Ship focused LLM features with production awareness.",
        "difficulty": "intermediate",
        "estimated_hours": 22,
        "track_focus": "llm",
        "status": "active",
        "milestones_json": [
            {"label": "Map the end-to-end request lifecycle", "status": "planned"},
            {"label": "Design one narrow assistant with clear guardrails", "status": "planned"},
            {"label": "Instrument latency, failure, and review loops", "status": "planned"},
            {"label": "Document the tradeoffs like a product engineer", "status": "planned"},
        ],
    },
    {
        "title": "RAG Builder Track",
        "slug": "rag-builder-track",
        "description": "Design, evaluate, and improve retrieval workflows.",
        "difficulty": "intermediate",
        "estimated_hours": 20,
        "track_focus": "rag",
        "status": "active",
        "milestones_json": [
            {"label": "Choose chunking and metadata strategy", "status": "planned"},
            {"label": "Improve ranking and citations", "status": "planned"},
            {"label": "Measure retrieval and answer quality separately", "status": "planned"},
            {"label": "Turn one RAG build into portfolio proof", "status": "planned"},
        ],
    },
    {
        "title": "AI Agents Builder Track",
        "slug": "ai-agents-builder-track",
        "description": "Build tool-using systems with explicit control surfaces.",
        "difficulty": "intermediate",
        "estimated_hours": 18,
        "track_focus": "agents",
        "status": "active",
        "milestones_json": [
            {"label": "Decide when an agent is justified", "status": "planned"},
            {"label": "Model tools and state transitions explicitly", "status": "planned"},
            {"label": "Add approvals, retries, and traces", "status": "planned"},
            {"label": "Ship one auditable workflow artifact", "status": "planned"},
        ],
    },
    {
        "title": "MLOps for Software Engineers",
        "slug": "mlops-for-software-engineers",
        "description": "Apply software engineering discipline to AI delivery.",
        "difficulty": "advanced",
        "estimated_hours": 21,
        "track_focus": "mlops",
        "status": "active",
        "milestones_json": [
            {"label": "Choose the runtime shape", "status": "planned"},
            {"label": "Harden secrets and configuration boundaries", "status": "planned"},
            {"label": "Separate request work from background work", "status": "planned"},
            {"label": "Make a project deployable outside localhost", "status": "planned"},
        ],
    },
    {
        "title": "Interview Prep Track",
        "slug": "interview-prep-track",
        "description": "Convert learning and projects into interview-ready performance.",
        "difficulty": "intermediate",
        "estimated_hours": 12,
        "track_focus": "interview",
        "status": "active",
        "milestones_json": [
            {"label": "Clarify the transition narrative", "status": "planned"},
            {"label": "Practice AI system design tradeoffs", "status": "planned"},
            {"label": "Refresh Python and backend reps under pressure", "status": "planned"},
            {"label": "Turn projects into answer proof points", "status": "planned"},
        ],
    },
]

PATHS = [(path["title"], path["slug"], path["description"], path["level"], path["estimated_hours"]) for path in LEARNING_LIBRARY]

INITIAL_PROGRESS = {
    "date": date.today(),
    "learning_completion_pct": 0.0,
    "python_practice_count": 0,
    "projects_completed_count": 0,
    "interview_readiness_score": 0,
    "notes": "Fresh portal setup. No activity recorded yet.",
}


def build_lessons():
    lessons = []
    for path in LEARNING_LIBRARY:
        for order_index, lesson in enumerate(path["lessons"], start=1):
            lessons.append(
                {
                    "path_slug": path["slug"],
                    "title": lesson["title"],
                    "slug": "%s-%s" % (path["slug"], order_index),
                    "summary": lesson["summary"],
                    "content_md": lesson["content_md"],
                    "prerequisites_json": [] if order_index == 1 else ["%s-%s" % (path["slug"], order_index - 1)],
                    "estimated_minutes": lesson["estimated_minutes"],
                    "order_index": order_index,
                    "tags_json": [path["slug"], "phase-1", "portfolio"],
                }
            )
    return lessons


def build_courses():
    return [dict(course) for course in COURSES]


EXERCISES = [
    {
        "title": "Normalize provider payloads into a typed response model",
        "slug": "normalize-provider-payloads",
        "category": "python-refresh",
        "difficulty": "easy",
        "prompt_md": "Write a function that accepts a loose provider response and returns a normalized typed payload with explicit error handling.",
        "starter_code": "def normalize_response(payload):\n    # TODO: validate and normalize\n    raise NotImplementedError\n",
        "solution_code": "def normalize_response(payload):\n    return {'id': payload.get('id', 'missing'), 'content': payload.get('content', '').strip(), 'status': payload.get('status', 'ok')}\n",
        "explanation_md": "This mirrors real provider boundary work: normalize once, then keep the rest of the system simple.",
        "tags_json": ["python-refresh", "validation", "api-boundary"],
    },
    {
        "title": "Aggregate model latency metrics from JSONL traces",
        "slug": "aggregate-model-latency-metrics",
        "category": "data-transformation",
        "difficulty": "medium",
        "prompt_md": "Given a JSONL file of request traces, compute per-model latency averages, P95, and failure counts.",
        "starter_code": "def summarize_traces(lines):\n    # TODO: compute grouped metrics\n    raise NotImplementedError\n",
        "solution_code": "def summarize_traces(lines):\n    return {'gpt-4o-mini': {'count': len(lines), 'avg_ms': 120.0, 'p95_ms': 180.0, 'failures': 0}}\n",
        "explanation_md": "Operational analysis like this is common when tuning provider selection and retry policy.",
        "tags_json": ["data-transformation", "metrics", "observability"],
    },
    {
        "title": "Retry a provider call with timeout and backoff",
        "slug": "retry-provider-call-timeout-backoff",
        "category": "api-async",
        "difficulty": "medium",
        "prompt_md": "Implement an async wrapper that retries retryable provider failures with a timeout and bounded backoff.",
        "starter_code": "async def call_with_retry(client, request):\n    # TODO: add timeout and retry policy\n    raise NotImplementedError\n",
        "solution_code": "async def call_with_retry(client, request):\n    return await client(request)\n",
        "explanation_md": "Most AI API integrations fail operationally because timeout and retry policy are inconsistent rather than absent.",
        "tags_json": ["api-async", "retries", "provider-ops"],
    },
    {
        "title": "Render a safe prompt template from user input",
        "slug": "render-safe-prompt-template",
        "category": "prompt-formatting",
        "difficulty": "easy",
        "prompt_md": "Build a template renderer that separates trusted system instructions from untrusted user input and outputs a final prompt payload.",
        "starter_code": "def build_prompt(system_text, user_text, context_blocks):\n    # TODO: preserve boundaries\n    raise NotImplementedError\n",
        "solution_code": "def build_prompt(system_text, user_text, context_blocks):\n    return {'system': system_text, 'user': user_text, 'context': context_blocks}\n",
        "explanation_md": "Prompt construction should feel like request composition, not string interpolation chaos.",
        "tags_json": ["prompt-formatting", "prompting", "safety"],
    },
    {
        "title": "Score retrieval candidates with metadata boosts",
        "slug": "score-retrieval-candidates",
        "category": "retrieval",
        "difficulty": "medium",
        "prompt_md": "Combine vector similarity and metadata weighting into a final retrieval score for candidate chunks.",
        "starter_code": "def rank_candidates(candidates):\n    # TODO: compute blended score\n    raise NotImplementedError\n",
        "solution_code": "def rank_candidates(candidates):\n    return sorted(candidates, key=lambda item: item.get('score', 0), reverse=True)\n",
        "explanation_md": "Embeddings alone rarely capture all business relevance, so rank fusion is a practical skill.",
        "tags_json": ["retrieval", "ranking", "rag"],
    },
    {
        "title": "Compute faithfulness and citation coverage from judge results",
        "slug": "compute-faithfulness-citation-coverage",
        "category": "evaluation",
        "difficulty": "medium",
        "prompt_md": "Take evaluation outputs and summarize pass rate, faithfulness score, and citation coverage per prompt version.",
        "starter_code": "def summarize_eval(results):\n    # TODO: aggregate benchmark outputs\n    raise NotImplementedError\n",
        "solution_code": "def summarize_eval(results):\n    return {'baseline': {'pass_rate': 0.8, 'faithfulness': 0.82, 'citation_coverage': 0.9}}\n",
        "explanation_md": "Strong AI engineering distinguishes answer quality from grounding and traceability.",
        "tags_json": ["evaluation", "metrics", "faithfulness"],
    },
]

EXERCISE_DRILLS = [
    ("Parse JSONL benchmark rows into normalized records", "parse-jsonl-benchmark-rows", "python-refresh", "easy"),
    ("Summarize token usage by endpoint and model", "summarize-token-usage", "data-transformation", "easy"),
    ("Detect malformed retrieval chunks before indexing", "detect-malformed-retrieval-chunks", "retrieval", "medium"),
    ("Enforce provider timeout defaults from env config", "enforce-provider-timeout-defaults", "api-async", "medium"),
    ("Compute confusion matrix from classifier review logs", "compute-confusion-matrix-review-logs", "evaluation", "medium"),
    ("Build a slug generator for lesson and project records", "build-slug-generator", "python-refresh", "easy"),
    ("Validate article metadata before publish", "validate-article-metadata", "data-transformation", "easy"),
    ("Batch provider requests with concurrency limits", "batch-provider-requests-concurrency-limits", "api-async", "hard"),
    ("Merge keyword and vector retrieval results", "merge-keyword-vector-results", "retrieval", "medium"),
    ("Compare benchmark runs and highlight regressions", "compare-benchmark-runs-regressions", "evaluation", "medium"),
    ("Parse CLI args for an evaluation runner", "parse-cli-args-eval-runner", "python-refresh", "easy"),
    ("Group API errors into actionable retry buckets", "group-api-errors-retry-buckets", "data-transformation", "medium"),
    ("Build an async health check for provider adapters", "async-health-check-provider-adapters", "api-async", "medium"),
    ("Filter retrieval contexts by recency and source type", "filter-retrieval-contexts", "retrieval", "easy"),
    ("Score prompt variants by pass rate and cost", "score-prompt-variants", "evaluation", "medium"),
    ("Write a pathlib-based artifact export helper", "pathlib-artifact-export-helper", "python-refresh", "easy"),
    ("Clean scraped text before chunking", "clean-scraped-text-before-chunking", "data-transformation", "easy"),
    ("Throttle background ingestion tasks with backpressure", "throttle-background-ingestion", "api-async", "hard"),
    ("Assemble citation spans from retrieved snippets", "assemble-citation-spans", "retrieval", "hard"),
    ("Audit benchmark failures by category", "audit-benchmark-failures-category", "evaluation", "medium"),
    ("Map provider enums into internal response states", "map-provider-enums-response-states", "python-refresh", "easy"),
    ("Compute rolling latency stats for model routes", "compute-rolling-latency-stats", "data-transformation", "medium"),
    ("Retry only idempotent ingestion steps", "retry-idempotent-ingestion-steps", "api-async", "hard"),
    ("Rank support documents with freshness boosts", "rank-support-documents-freshness", "retrieval", "medium"),
    ("Build a review queue from low-confidence outputs", "build-review-queue-low-confidence", "evaluation", "medium"),
    ("Serialize experiment configs to reproducible snapshots", "serialize-experiment-configs", "python-refresh", "easy"),
    ("Prepare dashboard series from daily usage rows", "prepare-dashboard-series", "data-transformation", "easy"),
    ("Wrap streaming provider responses into stable chunks", "wrap-streaming-provider-responses", "api-async", "hard"),
    ("Deduplicate retrieval candidates across indexes", "deduplicate-retrieval-candidates", "retrieval", "medium"),
    ("Calculate judge agreement on evaluation labels", "calculate-judge-agreement", "evaluation", "hard"),
    ("Protect temp files during dataset generation", "protect-temp-files-dataset-generation", "python-refresh", "easy"),
    ("Reconcile mismatched event timestamps", "reconcile-mismatched-event-timestamps", "data-transformation", "medium"),
    ("Implement bounded polling for long-running jobs", "implement-bounded-polling", "api-async", "medium"),
    ("Expand metadata filters into SQL-ready conditions", "expand-metadata-filters-sql", "retrieval", "medium"),
]

for title, slug, category, difficulty in EXERCISE_DRILLS:
    EXERCISES.append(
        {
            "title": title,
            "slug": slug,
            "category": category,
            "difficulty": difficulty,
            "prompt_md": "Implement this task with explicit validation, predictable output shape, and enough error handling that it could survive reuse in a real AI workflow.",
            "starter_code": "def solve(payload):\n    # TODO: implement\n    raise NotImplementedError\n",
            "solution_code": "def solve(payload):\n    return payload\n",
            "explanation_md": "This drill reinforces production-minded habits: typed boundaries, debuggable transformation steps, and clear operational assumptions.",
            "tags_json": ["phase-1", "ai-engineering", category],
        }
    )


def build_exercises():
    return EXERCISES


KNOWLEDGE_ARTICLES = [
    {
        "title": "What makes a RAG system trustworthy",
        "slug": "what-makes-a-rag-system-trustworthy",
        "category": "architecture",
        "summary": "A practical framework for grounding, citations, retrieval transparency, and evaluation in RAG products.",
        "content_md": """## Trustworthy RAG

A RAG system becomes trustworthy when a user can tell where the answer came from, why those sources were selected, and what to do when the answer is weak.

Trust is not a feeling you add at the end. It is an architectural property created by:

- grounded evidence
- visible provenance
- retrieval transparency
- evaluation discipline
- honest failure handling

## The practical test

Ask these questions about any RAG feature:

1. Can the user inspect the source of a claim?
2. Can the team diagnose whether failure came from retrieval or generation?
3. Can weak answers be reviewed without guessing what context the model saw?

If the answer is no, the system may still look good in demos, but it will be hard to trust in repeated use.

## The four pillars

### 1. Grounded evidence

The answer should be tied to retrieved material that is actually relevant, not just attached as decorative citations after generation.

### 2. Provenance the user can follow

Users should be able to see:

- which document supported the answer
- where that document came from
- how recent it is

This matters even in internal tools. Provenance reduces overconfidence and shortens debugging loops.

### 3. Retrieval transparency for the team

Engineers should be able to inspect:

- top retrieved chunks
- their scores or ranking rationale
- metadata used in filtering
- what the prompt actually received

If retrieval traces are hidden, weak answers often get misdiagnosed as "prompt problems."

### 4. Evaluation loops that isolate failure modes

Evaluate at least three layers separately:

- retrieval quality
- answer faithfulness
- user task usefulness

One vague score is not enough. You want metrics that point to the next engineering move.

## A useful design rule

Build the system so a bad answer can be investigated in under five minutes.

That means the product should preserve:

- the user question
- retrieved context
- final answer
- supporting citations
- scoring or review notes

## Common anti-patterns

- citations added after the fact with no real grounding
- hidden retrieval traces
- mixing source snippets and generated synthesis without boundaries
- no benchmark set for repeated review
- assuming that "looked plausible" equals "worked"

## What strong trust looks like

A strong RAG system lets you say:

> We know what the model saw, why it saw it, how the answer used it, and how we judge whether that was good enough.

## Practical takeaway

When improving a RAG project, do not start with prompt tweaking. Start by making grounding, provenance, and evaluation easier to inspect.
""",
        "source_links_json": ["https://platform.openai.com/docs", "https://fastapi.tiangolo.com"],
        "tags_json": ["rag", "trust", "evaluation"],
    },
    {
        "title": "Chunking strategies for product-grade retrieval",
        "slug": "chunking-strategies-product-grade-retrieval",
        "category": "architecture",
        "summary": "Choose chunk sizes and boundaries to preserve meaning, support citations, and improve ranking.",
        "content_md": """## Chunking strategy

Chunking defines the unit your retrieval system can reason about. Good chunking preserves semantic coherence and provenance.

Poor chunking creates downstream problems that look like:

- irrelevant retrieval
- weak citations
- duplicated answers
- missing context

## What chunking is really doing

You are deciding:

- how much context belongs together
- what metadata travels with it
- what your retriever can later rank, filter, and cite

So chunking is not a preprocessing footnote. It is a product decision.

## What makes a good chunk

A good chunk:

- preserves one coherent idea
- carries useful provenance
- is large enough to answer a question
- is small enough to rank precisely

## Boundary choices that matter

Prefer natural boundaries when possible:

- headings
- section blocks
- paragraphs that stay on one topic
- structured records with meaningful fields

Avoid arbitrary slicing that breaks concepts mid-thought unless you also have a strong overlap strategy.

## Metadata is part of chunk design

A chunk without useful metadata is harder to trust later.

Useful metadata often includes:

- source identifier
- title or section name
- document date
- content type
- tags that matter for filtering

## Decision guide

Use smaller chunks when:

- precision matters more than breadth
- users ask targeted factual questions
- citation quality matters a lot

Use larger chunks when:

- context is highly interdependent
- users need broader synthesis
- the document structure would break if sliced too aggressively

## What to inspect in practice

If retrieval feels weak, inspect:

- top chunks for one real query
- whether the chunk boundaries preserved meaning
- whether adjacent chunks should have stayed together
- whether metadata could have filtered better candidates upward

## Common anti-patterns

- chunking only by character count
- forgetting metadata entirely
- keeping chunks so large that ranking becomes fuzzy
- keeping chunks so small that the model loses context

## Practical takeaway

Chunking should be reviewed the same way you review an API contract: does it preserve meaning, and does it support the later behaviors you care about?
""",
        "source_links_json": ["https://platform.openai.com/docs"],
        "tags_json": ["rag", "chunking", "retrieval"],
    },
    {
        "title": "A decision guide for prompting, RAG, and fine-tuning",
        "slug": "decision-guide-prompting-rag-fine-tuning",
        "category": "concept",
        "summary": "Pick the right technique based on knowledge freshness, control needs, and operational cost.",
        "content_md": """## Prompting vs RAG vs fine-tuning

Use prompting when behavior is the main variable, RAG when knowledge changes, and fine-tuning when output behavior itself must become more reliable.

This decision is easier when you stop asking "Which technique is most advanced?" and start asking:

- what is changing?
- what must stay controlled?
- what will be expensive to maintain?

## Prompting

Prompting is the best first move when:

- the model already knows enough
- the main need is better instructions or output structure
- the workflow is still evolving quickly

Use prompting for:

- formatting
- role framing
- output constraints
- lightweight behavioral steering

## RAG

RAG is the better move when:

- the needed knowledge is external or changing
- the answer must cite real source material
- you need to ground outputs in specific documents

Use RAG when freshness and provenance matter more than memorized behavior.

## Fine-tuning

Fine-tuning is worth considering when:

- the same behavior needs to become consistently stronger
- prompting alone is too brittle
- retrieval will not solve the problem because the issue is output behavior rather than missing knowledge

It is not the first answer to every weak AI feature.

## Decision table

Choose prompting when:

- instructions are the main issue
- you want maximum iteration speed

Choose RAG when:

- knowledge changes often
- citation and grounding matter

Choose fine-tuning when:

- output behavior itself needs to change
- you have enough examples to justify the maintenance cost

## Common mistakes

- using RAG to solve a pure formatting problem
- trying to fine-tune around missing external knowledge
- endlessly prompt-tuning when the real issue is retrieval quality

## Practical takeaway

The best choice is the one that isolates the real failure mode with the least long-term complexity.
""",
        "source_links_json": ["https://platform.openai.com/docs"],
        "tags_json": ["prompting", "rag", "fine-tuning"],
    },
    {
        "title": "Evaluation metrics that actually help iteration",
        "slug": "evaluation-metrics-help-iteration",
        "category": "concept",
        "summary": "Use metrics that point to specific failure modes rather than one vague quality score.",
        "content_md": """## Useful evaluation metrics

Separate retrieval quality, answer faithfulness, latency, cost, and user task success so metrics guide your next engineering move.

The test for a useful metric is simple:

If this gets worse, do I know what kind of investigation or fix to start with?

If not, the metric may be decorative rather than operational.

## The categories that usually matter

### Retrieval quality

Ask whether the system found the right evidence.

### Answer faithfulness

Ask whether the answer stayed supported by the evidence it was given.

### Latency

Ask whether the feature remains usable in the product context.

### Cost

Ask whether the architecture is sustainable under real usage.

### User-task usefulness

Ask whether the feature helped the user complete the intended job.

## Why one score fails

A single composite score hides too much:

- a system can be fast and wrong
- accurate but too slow
- grounded but unhelpful

Breaking metrics apart gives you engineering leverage.

## What to do with a metric

Every metric should support one of these actions:

- investigate
- compare versions
- trigger review
- prioritize work

If it cannot do any of those, question whether it belongs on the dashboard.

## Good metric design habits

- keep benchmark sets small and trusted at first
- annotate important edge cases
- pair scores with notes when qualitative failure matters
- review regressions on a schedule

## Practical takeaway

Use metrics that narrow the search space of failure instead of creating the illusion of certainty.
""",
        "source_links_json": ["https://platform.openai.com/docs"],
        "tags_json": ["evaluation", "metrics", "observability"],
    },
    {
        "title": "Observability for AI requests",
        "slug": "observability-for-ai-requests",
        "category": "architecture",
        "summary": "Trace context assembly, provider calls, outputs, and failures so AI bugs become debuggable engineering work.",
        "content_md": """## AI observability

For a single request, you should be able to inspect the input, retrieved context, provider response, post-processing result, latency, and cost.

Without that, AI failures turn into anecdotes:

- "the model was weird"
- "retrieval felt off"
- "it timed out somehow"

Observability turns those guesses into engineering work.

## Minimum trace shape

For one request, capture:

- request identifier
- user input or task type
- retrieved context or documents
- model/provider used
- output produced
- latency
- token or cost estimate
- failure or review notes

## What this enables

Good traces let you answer:

- Did retrieval fail?
- Did the wrong model/config get used?
- Did post-processing break a good response?
- Are latency spikes tied to one dependency?

## Trace by layer

For AI systems, observability usually needs to span:

- context assembly
- provider call
- post-processing
- persistence or review handoff

If you only log the final answer, you lose the most valuable debugging information.

## Anti-patterns

- logging too little to diagnose failures
- logging everything with no structure
- having traces that humans cannot actually review

## Practical takeaway

An AI trace should help you explain both what happened and what to try next.
""",
        "source_links_json": ["https://fastapi.tiangolo.com"],
        "tags_json": ["observability", "tracing", "production"],
    },
    {
        "title": "Provider wrappers should be boring",
        "slug": "provider-wrappers-should-be-boring",
        "category": "concept",
        "summary": "A good provider wrapper normalizes responses, centralizes retries, and makes the rest of your system simpler.",
        "content_md": """## Provider wrappers

Keep authentication, timeout, retries, and normalized outputs at the edge so the rest of your code stays stable as vendors change.

The wrapper should not be where your product logic lives. It should be where vendor weirdness stops.

## What a wrapper should do

- accept stable internal inputs
- translate them to vendor-specific requests
- normalize vendor-specific responses
- centralize timeout and retry policy
- expose consistent errors back to the application layer

## What a wrapper should not do

- decide product behavior
- own orchestration logic
- leak vendor-specific shapes deep into your codebase

## Why boring is good

If wrappers stay boring:

- provider swaps are easier
- tests stay clearer
- application services can depend on stable contracts

## Practical takeaway

The wrapper’s job is to make the rest of the system forget which SDK sits at the edge.
""",
        "source_links_json": ["https://platform.openai.com/docs"],
        "tags_json": ["providers", "apis", "architecture"],
    },
]

ARTICLE_NOTES = [
    ("Prompt templates should behave like contracts", "prompt-templates-behave-like-contracts", "concept", "Treat prompts as explicit interfaces with versioning, variable boundaries, and review criteria rather than magic strings."),
    ("Retrieval metadata is a product decision", "retrieval-metadata-product-decision", "architecture", "Metadata design decides what the system can later filter, cite, and explain back to the user."),
    ("Why evaluation sets should start small", "evaluation-sets-should-start-small", "concept", "A curated, trusted benchmark set beats a larger but noisy dataset when you are still learning what failure looks like."),
    ("How to think about provider lock-in", "how-to-think-provider-lock-in", "concept", "Provider portability matters most at the boundary layer where schemas, retries, and cost controls are centralized."),
    ("Citations are a UX feature, not a footnote", "citations-are-a-ux-feature", "architecture", "Citations help the user calibrate trust, inspect weak answers, and continue research rather than starting over."),
    ("Human review is part of the system", "human-review-is-part-of-the-system", "concept", "Human checkpoints are a strength when confidence is low or business impact is high."),
    ("Latency budgets shape product design", "latency-budgets-shape-product-design", "architecture", "Perceived speed depends on retrieval, provider calls, streaming behavior, and how the UI acknowledges work in progress."),
    ("Why many agent demos fail in production", "why-agent-demos-fail-production", "concept", "Open-ended loops hide state, cost, and failure reasons unless you add explicit boundaries and observability."),
    ("A practical schema for AI request traces", "practical-schema-ai-request-traces", "architecture", "Store enough detail to debug context, prompts, outputs, latency, and cost without overwhelming yourself."),
    ("Use benchmark regressions to drive weekly work", "use-benchmark-regressions-weekly-work", "concept", "Weekly iteration improves when regressions produce concrete follow-up tasks instead of generic worry."),
    ("Deployment readiness for LLM features", "deployment-readiness-llm-features", "architecture", "Production readiness means secrets, retries, caching, tracing, and rollback plans are all intentional."),
    ("When to persist generated artifacts", "when-to-persist-generated-artifacts", "concept", "Persist prompts, contexts, scores, and outputs when they help review, replay, or explain product behavior."),
    ("Debug retrieval before changing prompts", "debug-retrieval-before-changing-prompts", "architecture", "Weak answers often come from bad context selection, so inspect retrieval traces before rewriting prompts."),
    ("What a strong AI project write-up includes", "strong-ai-project-writeup", "concept", "A strong write-up explains the problem, architecture, tradeoffs, evaluation method, and what you would improve next."),
    ("Choosing between sync APIs and background jobs", "choosing-sync-apis-vs-background-jobs", "architecture", "Move heavy ingestion and evaluation work off the request path once latency or reliability starts to matter."),
    ("Personal knowledge bases need freshness rules", "personal-knowledge-bases-need-freshness-rules", "concept", "Every content library should say what is stable, what expires, and what gets reviewed on a schedule."),
    ("How to review an AI feature after launch", "how-to-review-ai-feature-after-launch", "architecture", "Post-launch review should inspect traces, evaluation drift, user pain points, and operational cost together."),
    ("A portfolio roadmap for the AI engineer transition", "portfolio-roadmap-ai-engineer-transition", "concept", "Pair learning paths with portfolio artifacts so each month produces visible proof, not just study notes."),
    ("Failure modes worth logging explicitly", "failure-modes-worth-logging-explicitly", "architecture", "Log missing context, schema mismatches, provider failures, judge disagreement, and human override reasons."),
    ("Use learning systems to support real projects", "use-learning-systems-support-real-projects", "concept", "The portal should feed execution: learn, apply, review, and convert the result into portfolio evidence."),
    ("A clean handoff between ingestion and retrieval", "clean-handoff-ingestion-retrieval", "architecture", "The indexing layer should emit chunks and metadata in a form the retrieval layer can trust without guesswork."),
    ("Interview prep should mirror shipped work", "interview-prep-should-mirror-shipped-work", "concept", "The best prep material points back to projects, metrics, and tradeoffs you actually worked through."),
    ("Prompt evaluation needs qualitative notes too", "prompt-evaluation-needs-qualitative-notes", "concept", "Scores alone miss tone, structure, and user trust; keep notes that explain why a version won or failed."),
    ("Design your portal like a product, not a notebook", "design-your-portal-like-a-product", "architecture", "Treat content structure, navigation, and progress loops as product decisions that should reduce friction over time."),
]

for title, slug, category, summary in ARTICLE_NOTES:
    KNOWLEDGE_ARTICLES.append(
        {
            "title": title,
            "slug": slug,
            "category": category,
            "summary": summary,
            "content_md": "## %s\n\n%s\n\n### Practical takeaway\n\nCapture the decision this note supports, then connect it to a project, evaluation loop, or deployment choice so the idea stays operational." % (title, summary),
            "source_links_json": ["https://platform.openai.com/docs"],
            "tags_json": ["phase-1", "reference", category],
        }
    )


def build_articles():
    return KNOWLEDGE_ARTICLES


PROJECTS = [
    {
        "title": "RAG Research Brief Assistant",
        "slug": "rag-research-brief-assistant",
        "summary": "A retrieval app that turns domain documents into concise briefings with traceable sources.",
        "status": "active",
        "category": "rag-app",
        "stack_json": ["Next.js", "FastAPI", "PostgreSQL", "vector-search"],
        "architecture_md": """## Project goal
Turn a noisy domain corpus into briefings a user can trust, with citations they can inspect and evaluation traces the team can debug.

## Core workflow
- ingest source documents with stable document ids and metadata
- chunk content based on how the user will actually ask questions
- retrieve top evidence with filters for source type and freshness
- assemble a prompt that keeps source snippets and synthesis clearly separated
- return an answer with citations, confidence notes, and retrieval traces

## Architecture decisions
### Ingestion boundary
Keep parsing, cleaning, and metadata extraction in a dedicated ingestion step so retrieval quality can be improved without touching the answer layer.

### Retrieval boundary
Treat retrieval as its own subsystem with benchmark queries, top-k inspection, and ranking review instead of hiding it behind one helper call.

### Answer boundary
The answer renderer should only use retrieved evidence plus a narrow instruction set. This reduces "citation-shaped hallucinations."

## Evaluation plan
- benchmark retrieval quality with a small labeled query set
- review whether cited chunks really support the answer
- compare answer usefulness, not just lexical overlap

## Interview proof
If you demo this project well, you can explain chunking, retrieval debugging, citation design, and why trust in RAG is mostly an engineering problem, not a prompting trick.
""",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": """## What this project should teach you
- retrieval quality fails silently unless you inspect chunks directly
- citation UX matters because users judge trust through provenance
- benchmark queries keep iteration grounded when demos look deceptively good

## What to say in interviews
> The biggest improvement did not come from adding more model complexity. It came from tightening chunking, metadata, and retrieval review loops.

## Next improvement
Add side-by-side evaluation runs so you can compare prompt, retrieval, and answer changes without guessing which change actually helped.
""",
        "portfolio_score": 82,
    },
    {
        "title": "Agent Workflow Orchestrator",
        "slug": "agent-workflow-orchestrator",
        "summary": "A controlled multi-step workflow runner with tool calls, retries, and human approval checkpoints.",
        "status": "planned",
        "category": "agent-system",
        "stack_json": ["Python", "FastAPI", "Redis", "workflow-engine"],
        "architecture_md": """## Project goal
Build an agent-like workflow that stays auditable, interruptible, and safe under production pressure.

## Core workflow
- represent each task as an explicit state transition
- persist run state after each step
- route tool calls through a narrow adapter layer
- require approval before external side effects
- log retries, dead ends, and stop conditions

## Architecture decisions
### State machine over hidden recursion
The system should make each step visible so you can replay and inspect why a run moved forward, retried, or stopped.

### Tool boundaries
Every tool call should have structured inputs, outputs, and failure reasons. This keeps the orchestration layer boring and debuggable.

### Human review points
Insert approval gates before sending messages, mutating records, or calling expensive external systems.

## Evaluation plan
- success rate by workflow type
- average retries before completion
- stop-reason distribution
- human override frequency

## Interview proof
This project lets you talk about when agents add value, where deterministic workflows are safer, and how you would keep autonomy from becoming hidden chaos.
""",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": """## What this project should teach you
- agent systems need explicit control flow, not magical loops
- tool use becomes safer when every transition is inspectable
- approvals are a product feature, not just a compliance afterthought

## What to say in interviews
Frame this as a reliability project: the challenge is not just making the workflow powerful, but making it traceable, interruptible, and easy to debug.

## Next improvement
Add run replay and a visual timeline so you can demonstrate how the orchestrator behaves on good runs and failure cases.
""",
        "portfolio_score": 74,
    },
    {
        "title": "Evaluation Dashboard",
        "slug": "evaluation-dashboard",
        "summary": "Track prompt, retrieval, and answer quality using benchmark datasets and run comparisons.",
        "status": "active",
        "category": "eval-tooling",
        "stack_json": ["Next.js", "FastAPI", "Recharts"],
        "architecture_md": """## Project goal
Make model and retrieval iteration measurable so the team can see regressions before users do.

## Core workflow
- define benchmark cases with stable inputs and expected review dimensions
- store each evaluation run with model, prompt, retrieval settings, and timestamps
- compare runs side by side across quality, latency, and cost
- surface regressions visually with links back to the exact failing cases

## Architecture decisions
### Reproducibility first
Every run should preserve the exact inputs and configuration needed to replay the result later.

### Layered metrics
Track retrieval quality, answer quality, latency, and cost separately so one blended number does not hide the real failure mode.

### Review loop
The dashboard should support both automated metrics and human review notes. Useful evaluation mixes both.

## Interview proof
This project is strong evidence that you understand evaluation as an engineering system rather than an after-the-fact charting exercise.
""",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": """## What this project should teach you
- good metrics isolate a failure mode instead of decorating a dashboard
- reproducibility matters more than a large number of vanity charts
- evaluation should decide the next experiment, not summarize the last one

## What to say in interviews
> Measurement should shape iteration cadence, not trail it.

## Next improvement
Add diff views for prompt and retrieval changes so you can connect metric movement to a concrete engineering decision.
""",
        "portfolio_score": 88,
    },
]

INTERVIEW_QUESTIONS = [
    {
        "category": "python",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "How would you structure a Python service that wraps an LLM provider and remains testable as providers change?",
        "answer_outline_md": """## Strong answer shape
Start with the boundary: your application code should depend on an internal provider interface, not directly on vendor SDK objects.

## What to cover
- normalize request and response models with explicit schemas
- isolate retries, timeouts, and backoff in the adapter layer
- keep prompts and business logic outside the provider client
- make provider calls easy to stub in tests

## Concrete example
Say you would expose one internal method like `generate_text(request)` and keep OpenAI-, Anthropic-, or local-model details behind that contract.

## Interview takeaway
The theme is boring boundaries. Good AI backends survive provider changes because only a thin adapter knows vendor-specific details.
""",
        "tags_json": ["python", "backend", "providers"],
    },
    {
        "category": "rag",
        "role_type": "llm-engineer",
        "difficulty": "advanced",
        "question_text": "A RAG system works well in demos but produces weak answers in production. How do you debug it systematically?",
        "answer_outline_md": """## Strong answer shape
Break the pipeline into ingestion, chunking, retrieval, prompt assembly, and answer evaluation. Then isolate one layer at a time.

## What to cover
- inspect whether the right documents entered the corpus
- review chunk boundaries and metadata quality
- inspect top retrieved chunks for benchmark queries
- compare what the model saw against the final answer
- separate retrieval failure from generation failure

## Good interviewer signal
Mention that you want trace data and a small benchmark set before you start tweaking prompts blindly.

## Interview takeaway
The point is disciplined diagnosis. Production RAG debugging is mostly about making hidden layers inspectable.
""",
        "tags_json": ["rag", "debugging", "evaluation"],
    },
    {
        "category": "evaluation",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "What metrics would you put on an AI observability dashboard for a production feature?",
        "answer_outline_md": """## Strong answer shape
Explain that one score is never enough. Separate model quality, system reliability, and business usefulness.

## What to cover
- answer quality or task success
- faithfulness or groundedness when retrieval is involved
- latency and timeout rate
- token cost and cost per successful task
- provider failure rate and fallback usage
- human review or user correction signals

## Good interviewer signal
Say that useful metrics should point to the next engineering move, not just decorate a dashboard.

## Interview takeaway
Strong candidates think in layers: quality, reliability, and cost should be visible independently.
""",
        "tags_json": ["evaluation", "observability", "production"],
    },
    {
        "category": "agents",
        "role_type": "applied-ai-engineer",
        "difficulty": "advanced",
        "question_text": "When does an agent architecture add value, and when is it just complexity?",
        "answer_outline_md": """## Strong answer shape
Open with the tradeoff: agents add value when the system must choose tools or sequence steps dynamically under uncertainty.

## What to cover
- use agents when the task path is not known in advance
- keep workflows deterministic when the happy path is stable
- measure whether flexibility improves outcomes enough to justify lower predictability
- keep tool calls auditable and stop conditions explicit

## Concrete example
An internal research assistant may need dynamic retrieval and tool choice. A billing workflow usually does not.

## Interview takeaway
The strongest answer is not "agents are powerful." It is "agents are expensive complexity, so I use them only when the task truly demands it."
""",
        "tags_json": ["agents", "architecture", "tradeoffs"],
    },
    {
        "category": "system-design",
        "role_type": "ai-engineer",
        "difficulty": "advanced",
        "question_text": "Design a personal AI learning portal that can grow from one private user to a multi-user SaaS later.",
        "answer_outline_md": """## Strong answer shape
Start with domain boundaries: content, user activity, recommendations, and external signals should be separate from auth and tenancy concerns.

## What to cover
- durable content storage for lessons, practice, knowledge, and projects
- user activity tables for completions, attempts, saved signals, and interview reps
- recommendation services that read activity instead of hard-coding user assumptions
- deployment boundaries so frontend, backend, and persistence can scale independently later
- how auth and tenant scoping can be layered in without rewriting the content model

## Good interviewer signal
Mention that designing for future SaaS does not mean premature microservices. It means keeping clean boundaries now.

## Interview takeaway
This answer should sound like product-minded architecture: start simple, preserve seams, and avoid future rewrites.
""",
        "tags_json": ["system-design", "product", "scalability"],
    },
    {
        "category": "behavioral",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "How do you explain your transition from full-stack software engineering into AI engineering without sounding like you are starting over?",
        "answer_outline_md": """## Strong answer shape
Frame the move as a continuation of engineering strengths, not a reset.

## What to cover
- product delivery and stakeholder alignment already transfer
- backend design and API discipline still matter in AI systems
- the new layer is handling probabilistic behavior, evaluation, and model-driven workflows
- show proof through projects, practice, and market-aware learning

## A clean narrative
You are not leaving software engineering. You are applying strong product and systems fundamentals to a new technical surface with different failure modes.

## Interview takeaway
The goal is calm credibility: you already know how to ship complex systems, and now you are building proof that those strengths extend into AI engineering.
""",
        "tags_json": ["behavioral", "career-transition", "narrative"],
    },
]

INTERVIEW_PROMPTS = [
    ("python", "ai-engineer", "beginner", "What Python patterns matter most when moving from web product work into AI engineering?", "Focus on data modeling, serialization, scripts, async IO, and debugging speed instead of only algorithm trivia."),
    ("backend", "ai-engineer", "intermediate", "How would you design a backend boundary between product logic and provider-specific SDK calls?", "Keep provider adapters narrow, normalize payloads, and let application services depend on stable internal schemas."),
    ("llm-systems", "ai-engineer", "intermediate", "How do prompt, retrieval, tools, and memory interact in an LLM application?", "Explain them as distinct control surfaces, then show how poor boundaries create bugs or hidden coupling."),
    ("deployment", "ai-engineer", "advanced", "What changes when an AI feature moves from a demo to a real deployment?", "Cover retries, latency budgets, secrets, tracing, benchmark regressions, and human review where confidence is weak."),
    ("rag", "llm-engineer", "advanced", "How do you choose chunking and metadata strategies for a new retrieval corpus?", "Tie chunk design to user questions, citation needs, ranking signals, and future filtering requirements."),
    ("evaluation", "ai-engineer", "intermediate", "What makes an evaluation metric useful instead of decorative?", "Useful metrics isolate a failure mode and point toward a specific next experiment or engineering fix."),
    ("agents", "applied-ai-engineer", "advanced", "How would you keep an agent workflow auditable?", "Use explicit states, structured tool calls, stop conditions, logs, and approval points for risky actions."),
    ("system-design", "ai-engineer", "advanced", "Design an internal assistant for a company knowledge base.", "Discuss ingestion, retrieval, authorization, citations, evaluation, and how feedback improves the system over time."),
    ("behavioral", "ai-engineer", "intermediate", "Tell me about a time you shipped an ambiguous product requirement.", "Show how you created structure, aligned stakeholders, measured success, and adapted when reality changed."),
    ("python", "llm-engineer", "intermediate", "How would you structure evaluation scripts so they are rerunnable and trustworthy?", "Emphasize stable inputs, explicit outputs, logging, CLI args, and artifact persistence."),
    ("backend", "applied-ai-engineer", "intermediate", "How do you decide whether to persist intermediate AI artifacts?", "Persist what helps replay, review, compare versions, and explain outcomes later."),
    ("deployment", "llm-engineer", "advanced", "What belongs in an AI service health check?", "Probe dependencies, provider reachability, configuration sanity, queue lag, and any signals tied to degraded user experience."),
    ("rag", "ai-engineer", "intermediate", "What is the difference between retrieval quality and answer quality?", "Retrieval quality asks whether the right evidence was found; answer quality asks whether the final response used that evidence well."),
    ("evaluation", "applied-ai-engineer", "advanced", "How would you debug disagreement between an automated judge and a human reviewer?", "Inspect rubric ambiguity, low-quality context, edge cases, and whether the judge prompt tracks the real product goal."),
    ("agents", "ai-engineer", "intermediate", "When should a workflow stay deterministic instead of becoming agentic?", "Keep it deterministic when steps are known, reliability matters more than flexibility, and tool choices are stable."),
    ("system-design", "applied-ai-engineer", "advanced", "How would you evolve a private single-user learning portal into a multi-user SaaS?", "Separate content, user activity, and recommendation logic now so auth and tenancy can be layered in later."),
    ("behavioral", "llm-engineer", "intermediate", "How do you talk about an AI feature that failed its first production trial?", "Focus on diagnosis quality, iteration discipline, and how the failure improved the system."),
    ("python", "ai-engineer", "beginner", "How do you explain the role of Pydantic in an AI backend?", "Use it at boundaries to validate inputs and outputs while keeping the middle of the system simpler."),
]

for category, role_type, difficulty, question_text, outline in INTERVIEW_PROMPTS:
    INTERVIEW_QUESTIONS.append(
        {
            "category": category,
            "role_type": role_type,
            "difficulty": difficulty,
            "question_text": question_text,
            "answer_outline_md": outline,
            "tags_json": ["phase-1", "interview", category],
        }
    )


def build_interview_questions():
    return INTERVIEW_QUESTIONS


NEWS_ITEMS = [
    {
        "source_name": "OpenAI",
        "title": "Model releases and platform updates to review this week",
        "slug": "openai-model-releases-platform-updates",
        "summary": "Track changes in model capability, pricing, and API ergonomics that could change how you build or evaluate AI features.",
        "source_url": "https://platform.openai.com/docs/overview",
        "category": "model-release",
        "signal_score": 92,
        "tags_json": ["models", "platforms", "llm-apps"],
    },
    {
        "source_name": "Anthropic",
        "title": "Agent and tool-use patterns worth monitoring",
        "slug": "anthropic-agent-tool-use-patterns",
        "summary": "Watch for patterns that shift how production teams think about tool invocation, guardrails, and long-running workflows.",
        "source_url": "https://www.anthropic.com/news",
        "category": "agents",
        "signal_score": 88,
        "tags_json": ["agents", "tools", "production"],
    },
    {
        "source_name": "Hugging Face",
        "title": "Open-source stack momentum for applied AI engineers",
        "slug": "hugging-face-open-source-stack-momentum",
        "summary": "Follow the frameworks and model-serving tools gaining traction so your project choices stay grounded in ecosystem reality.",
        "source_url": "https://huggingface.co/blog",
        "category": "open-source",
        "signal_score": 84,
        "tags_json": ["open-source", "serving", "tooling"],
    },
    {
        "source_name": "MLOps Community",
        "title": "Evaluation and observability themes showing up across teams",
        "slug": "mlops-community-evaluation-observability-themes",
        "summary": "Collect the recurring patterns around eval datasets, traces, and review workflows that strong AI teams keep returning to.",
        "source_url": "https://home.mlops.community/",
        "category": "evaluation",
        "signal_score": 79,
        "tags_json": ["evaluation", "observability", "mlops"],
    },
]


JOB_POSTINGS = [
    {
        "source_name": "Seeded Watchlist",
        "title": "AI Engineer",
        "slug": "seeded-watchlist-ai-engineer",
        "company_name": "Frontier Systems Co.",
        "location": "Remote",
        "employment_type": "full-time",
        "summary": "Own LLM-backed product features, API integrations, and evaluation loops across a customer-facing platform.",
        "source_url": "https://example.com/jobs/ai-engineer",
        "description_md": "Build retrieval-backed features, provider integrations, dashboards, and deployment workflows with strong product ownership.",
        "tags_json": ["ai-engineer", "rag", "evaluation", "fastapi", "nextjs"],
    },
    {
        "source_name": "Seeded Watchlist",
        "title": "Applied AI Engineer",
        "slug": "seeded-watchlist-applied-ai-engineer",
        "company_name": "Workflow Intelligence Labs",
        "location": "US Remote",
        "employment_type": "full-time",
        "summary": "Ship agent-shaped product workflows, build prompt and tool abstractions, and harden them with observability.",
        "source_url": "https://example.com/jobs/applied-ai-engineer",
        "description_md": "Looking for engineers with backend ownership, product sense, Python fluency, and experience turning prototypes into production systems.",
        "tags_json": ["applied-ai", "agents", "python", "product-engineering"],
    },
    {
        "source_name": "Seeded Watchlist",
        "title": "LLM Platform Engineer",
        "slug": "seeded-watchlist-llm-platform-engineer",
        "company_name": "Inference Platform Group",
        "location": "Hybrid",
        "employment_type": "full-time",
        "summary": "Design the platform layer around model providers, evaluation runs, trace collection, and deployment safety.",
        "source_url": "https://example.com/jobs/llm-platform-engineer",
        "description_md": "Best fit for engineers who enjoy abstractions, reliability, observability, and multi-service deployment architecture.",
        "tags_json": ["platform", "providers", "observability", "deployment"],
    },
]
