# AI Engineer Personal Portal

## Purpose
Build a personal AI Engineer Portal tailored to the user: a single platform that combines career transition planning, structured learning, practical coding, project execution, industry awareness, and job opportunity tracking.

This portal should function as:
- a personal dashboard
- a learning center
- a course and curriculum hub
- a Python practice lab
- an AI engineering knowledge base
- a news and trend intelligence feed
- a career opportunity center
- a project execution command center

The user is a senior full-stack software engineer transitioning into AI engineering. The product must feel professional, modern, motivating, and highly actionable. It should reduce cognitive overhead and help the user move from “experienced software engineer exploring AI” to “AI engineer with portfolio, interview readiness, and market awareness.”

---

## Product Vision
Create a private personal portal that becomes the user’s operating system for an AI engineer career transition.

The portal should answer these daily questions:
- What should I learn next?
- What should I practice today?
- What AI engineering news matters to me?
- What jobs are relevant to my target path?
- What projects should I build or improve?
- What skills am I missing for interviews?
- How is my progress trending over time?

The system should prioritize:
- personalization to the user’s background
- clear learning progression
- practical coding and portfolio building
- fast visibility into industry movement
- measurable progress and accountability
- modular architecture for future expansion

---

## Primary User
### User profile
- Senior software engineer
- Full-stack background
- Strong React experience
- Comfortable building backend systems
- Wants to transition into AI Engineer roles
- Wants a tailored, serious, execution-focused product rather than a generic tutorial website

### Current strengths
- Frontend and full-stack engineering
- Product building mindset
- Systems thinking
- Real-world software delivery experience
- Ability to learn independently

### Gaps to close
- AI/ML systems breadth
- model lifecycle understanding
- vector search / RAG / agent systems patterns
- evaluation and observability
- ML deployment and infrastructure patterns
- interview preparation specific to AI Engineer roles
- structured learning path instead of fragmented exploration

---

## Product Goals
### Business goal
Help the user systematically transition into AI engineering through one integrated portal.

### User goals
- learn AI engineering in a structured way
- practice Python and AI coding regularly
- track progress across topics and projects
- stay updated on AI industry trends
- monitor career opportunities
- prepare for AI engineering interviews
- organize notes, resources, and projects in one place

### Success criteria
Within 3 to 6 months, the portal should help the user:
- complete a structured AI learning roadmap
- build multiple portfolio-grade AI projects
- improve Python and applied AI engineering fluency
- maintain awareness of market trends and tools
- prepare for and apply to relevant jobs with confidence

---

## Product Scope

## Core modules
### 1. Personal dashboard
A home screen summarizing what matters today.

Features:
- learning streak
- next recommended lesson
- pending Python exercises
- latest AI news highlights
- relevant job openings snapshot
- progress summary by skill area
- active projects status
- interview prep status

### 2. Learning center
Structured curriculum for AI engineering.

Features:
- topic taxonomy
- sequenced learning paths
- lesson pages
- notes and summaries
- checkpoints and quizzes
- personal completion tracking
- bookmarks and revisit lists

Suggested curriculum pillars:
- Python for AI
- Machine learning foundations
- Deep learning basics
- LLM fundamentals
- Prompt engineering
- Embeddings and vector databases
- Retrieval-augmented generation
- AI agents and tools
- Evaluation and observability
- Model serving and deployment
- MLOps and pipelines
- Data engineering for AI
- System design for AI products
- AI security and safety basics
- AI product case studies
- Interview preparation

### 3. Course series hub
A curated set of guided mini-courses.

Features:
- beginner to advanced tracks
- estimated duration
- prerequisites
- milestone projects
- completion status
- personal notes per course

Example tracks:
- AI Engineer Foundations
- Practical LLM Engineer
- RAG Builder Track
- AI Agents Builder Track
- MLOps for Software Engineers
- Interview Prep Track

### 4. Python practice hub
Hands-on coding practice focused on AI engineering needs.

Features:
- categorized exercises
- difficulty levels
- topic filters
- notebook-style explanations
- code runner integration later
- solution comparison
- saved attempts
- spaced repetition for weak areas

Practice categories:
- Python syntax and fluency refresh
- data structures and algorithms for interviews
- numpy / pandas basics
- APIs and async patterns
- data cleaning and transformation
- embeddings/vector operations
- model inference wrappers
- prompt templating
- evaluation scripts
- simple ML and DL exercises

