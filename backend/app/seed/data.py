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

PATHS = [
    ("Python for AI Engineers", "python-for-ai-engineers", "Refresh Python fluency with an AI engineering lens.", "beginner", 14),
    ("LLM App Foundations", "llm-app-foundations", "Understand the primitives behind practical LLM products.", "intermediate", 16),
    ("RAG Systems", "rag-systems", "Build retrieval systems that ship, evaluate, and improve.", "intermediate", 18),
    ("AI Agents and Tools", "ai-agents-and-tools", "Work through orchestration, tool use, and task design.", "intermediate", 14),
    ("Evaluation and Observability", "evaluation-and-observability", "Measure quality before adding complexity.", "intermediate", 12),
    ("AI Deployment and MLOps", "ai-deployment-and-mlops", "Move from prototype to durable operations.", "advanced", 18),
    ("AI Engineer Interview Readiness", "ai-engineer-interview-readiness", "Translate experience into interview-ready stories.", "intermediate", 10),
]

LESSON_BLUEPRINTS = [
    ("Mental model", "Build the conceptual frame for this topic and identify where your existing engineering skills transfer."),
    ("Core workflow", "Map the day-to-day implementation flow with concrete API, data, and system boundaries."),
    ("Hands-on pattern", "Study a practical implementation pattern you can reuse in portfolio projects."),
    ("Failure modes", "Review tradeoffs, common mistakes, and production pitfalls."),
    ("Portfolio move", "Turn the topic into a portfolio artifact and interview story."),
]

COURSES = [
    ("AI Engineer Foundations", "ai-engineer-foundations", "A broad practical transition track from senior SWE to AI engineer.", "beginner", 24, "foundations"),
    ("Practical LLM Engineer", "practical-llm-engineer", "Ship LLM experiences with confidence and production awareness.", "intermediate", 22, "llm"),
    ("RAG Builder Track", "rag-builder-track", "Design, evaluate, and improve retrieval workflows.", "intermediate", 20, "rag"),
    ("AI Agents Builder Track", "ai-agents-builder-track", "Learn tool-calling, orchestration, and agent control surfaces.", "intermediate", 18, "agents"),
    ("MLOps for Software Engineers", "mlops-for-software-engineers", "Apply software engineering discipline to AI platform delivery.", "advanced", 21, "mlops"),
    ("Interview Prep Track", "interview-prep-track", "Prepare for AI engineer interviews with focused repetition.", "intermediate", 12, "interview"),
]

EXERCISE_CATEGORIES = [
    "python-refresh",
    "data-transformation",
    "api-async",
    "prompt-formatting",
    "embeddings",
    "retrieval",
    "evaluation",
    "system-design-coding",
]

KNOWLEDGE_TOPICS = [
    "What is RAG",
    "Chunking strategies",
    "Embedding model selection",
    "Vector database tradeoffs",
    "Prompt template design",
    "Tool calling basics",
    "Agent loop guardrails",
    "Evaluation metrics",
    "Hallucination containment",
    "Model routing",
    "Caching LLM responses",
    "Tracing and observability",
    "Human-in-the-loop review",
    "Serving architecture",
    "Inference cost control",
    "Fine-tuning vs prompting vs RAG",
    "DSPy overview",
    "LangGraph overview",
    "LangChain tradeoffs",
    "LlamaIndex use cases",
    "OpenAI platform notes",
    "Anthropic comparison",
    "Open source serving",
    "Prompt safety basics",
    "Synthetic evaluation sets",
    "Retrieval failure analysis",
    "Experiment tracking",
    "AI system design interviews",
    "Portfolio storytelling",
    "Deployment runbooks",
    "Data quality checks",
    "Latency budgeting",
]

