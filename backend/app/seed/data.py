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
        "estimated_hours": 14,
        "lessons": [
            {
                "title": "Python runtime habits that matter in AI work",
                "summary": "Focus on data modeling, IO boundaries, debugging, and iteration speed rather than syntax memorization.",
                "content_md": "## Why this path starts with Python\n\nFor an experienced full-stack engineer, the real gap is speed under pressure across APIs, scripts, provider SDKs, and evaluation loops.\n\n### Optimize for\n- readable control flow\n- explicit inputs and outputs\n- lightweight validation\n- fast debugging\n- safe serialization",
                "estimated_minutes": 35,
            },
            {
                "title": "Modeling data with dicts, dataclasses, and Pydantic",
                "summary": "Use strict validation at boundaries and keep the middle of the system simple.",
                "content_md": "## Data modeling choices\n\nAI systems move semi-structured data around constantly.\n\n### Use dicts for exploration\n### Use dataclasses for internal domain objects\n### Use Pydantic for API and persistence boundaries",
                "estimated_minutes": 40,
            },
            {
                "title": "Async IO for provider calls and ingestion work",
                "summary": "Use async where network waiting dominates and make timeout and retry behavior explicit.",
                "content_md": "## Async patterns that pay off\n\nUse async for provider calls, multi-document fetches, retrieval fan-out, and background tasks. Avoid mixing sync and async blindly.",
                "estimated_minutes": 45,
            },
            {
                "title": "File handling, serialization, and safe evaluation scripts",
                "summary": "Write scripts you can trust repeatedly for dataset prep, prompt experiments, and benchmark runs.",
                "content_md": "## Script quality matters\n\nFavor pathlib, JSONL, idempotent scripts, stable output locations, and explicit command arguments.",
                "estimated_minutes": 40,
            },
            {
                "title": "Turning Python fluency into portfolio leverage",
                "summary": "Use Python skills to make every project more credible through APIs, tooling, and repeatability.",
                "content_md": "## Portfolio move\n\nShow a clean API surface, typed schemas, evaluation utilities, deployable runtime shape, and debugging-friendly logs.",
                "estimated_minutes": 35,
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
    ("AI Engineer Foundations", "ai-engineer-foundations", "A practical transition track from senior software engineer to AI engineer.", "beginner", 24, "foundations"),
    ("Practical LLM Engineer", "practical-llm-engineer", "Ship focused LLM features with production awareness.", "intermediate", 22, "llm"),
    ("RAG Builder Track", "rag-builder-track", "Design, evaluate, and improve retrieval workflows.", "intermediate", 20, "rag"),
    ("AI Agents Builder Track", "ai-agents-builder-track", "Build tool-using systems with explicit control surfaces.", "intermediate", 18, "agents"),
    ("MLOps for Software Engineers", "mlops-for-software-engineers", "Apply software engineering discipline to AI delivery.", "advanced", 21, "mlops"),
    ("Interview Prep Track", "interview-prep-track", "Convert learning and projects into interview-ready performance.", "intermediate", 12, "interview"),
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
    courses = []
    for title, slug, description, difficulty, estimated_hours, track_focus in COURSES:
        courses.append(
            {
                "title": title,
                "slug": slug,
                "description": description,
                "difficulty": difficulty,
                "estimated_hours": estimated_hours,
                "track_focus": track_focus,
                "milestones_json": [
                    {"label": "Build conceptual map", "status": "planned"},
                    {"label": "Ship one practical module", "status": "planned"},
                    {"label": "Document tradeoffs and metrics", "status": "planned"},
                    {"label": "Convert into interview stories", "status": "planned"},
                ],
                "status": "active",
            }
        )
    return courses


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
        "content_md": "## Trustworthy RAG\n\nA RAG system becomes trustworthy when a user can tell where the answer came from, why those sources were selected, and what to do when the answer is weak.",
        "source_links_json": ["https://platform.openai.com/docs", "https://fastapi.tiangolo.com"],
        "tags_json": ["rag", "trust", "evaluation"],
    },
    {
        "title": "Chunking strategies for product-grade retrieval",
        "slug": "chunking-strategies-product-grade-retrieval",
        "category": "architecture",
        "summary": "Choose chunk sizes and boundaries to preserve meaning, support citations, and improve ranking.",
        "content_md": "## Chunking strategy\n\nChunking defines the unit your retrieval system can reason about. Good chunking preserves semantic coherence and provenance.",
        "source_links_json": ["https://platform.openai.com/docs"],
        "tags_json": ["rag", "chunking", "retrieval"],
    },
    {
        "title": "A decision guide for prompting, RAG, and fine-tuning",
        "slug": "decision-guide-prompting-rag-fine-tuning",
        "category": "concept",
        "summary": "Pick the right technique based on knowledge freshness, control needs, and operational cost.",
        "content_md": "## Prompting vs RAG vs fine-tuning\n\nUse prompting when behavior is the main variable, RAG when knowledge changes, and fine-tuning when output behavior itself must become more reliable.",
        "source_links_json": ["https://platform.openai.com/docs"],
        "tags_json": ["prompting", "rag", "fine-tuning"],
    },
    {
        "title": "Evaluation metrics that actually help iteration",
        "slug": "evaluation-metrics-help-iteration",
        "category": "concept",
        "summary": "Use metrics that point to specific failure modes rather than one vague quality score.",
        "content_md": "## Useful evaluation metrics\n\nSeparate retrieval quality, answer faithfulness, latency, cost, and user task success so metrics guide your next engineering move.",
        "source_links_json": ["https://platform.openai.com/docs"],
        "tags_json": ["evaluation", "metrics", "observability"],
    },
    {
        "title": "Observability for AI requests",
        "slug": "observability-for-ai-requests",
        "category": "architecture",
        "summary": "Trace context assembly, provider calls, outputs, and failures so AI bugs become debuggable engineering work.",
        "content_md": "## AI observability\n\nFor a single request, you should be able to inspect the input, retrieved context, provider response, post-processing result, latency, and cost.",
        "source_links_json": ["https://fastapi.tiangolo.com"],
        "tags_json": ["observability", "tracing", "production"],
    },
    {
        "title": "Provider wrappers should be boring",
        "slug": "provider-wrappers-should-be-boring",
        "category": "concept",
        "summary": "A good provider wrapper normalizes responses, centralizes retries, and makes the rest of your system simpler.",
        "content_md": "## Provider wrappers\n\nKeep authentication, timeout, retries, and normalized outputs at the edge so the rest of your code stays stable as vendors change.",
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