### 5. AI knowledge hub
Reference center for tools, concepts, architecture patterns, and frameworks.

Features:
- searchable concept library
- architecture pattern pages
- glossary
- model/provider comparison pages
- framework comparison pages
- deployment and tooling reference
- diagrams and cheat sheets

Examples:
- what is RAG
- agent orchestration patterns
- evaluation metrics
- vector DB tradeoffs
- OpenAI vs Anthropic vs open source stack notes
- LangGraph / DSPy / LlamaIndex / LangChain comparison
- inference serving patterns
- fine-tuning vs prompting vs RAG decision guide

### 6. AI news and trend feed
Curated intelligence relevant to the user’s career shift.

Features:
- daily or weekly digest view
- topic filtering
- save for later
- signal scoring
- trend tags
- company watchlist
- tooling updates
- research-to-practice summaries

News categories:
- major model releases
- AI tooling and developer platforms
- LLM frameworks
- MLOps tools
- startup and enterprise adoption trends
- AI regulation and policy affecting engineering teams
- hiring trends and role expectations
- open-source project momentum

### 7. Career opportunity center
Track jobs and skill alignment.

Features:
- AI engineer job feed
- saved jobs
- job requirement parser
- skill gap extraction
- resume alignment notes
- interview prep mapping to jobs
- company watchlist
- application tracker in later phase

Job categories:
- AI Engineer
- Applied AI Engineer
- LLM Engineer
- ML Engineer
- AI Product Engineer
- Developer Experience AI roles

### 8. Project portfolio hub
A place to define, track, and showcase AI projects.

Features:
- project cards
- progress stages
- architecture notes
- tech stack tags
- lessons learned log
- demo/repo links
- portfolio readiness score

Suggested starter project categories:
- RAG app
- agent workflow app
- document understanding app
- multimodal app
- evaluation dashboard
- AI productivity assistant
- AI-powered industry analysis tool

### 9. Interview prep center
Targeted preparation area for AI engineering roles.

Features:
- role-based question bank
- system design prompts
- Python refresh tasks
- ML/LLM concept reviews
- behavioral story bank
- mock interview checklist
- company-specific prep notes later

### 10. Personalization engine
The portal should adapt recommendations to the user.

Initial personalization rules:
- prioritize engineering-heavy AI topics over research-heavy math paths
- leverage the user’s React/full-stack background
- recommend product-building projects early
- emphasize Python, LLM apps, RAG, agents, evaluation, deployment
- surface interview prep once skill coverage reaches threshold

---

## Non-functional requirements
- clean and professional UI
- desktop-first for phase 1, responsive support planned
- modular architecture
- scalable backend design
- production-minded code quality
- strong typing and validation
- auditable data flow
- background job support for feeds
- easy local development
- future-ready for auth and user profiles

---

## Recommended Architecture

## High-level stack
### Frontend
- Next.js with TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query for server state
- Zustand or lightweight state store if needed
- Recharts for progress analytics

### Backend
- Python FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic migrations
- PostgreSQL
- Redis for caching / background job support
- Celery or RQ for async jobs

### Data / infra
- PostgreSQL for relational data
- Redis for job queue and cache
- Optional object storage later for documents/assets
- Docker for local dev and deployment consistency

### Ingestion / enrichment
- scheduled jobs for AI news aggregation
- scheduled jobs for job feed ingestion
- LLM enrichment pipeline for summarization/tagging/gap extraction

### Future AI features
- embeddings service for semantic search across knowledge base and notes
- recommendation engine for learning next steps
- resume-job matching
- portfolio feedback assistant

---

## System architecture
### Frontend apps/pages
- `/` dashboard
- `/learn` learning center home
- `/learn/path/:slug` learning path detail
- `/learn/lesson/:slug` lesson detail
- `/courses` course series hub
- `/practice/python` practice dashboard
- `/practice/python/:exerciseId` exercise page
- `/knowledge` AI knowledge hub
- `/knowledge/:slug` detail page
- `/news` AI news feed
- `/jobs` career opportunities
- `/projects` portfolio hub
- `/interview` interview prep center
- `/settings` personalization and preferences

### Backend domains
- auth (phase 2 or later)
- users
- dashboard
- learning
- courses
- exercises
- knowledge
- news
- jobs
- projects
- interview
- recommendations
- ingestion
- analytics

