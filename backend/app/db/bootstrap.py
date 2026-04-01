from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


PHASE_FIVE_COLUMN_PATCHES = {
    "exercise_attempts": [
        (
            "ai_feedback_id",
            "ALTER TABLE exercise_attempts ADD COLUMN ai_feedback_id INTEGER REFERENCES ai_feedback(id)",
        ),
    ],
    "exercises": [
        (
            "is_generated",
            "ALTER TABLE exercises ADD COLUMN is_generated BOOLEAN DEFAULT FALSE",
        ),
        (
            "parent_exercise_id",
            "ALTER TABLE exercises ADD COLUMN parent_exercise_id INTEGER REFERENCES exercises(id)",
        ),
    ],
}

PHASE_TWO_COLUMN_PATCHES = {
    "news_items": [
        ("is_seeded", "ALTER TABLE news_items ADD COLUMN is_seeded BOOLEAN NOT NULL DEFAULT FALSE"),
        (
            "last_synced_at",
            "ALTER TABLE news_items ADD COLUMN last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        ),
    ],
    "job_postings": [
        ("is_seeded", "ALTER TABLE job_postings ADD COLUMN is_seeded BOOLEAN NOT NULL DEFAULT FALSE"),
        (
            "last_synced_at",
            "ALTER TABLE job_postings ADD COLUMN last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        ),
    ],
}


MEMORY_CARDS_CREATE_DDL = """
CREATE TABLE IF NOT EXISTS memory_cards (
    id SERIAL PRIMARY KEY,
    front_md TEXT NOT NULL,
    back_md TEXT NOT NULL,
    category VARCHAR(100) NOT NULL,
    source_kind VARCHAR(50) NOT NULL,
    source_title VARCHAR(500) NOT NULL,
    difficulty VARCHAR(50) DEFAULT 'intermediate',
    tags_json JSON DEFAULT '[]',
    review_count INTEGER DEFAULT 0,
    last_reviewed_at TIMESTAMP,
    confidence INTEGER,
    next_review_at TIMESTAMP,
    is_seeded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


INDEX_PATCHES = [
    "CREATE INDEX IF NOT EXISTS ix_exercises_category ON exercises (category)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_exercises_slug ON exercises (slug)",
    "CREATE INDEX IF NOT EXISTS ix_exercises_is_generated ON exercises (is_generated)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_lessons_slug ON lessons (slug)",
    "CREATE INDEX IF NOT EXISTS ix_lessons_path_id ON lessons (learning_path_id)",
    "CREATE INDEX IF NOT EXISTS ix_attempts_user_exercise ON exercise_attempts (user_id, exercise_id)",
    "CREATE INDEX IF NOT EXISTS ix_attempts_attempted_at ON exercise_attempts (attempted_at)",
    "CREATE INDEX IF NOT EXISTS ix_ai_feedback_feature_ref ON ai_feedback (feature, reference_id)",
    "CREATE INDEX IF NOT EXISTS ix_ai_feedback_user_created ON ai_feedback (user_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_interview_questions_category ON interview_questions (category)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_knowledge_articles_slug ON knowledge_articles (slug)",
    "CREATE INDEX IF NOT EXISTS ix_memory_cards_category ON memory_cards (category)",
    "CREATE INDEX IF NOT EXISTS ix_memory_cards_next_review ON memory_cards (next_review_at)",
]


def apply_runtime_schema_patches(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if not existing_tables:
        return

    with engine.begin() as connection:
        # Ensure memory_cards table exists (phase 6 — spaced repetition)
        if "memory_cards" not in existing_tables:
            connection.execute(text(MEMORY_CARDS_CREATE_DDL))

        all_patches = {**PHASE_TWO_COLUMN_PATCHES, **PHASE_FIVE_COLUMN_PATCHES}
        for table_name, patches in all_patches.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            has_last_synced_at = "last_synced_at" in existing_columns
            for column_name, ddl in patches:
                if column_name not in existing_columns:
                    connection.execute(text(ddl))
                    existing_columns.add(column_name)
                if column_name == "last_synced_at":
                    has_last_synced_at = True
            if has_last_synced_at:
                connection.execute(
                    text(f"UPDATE {table_name} SET last_synced_at = CURRENT_TIMESTAMP WHERE last_synced_at IS NULL")
                )

        # Apply index patches idempotently on existing databases
        for index_ddl in INDEX_PATCHES:
            connection.execute(text(index_ddl))
