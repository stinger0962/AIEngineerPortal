import {
  mockArticles,
  mockCourses,
  mockDashboard,
  mockExerciseDetail,
  mockExercises,
  mockInterviewQuestions,
  mockInterviewRoadmap,
  mockMemoryCards,
  mockPaths,
  mockProjects,
  mockRecommendations,
  mockToday,
} from "@/lib/data/mock";
import type {
  AdaptiveFocus,
  AIFeedbackResponse,
  Course,
  DashboardSummary,
  DashboardToday,
  Exercise,
  ExerciseAttempt,
  ExerciseDetail,
  ExerciseVariation,
  FeedRefreshMeta,
  InterviewPractice,
  InterviewQuestion,
  InterviewRoadmap,
  JobFitAnalysis,
  JobPosting,
  KnowledgeArticle,
  LearningPath,
  MasteryArea,
  MemoryCard,
  MemoryCardReview,
  NewsItem,
  PinnedExercise,
  PortfolioReadiness,
  Project,
  Recommendation,
  SkillGapInsight,
  VariationType,
} from "@/lib/types/portal";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const allowMockFallback = process.env.NODE_ENV !== "production";

async function fetchJson<T>(path: string, init?: RequestInit, fallback?: T): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (allowMockFallback && fallback !== undefined) {
      return fallback;
    }
    throw error;
  }
}