### Suggested backend folder structure
```text
backend/
  app/
    api/
      v1/
        routes/
          dashboard.py
          learning.py
          courses.py
          exercises.py
          knowledge.py
          news.py
          jobs.py
          projects.py
          interview.py
          recommendations.py
    core/
      config.py
      database.py
      security.py
      logging.py
    models/
      user.py
      learning.py
      course.py
      exercise.py
      knowledge.py
      news.py
      job.py
      project.py
      interview.py
      progress.py
    schemas/
      dashboard.py
      learning.py
      course.py
      exercise.py
      knowledge.py
      news.py
      job.py
      project.py
      interview.py
    services/
      dashboard_service.py
      learning_service.py
      course_service.py
      exercise_service.py
      knowledge_service.py
      news_service.py
      job_service.py
      project_service.py
      interview_service.py
      recommendation_service.py
    repositories/
    workers/
      news_ingestion.py
      jobs_ingestion.py
      summarization.py
      gap_analysis.py
    utils/
    main.py
  tests/
  alembic/
  requirements.txt
  docker-compose.yml
```

---

## Data model outline
### Core entities
#### User
- id
- name
- email
- target_role
- skill_profile_json
- preferences_json
- created_at
- updated_at

#### LearningPath
- id
- title
- slug
- description
- level
- estimated_hours
- order_index
- is_active

#### Lesson
- id
- learning_path_id
- title
- slug
- summary
- content_md
- prerequisites_json
- estimated_minutes
- order_index
- tags_json

#### Course
- id
- title
- slug
- description
- difficulty
- estimated_hours
- milestones_json
- status

#### Exercise
- id
- title
- slug
- category
- difficulty
- prompt_md
- starter_code
- solution_code
- explanation_md
- tags_json

#### UserExerciseAttempt
- id
- user_id
- exercise_id
- submitted_code
- notes
- status
- score
- attempted_at

#### KnowledgeArticle
- id
- title
- slug
- category
- summary
- content_md
- source_links_json
- tags_json
- last_reviewed_at

#### NewsItem
- id
- title
- source
- source_url
- published_at
- summary
- category
- tags_json
- relevance_score
- is_saved

#### JobPosting
- id
- company
- title
- location
- source
- source_url
- posted_at
- description_text
- extracted_skills_json
- fit_score
- status

#### Project
- id
- title
- slug
- summary
- status
- category
- stack_json
- architecture_md
- repo_url
- demo_url
- lessons_learned_md
- portfolio_score

#### InterviewQuestion
- id
- category
- role_type
- difficulty
- question_text
- answer_outline_md
- tags_json

#### ProgressSnapshot
- id
- user_id
- date
- learning_completion_pct
- python_practice_count
- projects_completed_count
- interview_readiness_score
- notes

---

## API design outline
### Dashboard
- `GET /api/v1/dashboard/summary`
- `GET /api/v1/dashboard/today`

### Learning
- `GET /api/v1/learning/paths`
- `GET /api/v1/learning/paths/{path_id}`
- `GET /api/v1/learning/lessons/{lesson_slug}`
- `POST /api/v1/learning/lessons/{lesson_id}/complete`

### Courses
- `GET /api/v1/courses`
- `GET /api/v1/courses/{course_slug}`
- `POST /api/v1/courses/{course_id}/progress`

### Exercises
- `GET /api/v1/exercises`
- `GET /api/v1/exercises/{exercise_id}`
- `POST /api/v1/exercises/{exercise_id}/attempt`
- `GET /api/v1/exercises/recommended`

### Knowledge
- `GET /api/v1/knowledge`
- `GET /api/v1/knowledge/{slug}`
- `GET /api/v1/knowledge/search`

### News
- `GET /api/v1/news`
- `POST /api/v1/news/refresh`
- `POST /api/v1/news/{id}/save`

