from app.models import (
    KoreanConversation,
    KoreanMessage,
    KoreanNode,
    KoreanProgress,
    KoreanRegion,
)


def test_korean_models_have_expected_tables():
    assert KoreanRegion.__tablename__ == "korean_regions"
    assert KoreanNode.__tablename__ == "korean_nodes"
    assert KoreanProgress.__tablename__ == "korean_progress"
    assert KoreanConversation.__tablename__ == "korean_conversations"
    assert KoreanMessage.__tablename__ == "korean_messages"


def test_korean_node_has_content_json_and_kind():
    cols = {c.name for c in KoreanNode.__table__.columns}
    assert {"region_id", "slug", "kind", "order_index", "title", "content_json"} <= cols


def test_korean_progress_is_user_scoped():
    cols = {c.name for c in KoreanProgress.__table__.columns}
    assert {"user_id", "node_id", "status", "score", "stars", "completed_at"} <= cols
