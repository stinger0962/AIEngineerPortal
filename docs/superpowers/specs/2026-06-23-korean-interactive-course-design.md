# 한국어 — Korean Interactive Course (Design)

**Date:** 2026-06-23
**Status:** Approved (brainstorm), ready for implementation planning
**Module:** New `korean` module inside the 方寸 platform

## 1. Purpose & scope

A fun, game-like Korean course for **absolute beginners** that takes a learner from zero
(cannot read 한글) up to **early intermediate**, focused on **everyday dialogue (speak +
listen) and reading**, tuned for the goal of **traveling and living in Korea**.

The course is a **reusable, multi-user product**, not a personal artifact. Content is authored
once and serves any zero-knowledge user; progress is tracked per user and is resettable.

**v1 scope:** the engine plus the first three regions — **한글 Reading Island, Arrival,
Café & Food** (~18–20 authored nodes). Regions 3–9 are later content authoring in the same
format, not new engineering.

## 2. Experience model

A **hybrid**:

- **Journey Map spine** — a stylized map of regions (topics). Each region holds 3–5 nodes.
  Clearing all nodes in a region unlocks the next region. Provides clear beginner→intermediate
  progression.
- **Authored visual-novel Scenes** at each node — the learner plays a customizable/neutral
  avatar (traveler/new arrival). NPCs speak Korean; the learner responds.
- **Free AI Roleplay "Boss"** to clear each node — open-ended conversation with an AI
  character in the node's scenario.

### Node loop

Each region node is one of four kinds:

1. **Reading** (한글 Island only) — tap a letter to hear it, build a syllable block, read a
   real word/sign. Pure recognition + listening, no grammar. Payoff: read a Korean sign unaided.
2. **Scene** — story dialogue. NPC line plays (with 한글 + romanization + 🔊 replay); the
   learner responds by **tapping a line** or **🎤 saying it**.
3. **Drill** — short mixed practice (match / listen-and-pick / fill-blank / type 한글) on the
   new words and grammar; seeds spaced-repetition cards.
4. **Boss** — free AI roleplay with a concrete goal (e.g., "order a coffee and pay"). The AI
   persona reacts to meaning, adapts difficulty, grades the goal, and awards stars that clear
   the node.

Romanization is shown alongside 한글 for beginners, with a **toggle to fade it out** as the
learner progresses.

## 3. Speaking, listening & AI

- **Listening (TTS):** reuse the existing MiniMax `_tts_bytes` path with a **Korean voice id**.
  A `/korean/tts` endpoint mirrors `/ziwei/tts`. Authored lines are **cached by text-hash**
  (generate once, store mp3 path, replay free). TTS is always an enhancement, never a gate.
- **Speaking (STT):** browser **Web Speech API** (`SpeechRecognition`, `lang="ko-KR"`),
  client-side, zero infra, zero cost. Unsupported browsers (Safari/Firefox) hide the 🎤 button
  and fall back to tap/type — no learner is ever blocked. Server-side Whisper is a documented
  later upgrade, not in v1.
- **"AI judges meaning" — two tiers:**
  - *Scene lines (constrained):* 1–3 accepted intents authored in `content_json`. The STT
    transcript is normalized and **fuzzy-matched locally** — instant, no AI call. Close enough
    passes; far off prompts a gentle retry.
  - *Boss roleplay (open-ended):* Claude via a `KoreanOracle` service (mirrors `ZiweiOracle`)
    with a **Korean tutor persona**. The system prompt receives the node's **goal**, the
    learner's **level**, and the **vocabulary introduced so far**, with a hard rule to stay
    within that vocabulary plus a small stretch. Streams over SSE; returns a structured verdict
    (goal met? stars? one correction tip) that writes `KoreanProgress`.
- **Cost posture:** reading, drills, scene-line checks, and TTS replays are free or one-time.
  Claude is invoked only during boss roleplay turns.

## 4. Architecture

**Placement (mirrors `ziwei`/`qian`):**

- Frontend: `frontend/src/app/korean/` (route `/korean`) + components under
  `frontend/src/components/korean/`.
- Backend: routes `backend/app/api/v1/routes/korean.py`; service logic in
  `backend/app/services/korean/` (`oracle.py`, `personas.py`).

**Content vs. state split** (the platform's established pattern — content tables seeded like
other content; per-user state keyed by `user_id`):

### Content tables (authored once, shared)

- **`KoreanRegion`** — `id`, `slug`, `title`, `order_index`, `theme`, `is_active`.
- **`KoreanNode`** — `id`, `region_id` (FK), `slug`, `kind`
  (`reading` | `scene` | `drill` | `boss`), `order_index`, `title`, `content_json` (full node
  payload, flexible JSON in the style of `milestones_json` / `context_json`).

### Per-user state tables (scoped by `user_id`)

