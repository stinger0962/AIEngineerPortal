export type DashboardSummary = {
  user_name: string;
  headline: string;
  learning_streak: number;
  stats: { label: string; value: string; tone: string }[];
  next_lesson: { id: number; title: string; slug: string; summary: string } | null;
  recommended_exercise: { id: number; title: string; category: string; difficulty: string } | null;
  active_projects: { id: number; title: string; status: string; portfolio_score: number }[];
  recommendation_panel: { title: string; reason: string }[];
};

export type DashboardToday = {
  focus: string[];
  highlights: string[];
  blockers: string[];
};

export type Lesson = {
  id: number;
  learning_path_id: number;
  title: string;
  slug: string;
  summary: string;
  content_md: string;
  prerequisites_json: string[];
  estimated_minutes: number;
  order_index: number;
  tags_json: string[];
  is_completed?: boolean;
};

export type LearningPath = {
  id: number;
  title: string;
  slug: string;
  description: string;
  level: string;
  estimated_hours: number;
  order_index: number;
  is_active: boolean;
  tags_json: string[];
  completion_pct: number;
  lessons: Lesson[];
};

export type Course = {
  id: number;
  title: string;
  slug: string;
  description: string;
  difficulty: string;
  estimated_hours: number;
  milestones_json: { label: string; status: string }[];
  status: string;
  track_focus: string;
};

export type Exercise = {
  id: number;
  title: string;
  slug: string;
  category: string;
  difficulty: string;
  prompt_md: string;
  starter_code: string;
  solution_code: string;
  explanation_md: string;
  tags_json: string[];
};

export type ExerciseAttempt = {
  id: number;
  exercise_id: number;
  submitted_code: string;
  notes: string;
  status: string;
  score: number;
  attempted_at: string;
};

export type ExerciseDetail = {
  exercise: Exercise;
  attempts: ExerciseAttempt[];
};

export type KnowledgeArticle = {
  id: number;
  title: string;
  slug: string;
  category: string;
  summary: string;
  content_md: string;
  source_links_json: string[];
  tags_json: string[];
  last_reviewed_at: string;
};

export type NewsItem = {
  id: number;
  source_name: string;
  title: string;
  slug: string;
  summary: string;
  source_url: string;
  category: string;
  published_at: string;
  signal_score: number;
  tags_json: string[];
  is_saved: boolean;
};

export type Project = {
  id: number;
  title: string;
  slug: string;
  summary: string;
  status: string;
  category: string;
  stack_json: string[];
  architecture_md: string;
  repo_url: string | null;
  demo_url: string | null;
  lessons_learned_md: string;
  portfolio_score: number;
};

export type JobPosting = {
  id: number;
  source_name: string;
  title: string;
  slug: string;
  company_name: string;
  location: string;
  employment_type: string;
  summary: string;
  source_url: string;
  description_md: string;
  published_at: string;
  tags_json: string[];
  skill_gaps_json: string[];
  fit_score: number;
  is_saved: boolean;
};

export type InterviewQuestion = {
  id: number;
  category: string;
  role_type: string;
  difficulty: string;
  question_text: string;
  answer_outline_md: string;
  tags_json: string[];
};

export type InterviewRoadmap = {
  focus_areas: string[];
  weekly_plan: string[];
};

export type Recommendation = {
  title: string;
  reason: string;
  action_path: string;
};

export type JobFitAnalysis = {
  job_id: number;
  fit_score: number;
  strengths: string[];
  gaps: string[];
  rationale: string;
};

export type FeedRefreshMeta = {
  source: string;
  item_count: number;
  live_item_count: number;
  seeded_item_count: number;
  refreshed_at: string;
};
