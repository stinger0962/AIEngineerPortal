def test_summary_model_table_and_columns():
    from app.models.entities import Summary
    assert Summary.__tablename__ == "summaries"
    cols = set(Summary.__table__.columns.keys())
    assert {
        "id", "source_type", "source_url", "title", "tldr",
        "key_points", "takeaways", "sections",
        "output_type", "mindmap_md", "char_count", "created_at",
    }.issubset(cols)