- **`KoreanProgress`** — one row per (user, node): `status`
  (`locked` | `unlocked` | `completed`), `score`, `stars`, `completed_at`. Drives map unlocking
  and reset.
- **`MemoryCard`** (existing table) — vocab/phrases written with `category="korean"` so
  spaced-repetition review is reused, not rebuilt.
- **`KoreanConversation` / `KoreanMessage`** — boss roleplay transcripts, scoped per
  user + node (mirrors `ZiweiConversation` / `ZiweiMessage`).

**Current-user resolution:** the platform currently resolves a single default user via
`get_user_id(db)` (first user; no real auth yet). All Korean state is scoped by `user_id` via
that same helper, so it is personal and resettable today and works unchanged when real
multi-user auth arrives.

### `content_json` shapes

- **Reading:** `{ letters:[{jamo, sound, audio_key}], blocks:[…], words:[{ko, en}] }`
- **Scene:** `{ setting, character, lines:[{speaker, ko, romaji, en, audio_key}],
  your_turns:[{prompt_en, options:[…], accepted:[{ko, intents}]}],
  new_vocab:[{ko, en, romaji}] }`
- **Drill:** `{ items:[{type:"match"|"listen"|"fill"|"type", …}] }` (also auto-seeds
  `MemoryCard`s from the originating scene's `new_vocab`).
- **Boss:** `{ goal_en, persona, level, allowed_vocab, success_criteria, max_turns }`

## 5. v1 content — regions 0–2

- **Region 0 · 한글 Reading Island** (~5 reading nodes): basic vowels → consonants (2 nodes)
  → syllable blocks + 받침 → "read real words/signs" mini-boss. No grammar.
- **Region 1 · Arrival** (3 scenes + drills + 1 boss): greetings / thanks / yes-no →
  immigration (여권이요, purpose of visit) → exit & taxi. Boss: **get a taxi to the city**.
  Grammar: 입니다/이에요, basic particles, 네/아니요.
- **Region 2 · Café & Food** (3 scenes + drills + 1 boss): ordering (X 주세요) → native
  numbers 하나~열 + counters → paying / sizes. Boss: **order a drink and pay**. Grammar:
  주세요, Sino vs. native numbers, 이거/저거.

## 6. Reset & user scoping

- A "**Reset progress**" control in the Korean map header → confirmation dialog →
  `DELETE /korean/progress` deletes the current user's `KoreanProgress` rows, Korean
  `MemoryCard`s, and boss conversations. The map snaps back to Region 0 / Node 1 unlocked.
  Authored content is untouched.

## 7. Error handling

Graceful degradation everywhere — a flaky dependency never traps a learner:

- **No mic / unsupported browser** → 🎤 hides, tap/type carries on.
- **TTS upstream fails** → show text + romanization, log it (mirrors `/ziwei/tts` 502 handling).
- **Claude boss call fails / times out** → fall back to a canned NPC reply and allow retry; the
  node remains clearable via the scripted path.
- **STT mis-hears** → "didn't catch that — try again or tap," low-friction retry, no penalty.

## 8. Testing

- **Backend (pytest):** content seed integrity; progress unlock/complete transitions; reset
  wipes only the right user's rows; boss verdict writes `KoreanProgress`. AI calls mocked
  (existing `test_ai_service` pattern).
- **Content validation test:** every `content_json` conforms to its node-kind schema (catches
  authoring typos before the UI).
- **Frontend:** node loop renders each node kind; mic absence degrades correctly; romanization
  toggle works.

## 9. Build order

1. **Backend foundation** — models (`KoreanRegion`, `KoreanNode`, `KoreanProgress`,
   `KoreanConversation`, `KoreanMessage`), bootstrap/migration, Pydantic schemas, `content_json`
   validation, reuse `get_user_id`.
2. **Content authoring** — author regions 0–2 `content_json` and seed.
3. **Korean service + routes** — map/region/node listing, node fetch, node-completion submit,
   reset, `/korean/tts`, `KoreanOracle` + persona boss SSE, `MemoryCard` seeding.
4. **Frontend** — `/korean` map page; node players (reading, scene, drill, boss); TTS playback
   + caching; Web Speech API mic hook; romanization toggle; reset control.
5. **Review integration** — Korean `MemoryCard`s surface in the existing spaced-repetition
   review flow.
6. **Tests + polish + deploy** — full test pass, then deploy strictly via the GitHub Actions
   pipeline (tag `vX.Y.Z`); never SSH/build on the VPS.

## 10. Explicitly out of scope for v1

- Pronunciation scoring (phoneme-level feedback) — later upgrade on top of speaking.
- Server-side Whisper STT — browser Web Speech API covers v1.
- Regions 3–9 — content authoring in the existing format, after v1 ships.
- Real multi-user authentication — state is already `user_id`-scoped to be ready for it.