### Jobs
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{id}`
- `POST /api/v1/jobs/{id}/save`
- `POST /api/v1/jobs/{id}/analyze-fit`

### Projects
- `GET /api/v1/projects`
- `GET /api/v1/projects/{slug}`
- `POST /api/v1/projects`
- `PATCH /api/v1/projects/{id}`

### Interview
- `GET /api/v1/interview/questions`
- `GET /api/v1/interview/roadmap`

### Recommendations
- `GET /api/v1/recommendations/next-actions`

---

## Feature phasing roadmap

## Phase 0: foundation and scaffolding
Goal: establish architecture, repo, conventions, local dev, design system, and initial seed data.

Deliverables:
- monorepo or clearly separated frontend/backend
- environment config
- database setup
- migration setup
- shared coding standards
- seeded content for MVP
- shell UI and navigation

## Phase 1: MVP personal portal core
Goal: make a usable private portal with real utility.

Deliverables:
- dashboard
- learning center with seeded curriculum
- course hub
- Python practice hub with seeded exercises
- knowledge hub with initial articles
- projects hub
- manual content entry support
- progress tracking basics

## Phase 2: intelligence and feeds
Goal: add dynamic AI news and job opportunity value.

Deliverables:
- AI news feed ingestion pipeline
- job feed ingestion pipeline
- AI summarization/tagging
- fit scoring for job postings
- dashboard intelligence widgets

## Phase 3: career transition engine
Goal: make the portal actively guide the career switch.

Deliverables:
- personalized recommendations
- skill gap analysis
- interview prep center
- learning path adaptation
- portfolio readiness scoring

## Phase 4: advanced AI features
Goal: turn the product into an AI-native assistant for growth.

Deliverables:
- semantic search over portal content
- conversational assistant for portal knowledge
- resume-job alignment support
- project idea generator
- adaptive practice generation

## Phase 5: production hardening
Goal: make it robust and extensible.

Deliverables:
- auth and user settings
- observability
- background job reliability
- content admin tooling
- deployment pipelines
- security hardening

---

## Detailed implementation plan

## Frontend architecture plan
### Principles
- feature-based folders
- reusable UI primitives
- clean state boundaries
- optimistic UX where appropriate
- server-state-first architecture

### Suggested frontend structure
```text
frontend/
  src/
    app/
      dashboard/
      learn/
      courses/
      practice/
      knowledge/
      news/
      jobs/
      projects/
      interview/
      settings/
    components/
      layout/
      dashboard/
      learning/
      courses/
      practice/
      knowledge/
      news/
      jobs/
      projects/
      interview/
      ui/
    lib/
      api/
      hooks/
      utils/
      constants/
      types/
    store/
    styles/
