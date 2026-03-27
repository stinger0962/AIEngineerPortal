export type DashboardSummary = {
  user_name: string;
  headline: string;
  learning_streak: number;
  stats: { label: string; value: string; tone: string }[];
  next_lesson: { id: number; title: string; slug: string; summary: string } | null;
  recommended_exercise: { id: number; title: string; category: string; difficulty: string } | null;
  active_projects: { id: number; title: string; status: string; portfolio_score: number }[];
  recommendation_panel: { title: string; reason: string }[];
  adaptive_focus?: AdaptiveFocus | null;
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
  milestones_json: {
    label: string;
    status: string;
    goal?: string;
    outcome?: string;
    path_slug?: string;
    path_title?: string;
    lesson_slugs?: string[];
    exercise_slugs?: string[];
    project_slug?: string;
    deliverable?: string;
    why_it_matters?: string;
  }[];
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
  progression_label?: string | null;
  practice_stage?: string | null;
  hint_md?: string | null;
  review_checklist_json?: string[];
  success_criteria_json?: string[];
  related_lesson_slugs?: string[];
  related_lesson_titles?: string[];
  next_exercise_id?: number | null;
  next_exercise_slug?: string | null;
  next_exercise_title?: string | null;
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
  review_prompt?: string | null;
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
  why_it_matters: string;
  suggested_action: string;
  focus_area: string;
  recommended_path_slug?: string | null;
  recommended_path_title?: string | null;
  recommended_exercise_category?: string | null;
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
  fit_summary: string;
  suggested_action: string;
  primary_gap?: string | null;
  focus_area: string;
  recommended_path_slug?: string | null;
  recommended_path_title?: string | null;
  recommended_exercise_category?: string | null;
};

export type InterviewQuestion = {
  id: number;
  category: string;
  role_type: string;
  difficulty: string;
  question_text: string;
  answer_outline_md: string;
  tags_json: string[];
  practice_count: number;
  last_practiced_at?: string | null;
  average_confidence?: number | null;
};

export type InterviewRoadmap = {
  focus_areas: string[];
  weekly_plan: string[];
  rationale: string[];
};

export type PortfolioReadiness = {
  overall_score: number;
  strongest_signals: string[];
  gaps_to_close: string[];
  next_best_moves: string[];
};

export type SkillGapInsight = {
  title: string;
  urgency: string;
  evidence: string;
  action_path: string;
};

export type MasteryArea = {
  area_slug: string;
  area_title: string;
  mastery_score: number;
  status: string;
  evidence: string;
  gap: string;
  weakest_signal: string;
  next_action_path: string;
  next_action_label: string;
};

export type AdaptiveFocus = {
  title: string;
  reason: string;
  action_path: string;
  target_kind: string;
  mastery_score: number;
  area_slug: string;
  area_title: string;
  action_label: string;
};

export type InterviewPractice = {
  question_id: number;
  practice_count: number;
  last_practiced_at: string;
  average_confidence: number;
};

export type Recommendation = {
  title: string;
  reason: string;
  action_path: string;
  source_kind: string;
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
  is_stale: boolean;
  refresh_window_hours: number;
  auto_refresh_enabled: boolean;
};

export type MemoryCard = {
  id: number;
  front_md: string;
  back_md: string;
  category: string;
  source_kind: "lesson" | "exercise" | "interview" | "knowledge";
  source_title: string;
  difficulty: "beginner" | "intermediate" | "advanced";
  tags_json: string[];
  review_count: number;
  last_reviewed_at: string | null;
  confidence: number | null;
  next_review_at: string | null;
};

export type MemoryCardReview = {
  card_id: number;
  confidence: number;
  reviewed_at: string;
};

export type ReviewSessionSummary = {
  total_cards: number;
  reviewed: number;
  avg_confidence: number;
  strongest_category: string;
  weakest_category: string;
};
