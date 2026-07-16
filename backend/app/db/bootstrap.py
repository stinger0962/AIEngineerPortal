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


SUMMARIES_COLUMN_PATCHES = {
    "summaries": [
        ("sections", "ALTER TABLE summaries ADD COLUMN sections JSON"),
        ("output_type", "ALTER TABLE summaries ADD COLUMN output_type VARCHAR(20) DEFAULT 'summary'"),
        ("mindmap_md", "ALTER TABLE summaries ADD COLUMN mindmap_md TEXT"),
    ],
}

# Per-browser privacy for 命理: anonymous device ownership. Existing rows keep
# device_id NULL (hidden from all devices until claimed).
ORACLE_PRIVACY_COLUMN_PATCHES = {
    "ziwei_profiles": [
        ("device_id", "ALTER TABLE ziwei_profiles ADD COLUMN device_id VARCHAR(64)"),
    ],
    "qian_readings": [
        ("device_id", "ALTER TABLE qian_readings ADD COLUMN device_id VARCHAR(64)"),
    ],
}

# Columns whose NOT NULL must be relaxed on already-existing tables.
# (create_all handles new DBs; this handles the prod table created earlier.)
NULLABILITY_PATCHES = {
    "dub_videos": ["youtube_url"],
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
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_korean_regions_slug ON korean_regions (slug)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_korean_nodes_slug ON korean_nodes (slug)",
    "CREATE INDEX IF NOT EXISTS ix_korean_nodes_region ON korean_nodes (region_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_korean_progress_user_node ON korean_progress (user_id, node_id)",
    "CREATE INDEX IF NOT EXISTS ix_korean_conv_user_node ON korean_conversations (user_id, node_id)",
    "CREATE INDEX IF NOT EXISTS ix_korean_msg_conv ON korean_messages (conversation_id)",
    "CREATE INDEX IF NOT EXISTS ix_ziwei_profiles_device ON ziwei_profiles (device_id)",
    "CREATE INDEX IF NOT EXISTS ix_qian_readings_device ON qian_readings (device_id)",
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

        all_patches = {
            **PHASE_TWO_COLUMN_PATCHES,
            **PHASE_FIVE_COLUMN_PATCHES,
            **SUMMARIES_COLUMN_PATCHES,
            **ORACLE_PRIVACY_COLUMN_PATCHES,
        }
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

        # Relax NOT NULL on columns that gained nullable semantics later.
        # Postgres-only DDL; on SQLite the model's create_all already made it
        # nullable, so this is a guarded no-op there.
        if connection.dialect.name == "postgresql":
            for table_name, columns in NULLABILITY_PATCHES.items():
                if table_name not in existing_tables:
                    continue
                col_info = {c["name"]: c for c in inspector.get_columns(table_name)}
                for col in columns:
                    info = col_info.get(col)
                    if info is not None and info.get("nullable") is False:
                        connection.execute(
                            text(f"ALTER TABLE {table_name} ALTER COLUMN {col} DROP NOT NULL")
                        )

        # Apply index patches idempotently on existing databases
        for index_ddl in INDEX_PATCHES:
            connection.execute(text(index_ddl))