```

### Initial UI components
- AppShell
- SidebarNav
- Header
- DashboardSummaryCards
- ProgressRing
- RecommendationPanel
- NewsCard
- JobCard
- LearningPathCard
- LessonContentViewer
- ExerciseCard
- KnowledgeArticleCard
- ProjectCard
- InterviewQuestionCard

---

## Backend architecture plan
### Principles
- domain-oriented services
- thin route handlers
- strong schema validation
- clean DB session management
- testable service layer
- ingestion separated from API

### Services responsibilities
- LearningService: learning paths, lessons, completion tracking
- CourseService: guided tracks and milestones
- ExerciseService: practice retrieval, attempts, recommendations
- KnowledgeService: articles, indexing, search
- NewsService: curated feed retrieval and filtering
- JobService: job storage, parsing, scoring
- ProjectService: portfolio objects and progress
- InterviewService: question banks and prep plans
- RecommendationService: next best actions based on user state

---

## Seed content plan for MVP
The first version should not wait for dynamic ingestion.
Seed meaningful content manually so the portal is useful from day one.

### Initial seeded learning paths
1. Python for AI Engineers
2. LLM App Foundations
3. RAG Systems
4. AI Agents and Tools
5. Evaluation and Observability
6. AI Deployment and MLOps
7. AI Engineer Interview Readiness

### Initial seeded exercises
At least 40 to 60 exercises:
- Python refresh
- data transformation
- API handling
- prompt formatting
- embedding handling
- retrieval logic
- evaluation scripts
- mini system design coding tasks

### Initial seeded knowledge articles
At least 30 to 50 articles:
- conceptual explainers
- tool comparisons
- architecture cheat sheets
- decision frameworks

### Initial seeded interview bank
At least 80 questions across:
- Python
- backend systems
- AI/ML fundamentals
- LLM systems
- RAG and agents
- evaluation and production concerns
- behavioral questions for transition narrative

---

## Personalization strategy
The system should be tailored to this user specifically.

### Tailoring rules
- assume strong JavaScript/React/full-stack base
- recommend Python depth-building early
- prioritize AI application engineering over pure model research
- emphasize shipping portfolio projects quickly
- include LLM systems and AI product engineering heavily
- map each learning path to interview relevance and job relevance

### Personalized dashboard ideas
- “Today’s best next step”
- “Skill gaps blocking AI Engineer roles”
- “Projects that best leverage your React/full-stack strength”
- “This week’s AI developments worth your time”
- “Top job requirements you still need to close”

---

## Important engineering choices
### Why Next.js + FastAPI
- excellent frontend developer ergonomics
- strong backend speed and schema validation
- easy AI ecosystem integration on Python side
- good separation of concerns
- scalable and hiring-aligned stack for AI products

### Why PostgreSQL instead of SQLite for this portal
- multi-domain data model
- better scaling for feeds and tracking
- easier future production migration path
- suitable for search metadata and analytics

### Why seed content first
- immediate product value
- faster frontend/backend iteration
- avoids blocking on ingestion pipeline complexity
- improves design quality before automation

---

## Multi-agent delivery strategy for Codex
Yes, use worktrees for parallel development where possible.

### Recommended worktree model
Use one main orchestration thread plus several focused implementation threads.

Suggested parallel agent threads:
1. **Foundation agent**
   - repo scaffolding
   - environment setup
   - shared config
   - linting/formatting
   - Docker and compose

2. **Frontend shell agent**
   - app shell
   - navigation
   - layout
   - theme
   - shared UI primitives

3. **Backend core agent**
   - FastAPI app
   - DB wiring
   - models
   - migrations
   - common schemas

4. **Learning module agent**
   - learning paths
   - lessons
   - progress tracking

5. **Practice module agent**
   - exercises
   - attempts
   - recommendation basics

6. **Knowledge/news/jobs agent**
   - knowledge module
   - news feed scaffolding
   - jobs module scaffolding

7. **Projects/interview agent**
   - projects hub
   - interview prep center
   - readiness score scaffolding

### Rules for parallel work
- each agent gets a narrow scope
- avoid overlapping files when possible
- merge foundational work first
- define API contracts and shared types early
- keep one orchestration thread responsible for reviewing and integrating
- require every agent to run lint/tests before handing off

### Coordination artifacts to create early
- architecture decision record file
- API contract document
- database schema overview
- frontend route map
- shared naming conventions
- definition of done checklist

---

## Definition of done for MVP
MVP is complete when:
- portal has working navigation and polished shell
- dashboard shows real personalized summaries from backend
- learning center supports paths, lessons, and completion tracking
- Python practice hub supports viewing and submitting attempts
- knowledge hub is searchable and content-backed
- projects hub supports CRUD basics
- progress is persisted and visible
- seeded content makes the portal genuinely useful on day one
- codebase has tests for critical service logic and API routes
- local setup is documented and reproducible

---

## Testing strategy
### Backend
- unit tests for services
- API route tests with test DB
- migration sanity checks
- fixture-based seed validation

### Frontend
- component tests for critical reusable pieces
- route/page smoke tests
- form interaction tests for major flows

### End-to-end
- core flows:
  - open dashboard
  - complete lesson
  - submit exercise attempt
  - browse knowledge article
  - create/update project

---

## Risks and mitigations
### Risk: scope explosion
Mitigation:
- keep MVP focused on seeded content and essential tracking
- delay fancy AI features until core product is solid

### Risk: weak personalization
Mitigation:
- implement simple rule-based recommendations first
- evolve to smarter recommendations later

### Risk: ingestion complexity too early
Mitigation:
- do not block MVP on live feeds
- seed content first, then automate

### Risk: fragmented parallel agent work
Mitigation:
- define contracts first
- use worktree threads by module
- require integration review by orchestration thread

---

## Immediate build order
1. Scaffold frontend and backend projects
2. Establish database models and migrations
3. Build app shell and route structure
4. Implement learning center backend and frontend
5. Implement Python practice hub backend and frontend
6. Implement knowledge hub
7. Implement projects hub
8. Implement dashboard aggregation
9. Seed meaningful content
10. Add news and jobs scaffolding
11. Add personalization and recommendations basics

---

## Final instruction to Codex
Build this product as a serious personal AI Engineer Portal tailored to a senior full-stack software engineer transitioning into AI engineering. Favor pragmatic engineering choices, modular architecture, polished UX, and a phased roadmap. Start with a strong MVP using seeded content before adding dynamic ingestion or advanced AI features. Produce production-minded code, clean architecture, typed contracts, tests for critical flows, and a clear README for local setup.

When implementing, first create:
1. a concrete repo structure
2. architecture decision notes
3. the database schema and migrations
4. the frontend route and layout skeleton
5. the first MVP modules in the build order above

Do not try to build everything at once. Build in phases with stable checkpoints.

