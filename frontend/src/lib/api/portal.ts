import {
  mockArticles,
  mockCourses,
  mockDashboard,
  mockExerciseDetail,
  mockExercises,
  mockInterviewQuestions,
  mockInterviewRoadmap,
  mockPaths,
  mockProjects,
  mockRecommendations,
  mockToday,
} from "@/lib/data/mock";
import type {
  Course,
  DashboardSummary,
  DashboardToday,
  Exercise,
  ExerciseAttempt,
  ExerciseDetail,
  InterviewQuestion,
  InterviewRoadmap,
  JobFitAnalysis,
  JobPosting,
  KnowledgeArticle,
  LearningPath,
  NewsItem,
  Project,
  Recommendation,
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
  refreshNews: () => fetchJson<NewsItem[]>("/news/refresh", { method: "POST" }),
  saveNewsItem: (newsId: number) => fetchJson<NewsItem>(`/news/${newsId}/save`, { method: "POST" }),
  getJobs: () => fetchJson<JobPosting[]>("/jobs"),
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
  getRecommendations: () => fetchJson<Recommendation[]>("/recommendations/next-actions", undefined, mockRecommendations),
};