PROJECTS = [
    {
        "title": "RAG Research Brief Assistant",
        "slug": "rag-research-brief-assistant",
        "summary": "A retrieval app that turns domain documents into concise briefings.",
        "status": "active",
        "category": "rag-app",
        "stack_json": ["Next.js", "FastAPI", "PostgreSQL", "vector-search"],
        "architecture_md": "Ingest documents, chunk them, retrieve grounded context, and render sourced answers.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "Focus on retrieval quality before adding agent complexity.",
        "portfolio_score": 82,
    },
    {
        "title": "Agent Workflow Orchestrator",
        "slug": "agent-workflow-orchestrator",
        "summary": "A multi-step task runner with tool calls, retries, and audit trails.",
        "status": "planned",
        "category": "agent-system",
        "stack_json": ["Python", "FastAPI", "Redis", "workflow-engine"],
        "architecture_md": "Model each agent step as a deterministic state transition with observability hooks.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "",
        "portfolio_score": 74,
    },
    {
        "title": "Evaluation Dashboard",
        "slug": "evaluation-dashboard",
        "summary": "Track prompt, retrieval, and answer quality using benchmark datasets.",
        "status": "active",
        "category": "eval-tooling",
        "stack_json": ["Next.js", "FastAPI", "Recharts"],
        "architecture_md": "Store runs, compare metrics, and surface regression hotspots visually.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "Measurement should shape iteration cadence.",
        "portfolio_score": 88,
    },
    {
        "title": "Multimodal Document Intake",
        "slug": "multimodal-document-intake",
        "summary": "Extract entities and summaries from mixed-format enterprise documents.",
        "status": "planned",
        "category": "multimodal",
        "stack_json": ["Python", "OCR", "LLM", "FastAPI"],
        "architecture_md": "Normalize inputs, extract structure, and map outputs to downstream workflows.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "",
        "portfolio_score": 70,
    },
    {
        "title": "AI Productivity Copilot",
        "slug": "ai-productivity-copilot",
        "summary": "A focused productivity assistant for planning and execution.",
        "status": "backlog",
        "category": "assistant",
        "stack_json": ["Next.js", "FastAPI", "OpenAI"],
        "architecture_md": "Use narrow workflows and explicit context windows for reliable outcomes.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "",
        "portfolio_score": 67,
    },
    {
        "title": "Industry Analysis Generator",
        "slug": "industry-analysis-generator",
        "summary": "Generate market briefs and compare tooling ecosystems by vertical.",
        "status": "planned",
        "category": "analysis",
        "stack_json": ["Python", "FastAPI", "search", "dashboard"],
        "architecture_md": "Blend curated inputs with structured synthesis templates and review controls.",
        "repo_url": None,
        "demo_url": None,
        "lessons_learned_md": "",
        "portfolio_score": 76,
    },
]

INTERVIEW_PROMPTS = [
    ("python", "ai-engineer", "intermediate", "How would you structure a Python service that wraps an LLM provider and remains testable?"),
    ("backend", "ai-engineer", "advanced", "Design a scalable job for evaluating nightly prompt regressions across multiple datasets."),
    ("llm-systems", "llm-engineer", "intermediate", "When would you choose RAG over fine-tuning for a product feature?"),
    ("rag", "ai-engineer", "advanced", "How do you debug a retrieval system that appears correct in demos but fails in production?"),
    ("agents", "ai-engineer", "advanced", "What controls would you add before letting an agent call external tools?"),
    ("evaluation", "ai-engineer", "intermediate", "How do you define success for an AI feature with subjective outputs?"),
    ("deployment", "ml-engineer", "advanced", "Walk through deploying a latency-sensitive inference service."),
    ("behavioral", "ai-engineer", "intermediate", "How do you explain your transition from full-stack engineering into AI engineering?"),
    ("system-design", "ai-engineer", "advanced", "Design an AI knowledge portal for a single-user workflow with future multi-user expansion."),
    ("product", "ai-product-engineer", "intermediate", "How do you decide whether an AI feature should be fully automated or approval-driven?"),
    ("python", "ai-engineer", "beginner", "What Python features do you rely on most when building clean AI services?"),
    ("backend", "applied-ai-engineer", "intermediate", "How would you expose model inference through a versioned API?"),
    ("llm-systems", "llm-engineer", "intermediate", "How do context windows influence chunking and prompt strategy?"),
    ("rag", "llm-engineer", "intermediate", "Which retrieval metrics matter when answers need citations?"),
    ("agents", "applied-ai-engineer", "intermediate", "Where do agent loops most often go wrong in enterprise use cases?"),
    ("evaluation", "ai-engineer", "advanced", "How would you build a benchmark suite for answer faithfulness?"),
    ("deployment", "ai-engineer", "intermediate", "What signals tell you a model-serving architecture needs caching?"),
    ("behavioral", "ai-engineer", "intermediate", "Describe a time you navigated an ambiguous technical frontier."),
    ("system-design", "ai-engineer", "advanced", "Design a portfolio-ready AI project that highlights production quality."),
    ("product", "developer-experience-ai", "intermediate", "How would you design developer onboarding around an LLM platform?"),
    ("python", "ai-engineer", "intermediate", "How do dataclasses and Pydantic serve different roles in backend design?"),
    ("backend", "ml-engineer", "intermediate", "How would you persist experiment metadata alongside production usage data?"),
    ("evaluation", "ai-engineer", "intermediate", "What would you put on an AI observability dashboard?"),
    ("behavioral", "ai-engineer", "beginner", "Why does your full-stack background make you effective in applied AI roles?"),
]