export const portalApi = {
  getDashboardSummary: () => fetchJson<DashboardSummary>("/dashboard/summary", undefined, mockDashboard),
  getDashboardToday: () => fetchJson<DashboardToday>("/dashboard/today", undefined, mockToday),
  getLearningPaths: () => fetchJson<LearningPath[]>("/learning/paths", undefined, mockPaths),
  getPathBySlug: async (slug: string) => {
    const paths = await portalApi.getLearningPaths();
    return paths.find((path) => path.slug === slug) ?? null;
  },
  getLesson: async (slug: string) => {
    const paths = await portalApi.getLearningPaths();
    const lesson = paths.flatMap((path) => path.lessons).find((item) => item.slug === slug);
    if (lesson) {
      return lesson;
    }
    return fetchJson(`/learning/lessons/${slug}`, undefined, mockPaths[0]?.lessons[0] ?? null);
  },
  completeLesson: (lessonId: number) =>
    fetchJson(`/learning/lessons/${lessonId}/complete`, { method: "POST" }, { completed: true, learning_completion_pct: 20, lesson_id: lessonId }),
  getCourses: () => fetchJson<Course[]>("/courses", undefined, mockCourses),
  getCourse: async (slug: string) => {
    const courses = await portalApi.getCourses();
    return courses.find((course) => course.slug === slug) ?? null;
  },
  getExercises: () => fetchJson<Exercise[]>("/exercises", undefined, mockExercises),
  getExercise: (id: number) => fetchJson<ExerciseDetail>(`/exercises/${id}`, undefined, mockExerciseDetail),
  submitAttempt: (exerciseId: number, submitted_code: string, notes: string) =>
    fetchJson<ExerciseAttempt>(
      `/exercises/${exerciseId}/attempt`,
      {
        method: "POST",
        body: JSON.stringify({ submitted_code, notes }),
      },
      {
        id: Date.now(),
        exercise_id: exerciseId,
        submitted_code,
        notes,
        status: "completed",
        score: 88,
        attempted_at: new Date().toISOString(),
      },
    ),
  getKnowledgeArticles: () => fetchJson<KnowledgeArticle[]>("/knowledge", undefined, mockArticles),
  getKnowledgeArticle: async (slug: string) => {
    const articles = await portalApi.getKnowledgeArticles();
    return articles.find((article) => article.slug === slug) ?? null;
  },
  getNewsItems: () => fetchJson<NewsItem[]>("/news"),
  getNewsMeta: () => fetchJson<FeedRefreshMeta>("/news/meta"),
  refreshNews: () => fetchJson<NewsItem[]>("/news/refresh", { method: "POST" }),
  saveNewsItem: (newsId: number) => fetchJson<NewsItem>(`/news/${newsId}/save`, { method: "POST" }),
  getJobs: () => fetchJson<JobPosting[]>("/jobs"),
  getJobsMeta: () => fetchJson<FeedRefreshMeta>("/jobs/meta"),
  getJob: (jobId: number) => fetchJson<JobPosting>(`/jobs/${jobId}`),
  refreshJobs: () => fetchJson<JobPosting[]>("/jobs/refresh", { method: "POST" }),
  saveJob: (jobId: number) => fetchJson<JobPosting>(`/jobs/${jobId}/save`, { method: "POST" }),
  analyzeJobFit: (jobId: number) => fetchJson<JobFitAnalysis>(`/jobs/${jobId}/analyze-fit`, { method: "POST" }),
  getProjects: () => fetchJson<Project[]>("/projects", undefined, mockProjects),
  getProject: async (slug: string) => {
    const projects = await portalApi.getProjects();
    return projects.find((project) => project.slug === slug) ?? null;
  },
  createProject: (payload: Omit<Project, "id" | "slug"> & { title: string }) =>
    fetchJson<Project>(
      "/projects",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      {
        id: Date.now(),
        slug: payload.title.toLowerCase().replace(/\s+/g, "-"),
        ...payload,
      },
    ),
  updateProject: (projectId: number, payload: Omit<Project, "id" | "slug"> & { title: string }) =>
    fetchJson<Project>(
      `/projects/${projectId}`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
      {
        id: projectId,
        slug: payload.title.toLowerCase().replace(/\s+/g, "-"),
        ...payload,
      },
    ),
  getInterviewQuestions: () => fetchJson<InterviewQuestion[]>("/interview/questions", undefined, mockInterviewQuestions),
  getInterviewRoadmap: () => fetchJson<InterviewRoadmap>("/interview/roadmap", undefined, mockInterviewRoadmap),
  getPortfolioReadiness: () => fetchJson<PortfolioReadiness>("/interview/portfolio-readiness"),
  getInterviewSkillGaps: () => fetchJson<SkillGapInsight[]>("/interview/skill-gaps"),
  getMasteryProfile: () => fetchJson<MasteryArea[]>("/adaptive/mastery"),
  getAdaptiveFocus: () => fetchJson<AdaptiveFocus | null>("/adaptive/focus"),
  practiceInterviewQuestion: (questionId: number, confidence_score: number, notes: string) =>
    fetchJson<InterviewPractice>(
      `/interview/questions/${questionId}/practice`,
      {
        method: "POST",
        body: JSON.stringify({ confidence_score, notes }),
      },
      {
        question_id: questionId,
        practice_count: 1,
        last_practiced_at: new Date().toISOString(),
        average_confidence: confidence_score,
      },
    ),
  getRecommendations: () => fetchJson<Recommendation[]>("/recommendations/next-actions", undefined, mockRecommendations),

  getMemoryCards: () => fetchJson<MemoryCard[]>("/memory/cards", undefined, mockMemoryCards),
  reviewMemoryCard: (cardId: number, confidence: number) =>
    fetchJson<MemoryCardReview>(
      `/memory/cards/${cardId}/review`,
      {
        method: "POST",
        body: JSON.stringify({ confidence }),
      },
      {
        card_id: cardId,
        confidence,
        reviewed_at: new Date().toISOString(),
      },
    ),
  async submitForAIFeedback(exerciseId: number, code: string, referenceSolution?: string): Promise<AIFeedbackResponse> {
    const body: Record<string, string> = { code };
    if (referenceSolution) {
      body.reference_solution = referenceSolution;
    }
    const res = await fetch(
      `${API_BASE}/exercises/${exerciseId}/ai-feedback`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "AI feedback unavailable" }));
      throw new Error(err.detail || `AI feedback failed (${res.status})`);
    }
    return res.json();
  },

  async generateVariation(exerciseId: number, variationType: VariationType = "scenario"): Promise<ExerciseVariation> {
    const res = await fetch(
      `${API_BASE}/exercises/${exerciseId}/variation?variation_type=${variationType}`,
      { method: "POST" }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Variation generation failed" }));
      throw new Error(err.detail || `Generation failed (${res.status})`);
    }
    return res.json();
  },

  async pinVariation(exerciseId: number, variation: ExerciseVariation): Promise<PinnedExercise> {
    const res = await fetch(
      `${API_BASE}/exercises/${exerciseId}/variation/pin`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: variation.title,
          prompt_md: variation.prompt_md,
          starter_code: variation.starter_code,
          solution_code: variation.solution_code,
          explanation_md: variation.explanation_md,
          variation_type: variation.variation_type,
        }),
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Pin failed" }));
      throw new Error(err.detail || `Pin failed (${res.status})`);
    }
    return res.json();
  },
};
