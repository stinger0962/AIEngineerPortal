# API Contracts

Base path: `/api/v1`

## Dashboard
- `GET /dashboard/summary`
- `GET /dashboard/today`

## Learning
- `GET /learning/paths`
- `GET /learning/paths/{path_id}`
- `GET /learning/lessons/{lesson_slug}`
- `POST /learning/lessons/{lesson_id}/complete`

## Courses
- `GET /courses`
- `GET /courses/{course_slug}`
- `POST /courses/{course_id}/progress`

## Exercises
- `GET /exercises`
- `GET /exercises/{exercise_id}`
- `POST /exercises/{exercise_id}/attempt`
- `GET /exercises/recommended`

## Knowledge
- `GET /knowledge`
- `GET /knowledge/{slug}`
- `GET /knowledge/search`

## Projects
- `GET /projects`
- `GET /projects/{slug}`
- `POST /projects`
- `PATCH /projects/{project_id}`

## Interview
- `GET /interview/questions`
- `GET /interview/roadmap`

## Recommendations
- `GET /recommendations/next-actions`
