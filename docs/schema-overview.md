# Schema Overview

Core persisted entities:

- `users`
- `learning_paths`
- `lessons`
- `lesson_completions`
- `courses`
- `exercise_attempts`
- `exercises`
- `knowledge_articles`
- `projects`
- `interview_questions`
- `progress_snapshots`

Design notes:

- JSON columns store tags, milestones, stacks, and skill metadata.
- A single default user powers Phase 1 personalization.
- Progress is computed from persisted completion and attempt records, then materialized into snapshots.
