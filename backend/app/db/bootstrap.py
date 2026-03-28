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


def apply_runtime_schema_patches(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    if not existing_tables:
        return

    with engine.begin() as connection:
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
