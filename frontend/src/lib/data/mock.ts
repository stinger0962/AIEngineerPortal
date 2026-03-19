import type {
  Course,
  DashboardSummary,
  DashboardToday,
  Exercise,
  ExerciseDetail,
  InterviewQuestion,
  InterviewRoadmap,
  KnowledgeArticle,
  LearningPath,
  Project,
  Recommendation,
} from "@/lib/types/portal";

export const mockDashboard: DashboardSummary = {
  user_name: "Alex Builder",
  headline: "Use the portal to turn your full-stack leverage into visible AI engineering momentum.",
  learning_streak: 5,
  stats: [
    { label: "Learning completion", value: "18%", tone: "primary" },
    { label: "Practice attempts", value: "6", tone: "secondary" },
    { label: "Interview readiness", value: "42/100", tone: "accent" },
  ],
  next_lesson: {
    id: 1,
    title: "Python for AI Engineers: Core workflow",
    slug: "python-for-ai-engineers-2",
    summary: "Map the day-to-day implementation flow with concrete API and data boundaries.",
  },
  recommended_exercise: {
    id: 1,
    title: "Python Refresh Drill 1",
    category: "python-refresh",
    difficulty: "easy",
  },
  active_projects: [
    { id: 1, title: "Evaluation Dashboard", status: "active", portfolio_score: 88 },
    { id: 2, title: "RAG Research Brief Assistant", status: "active", portfolio_score: 82 },
  ],
  recommendation_panel: [
    { title: "Close the Python fluency gap", reason: "Daily repetition still offers the fastest compounding return." },
    { title: "Keep a project moving", reason: "A live portfolio artifact helps every other learning stream stick." },
  ],
};

export const mockToday: DashboardToday = {
  focus: ["Complete one lesson", "Submit one exercise attempt", "Update one project note"],
  highlights: ["Your React/product instincts are an advantage.", "RAG and evaluation remain your highest-value focus areas."],
  blockers: ["Python speed under pressure", "Turning theory into reusable implementation patterns"],
};

export const mockPaths: LearningPath[] = [
  {
    id: 1,
    title: "Python for AI Engineers",
    slug: "python-for-ai-engineers",
    description: "Refresh Python fluency with an AI engineering lens.",
    level: "beginner",
    estimated_hours: 14,
    order_index: 1,
    is_active: true,
    tags_json: ["python", "phase-1"],
    completion_pct: 20,
    lessons: [
      {
        id: 1,
        learning_path_id: 1,
        title: "Python for AI Engineers: Mental model",
        slug: "python-for-ai-engineers-1",
        summary: "Connect Python fluency to AI engineering workflows.",
        content_md: "## Mental model\n\nBuild Python instincts that help you ship services and pipelines.",
        prerequisites_json: [],
        estimated_minutes: 35,
        order_index: 1,
        tags_json: ["python"],
        is_completed: true,
      },
      {
        id: 2,
        learning_path_id: 1,
        title: "Python for AI Engineers: Core workflow",
        slug: "python-for-ai-engineers-2",
        summary: "Map the implementation flow.",
        content_md: "## Core workflow\n\nTranslate Python fundamentals into service architecture.",
        prerequisites_json: ["python-for-ai-engineers-1"],
        estimated_minutes: 40,
        order_index: 2,
        tags_json: ["python"],
        is_completed: false,
      },
    ],
  },
];

