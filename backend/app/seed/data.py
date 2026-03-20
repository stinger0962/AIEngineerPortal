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
            {"title": "When not to use an agent", "summary": "Compare fixed workflows to open-ended orchestration.", "content_md": "## Agent caution\n\nMany problems are better solved with deterministic flows plus a model in the right place.", "estimated_minutes": 35},
            {"title": "Tool definitions and execution boundaries", "summary": "Design tool interfaces the model can use reliably.", "content_md": "## Tools\n\nSimple, well-typed tools reduce ambiguity and make debugging easier.", "estimated_minutes": 40},
            {"title": "State machines over vague loops", "summary": "Model multi-step behavior with explicit states and stop conditions.", "content_md": "## State\n\nControl improves when transitions are named and observable.", "estimated_minutes": 40},
            {"title": "Guardrails, approvals, and retries", "summary": "Protect external actions and manage failure paths deliberately.", "content_md": "## Controls\n\nRisk increases sharply when models can trigger real-world side effects.", "estimated_minutes": 35},
            {"title": "Portfolio slice: workflow orchestrator", "summary": "Build an agent-shaped system that still feels engineered.", "content_md": "## Portfolio move\n\nShow auditability, traceability, and approval points.", "estimated_minutes": 35},
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
        "architecture_md": "Ingest domain documents, chunk them with metadata, retrieve grounded context, render sourced answers, and record evaluation traces.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "The quality of chunking and retrieval evaluation matters more than adding more orchestration.",
        "portfolio_score": 82,
    },
    {
        "title": "Agent Workflow Orchestrator",
        "slug": "agent-workflow-orchestrator",
        "summary": "A controlled multi-step workflow runner with tool calls, retries, and human approval checkpoints.",
        "status": "planned",
        "category": "agent-system",
        "stack_json": ["Python", "FastAPI", "Redis", "workflow-engine"],
        "architecture_md": "Represent each step as an explicit state transition, capture tool invocations, and require approvals for external side effects.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "",
        "portfolio_score": 74,
    },
    {
        "title": "Evaluation Dashboard",
        "slug": "evaluation-dashboard",
        "summary": "Track prompt, retrieval, and answer quality using benchmark datasets and run comparisons.",
        "status": "active",
        "category": "eval-tooling",
        "stack_json": ["Next.js", "FastAPI", "Recharts"],
        "architecture_md": "Store evaluation runs, compare metrics across versions, and surface regressions visually with reproducible inputs.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "Measurement should shape iteration cadence, not trail it.",
        "portfolio_score": 88,
    },
]

INTERVIEW_QUESTIONS = [
    {
        "category": "python",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "How would you structure a Python service that wraps an LLM provider and remains testable as providers change?",
        "answer_outline_md": "Clarify provider boundaries, normalize request and response models, centralize retries and timeouts, and keep business logic independent from vendor-specific SDK details.",
        "tags_json": ["python", "backend", "providers"],
    },
    {
        "category": "rag",
        "role_type": "llm-engineer",
        "difficulty": "advanced",
        "question_text": "A RAG system works well in demos but produces weak answers in production. How do you debug it systematically?",
        "answer_outline_md": "Split the problem into ingestion, chunking, ranking, prompt assembly, and answer evaluation. Use trace data and benchmark queries to isolate the weakest layer before changing the whole pipeline.",
        "tags_json": ["rag", "debugging", "evaluation"],
    },
    {
        "category": "evaluation",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "What metrics would you put on an AI observability dashboard for a production feature?",
        "answer_outline_md": "Include answer quality, faithfulness, latency, token cost, provider failure rate, and any user-task completion signal available.",
        "tags_json": ["evaluation", "observability", "production"],
    },
    {
        "category": "agents",
        "role_type": "applied-ai-engineer",
        "difficulty": "advanced",
        "question_text": "When does an agent architecture add value, and when is it just complexity?",
        "answer_outline_md": "Use agents when a task genuinely needs dynamic sequencing or tool selection. Prefer deterministic workflows when the happy path is known and reliability is the priority.",
        "tags_json": ["agents", "architecture", "tradeoffs"],
    },
    {
        "category": "system-design",
        "role_type": "ai-engineer",
        "difficulty": "advanced",
        "question_text": "Design a personal AI learning portal that can grow from one private user to a multi-user SaaS later.",
        "answer_outline_md": "Explain domain boundaries, content persistence, personalization, deployment model, and how auth and multi-tenancy could be layered in without rewriting core modules.",
        "tags_json": ["system-design", "product", "scalability"],
    },
    {
        "category": "behavioral",
        "role_type": "ai-engineer",
        "difficulty": "intermediate",
        "question_text": "How do you explain your transition from full-stack software engineering into AI engineering without sounding like you are starting over?",
        "answer_outline_md": "Frame it as an expansion of strengths: product delivery, systems thinking, API design, and ownership now applied to model-powered systems and evaluation-heavy workflows.",
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