def build_lessons() -> list[dict]:
    lessons: list[dict] = []
    for title, slug, _description, _level, _hours in PATHS:
        for order_index, (suffix, summary) in enumerate(LESSON_BLUEPRINTS, start=1):
            lessons.append(
                {
                    "path_slug": slug,
                    "title": f"{title}: {suffix}",
                    "slug": f"{slug}-{order_index}",
                    "summary": summary,
                    "content_md": (
                        f"## {title} - {suffix}\n\n"
                        "Connect this topic to a senior software engineering mindset.\n\n"
                        "### Outcome\n"
                        "- understand the implementation shape\n"
                        "- connect it to portfolio work\n"
                        "- extract an interview-ready story\n\n"
                        "### Practice prompt\n"
                        "Write down the API, data model, observability checkpoints, and failure cases."
                    ),
                    "prerequisites_json": [] if order_index == 1 else [f"{slug}-{order_index - 1}"],
                    "estimated_minutes": 35 + (order_index * 5),
                    "order_index": order_index,
                    "tags_json": [slug, "portfolio", "interview"],
                }
            )
    return lessons


def build_courses() -> list[dict]:
    courses: list[dict] = []
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
                    {"label": "Understand the landscape", "status": "complete"},
                    {"label": "Ship a practical feature", "status": "in-progress"},
                    {"label": "Document tradeoffs and metrics", "status": "planned"},
                    {"label": "Convert into interview stories", "status": "planned"},
                ],
                "status": "active",
            }
        )
    return courses


def build_exercises() -> list[dict]:
    exercises: list[dict] = []
    difficulty_cycle = ["easy", "medium", "hard"]
    for index in range(48):
        category = EXERCISE_CATEGORIES[index % len(EXERCISE_CATEGORIES)]
        difficulty = difficulty_cycle[index % len(difficulty_cycle)]
        number = index + 1
        exercises.append(
            {
                "title": f"{category.replace('-', ' ').title()} Drill {number}",
                "slug": f"{category}-{number}",
                "category": category,
                "difficulty": difficulty,
                "prompt_md": (
                    f"Implement a solution for **{category}** that reflects a real AI engineering workflow.\n\n"
                    "Focus on readability, typed outputs, and failure handling."
                ),
                "starter_code": "def solve(payload):\n    # TODO: implement\n    return payload\n",
                "solution_code": "def solve(payload):\n    return payload\n",
                "explanation_md": "Prefer small pure functions, explicit validation, and debug-friendly outputs.",
                "tags_json": [category, difficulty, "ai-engineering"],
            }
        )
    return exercises


def build_articles() -> list[dict]:
    articles: list[dict] = []
    for index, topic in enumerate(KNOWLEDGE_TOPICS, start=1):
        articles.append(
            {
                "title": topic,
                "slug": topic.lower().replace(" ", "-"),
                "category": "concept" if index % 2 else "architecture",
                "summary": f"A practical note on {topic.lower()} for applied AI engineering.",
                "content_md": (
                    f"## {topic}\n\n"
                    "This note explains why the topic matters, what tradeoffs show up in production, and how to "
                    "turn the concept into a portfolio-grade implementation decision."
                ),
                "source_links_json": ["https://platform.openai.com/docs", "https://fastapi.tiangolo.com"],
                "tags_json": ["ai", "engineering", topic.split(" ")[0].lower()],
            }
        )
    return articles


def build_interview_questions() -> list[dict]:
    return [
        {
            "category": category,
            "role_type": role_type,
            "difficulty": difficulty,
            "question_text": question_text,
            "answer_outline_md": (
                "1. Clarify the problem.\n"
                "2. Explain tradeoffs and system boundaries.\n"
                "3. Connect to production reliability.\n"
                "4. Close with how you would measure success."
            ),
            "tags_json": [category, difficulty, role_type],
        }
        for category, role_type, difficulty, question_text in INTERVIEW_PROMPTS
    ]


INITIAL_PROGRESS = {
    "date": date.today(),
    "learning_completion_pct": 0.0,
    "python_practice_count": 0,
    "projects_completed_count": 0,
    "interview_readiness_score": 0,
    "notes": "Fresh portal setup. No activity recorded yet.",
}