export const mockCourses: Course[] = [
  {
    id: 1,
    title: "AI Engineer Foundations",
    slug: "ai-engineer-foundations",
    description: "A guided transition track that turns software engineering strength into visible AI engineering proof.",
    difficulty: "beginner",
    estimated_hours: 18,
    milestones_json: [
      {
        label: "Week 1: Build Python execution confidence",
        status: "active",
        goal: "Learn the runtime habits, boundary modeling, and async instincts that applied AI work depends on.",
        outcome: "You can explain and implement safer provider boundaries, cleaner scripts, and rerunnable Python workflows.",
        path_slug: "python-for-ai-engineers",
        path_title: "Python for AI Engineers",
        lesson_slugs: ["python-for-ai-engineers-1", "python-for-ai-engineers-2", "python-for-ai-engineers-3"],
        exercise_slugs: ["normalize-provider-payloads", "retry-provider-call-timeout-backoff"],
        project_slug: "evaluation-dashboard",
        deliverable: "Refactor one project boundary or utility into a typed, rerunnable Python module.",
        why_it_matters: "This is the fastest way to stop feeling like Python is the bottleneck in AI work.",
      },
      {
        label: "Week 2: Understand the LLM application shape",
        status: "planned",
        goal: "Learn how prompt, context, tools, memory, latency, and guardrails interact in a real product feature.",
        outcome: "You can map the request lifecycle of an LLM feature and explain the major tradeoffs clearly.",
        path_slug: "llm-app-foundations",
        path_title: "LLM App Foundations",
        lesson_slugs: ["llm-app-foundations-1", "llm-app-foundations-2", "llm-app-foundations-3"],
        exercise_slugs: ["render-safe-prompt-template"],
        project_slug: "rag-research-brief-assistant",
        deliverable: "Document one assistant workflow with explicit context assembly, guardrails, and failure handling.",
        why_it_matters: "Most AI engineer interviews and projects assume this systems map, not just prompt familiarity.",
      },
    ],
    status: "active",
    track_focus: "foundations",
  },
];

export const mockExercises: Exercise[] = [
  {
    id: 1,
    title: "Python Refresh Drill 1",
    slug: "python-refresh-1",
    category: "python-refresh",
    difficulty: "easy",
    prompt_md: "Implement a tiny utility with explicit validation.",
    starter_code: "def solve(payload):\n    return payload\n",
    solution_code: "def solve(payload):\n    return payload\n",
    explanation_md: "Prefer small pure functions.",
    tags_json: ["python-refresh"],
  },
];

export const mockExerciseDetail: ExerciseDetail = {
  exercise: mockExercises[0],
  attempts: [],
};

export const mockArticles: KnowledgeArticle[] = [
  {
    id: 1,
    title: "What is RAG",
    slug: "what-is-rag",
    category: "concept",
    summary: "A practical note on retrieval-augmented generation for applied AI engineering.",
    content_md: "## What is RAG\n\nUse retrieval to ground a model with trustworthy context.",
    source_links_json: ["https://platform.openai.com/docs"],
    tags_json: ["rag"],
    last_reviewed_at: new Date().toISOString(),
  },
];

export const mockProjects: Project[] = [
  {
    id: 1,
    title: "Evaluation Dashboard",
    slug: "evaluation-dashboard",
    summary: "Track prompt and retrieval quality over time.",
    status: "active",
    category: "eval-tooling",
    stack_json: ["Next.js", "FastAPI", "Recharts"],
    architecture_md: "Store runs, compare metrics, and review regressions.",
    repo_url: null,
    demo_url: null,
    lessons_learned_md: "Measurement should shape iteration cadence.",
    portfolio_score: 88,
  },
];

export const mockInterviewQuestions: InterviewQuestion[] = [
  {
    id: 1,
    category: "python",
    role_type: "ai-engineer",
    difficulty: "intermediate",
    question_text: "How would you structure a Python service that wraps an LLM provider and remains testable?",
    answer_outline_md: "Clarify interface boundaries, test seams, retries, and observability.",
    tags_json: ["python", "ai-engineer"],
    practice_count: 0,
    last_practiced_at: null,
    average_confidence: null,
  },
];

export const mockInterviewRoadmap: InterviewRoadmap = {
  focus_areas: ["Python fluency", "LLM systems", "RAG debugging", "Behavioral transition story"],
  weekly_plan: ["Monday practice", "Wednesday mock system design", "Friday review and refine"],
  rationale: ["Project proof and interview readiness should reinforce each other."],
};

export const mockRecommendations: Recommendation[] = [
  {
    title: "Advance the next learning milestone",
    reason: "Keep lesson completion moving while project work is active.",
    action_path: "/learn/lesson/python-for-ai-engineers-2",
    source_kind: "learning",
  },
];
