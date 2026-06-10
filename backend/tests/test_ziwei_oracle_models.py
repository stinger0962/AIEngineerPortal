from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_DIR = Path(mkdtemp(prefix="ziwei-oracle-model-tests-"))
TEST_DATABASE_URL = f"sqlite:///{(TEST_DB_DIR / 'test.db').as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def setup_module():
    from app.models.entities import ZiweiConversation, ZiweiMessage

    ZiweiConversation.__table__.create(bind=engine, checkfirst=True)
    ZiweiMessage.__table__.create(bind=engine, checkfirst=True)


def teardown_module():
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


def test_conversation_and_message_roundtrip():
    from app.models.entities import ZiweiConversation, ZiweiMessage

    db = TestingSessionLocal()
    try:
        conv = ZiweiConversation(profile_id=1, scenario="natal", title="开场解读")
        db.add(conv)
        db.commit()
        db.refresh(conv)
        assert conv.id is not None
        assert conv.scenario == "natal"
        assert conv.created_at is not None

        msg = ZiweiMessage(
            conversation_id=conv.id,
            role="assistant",
            content="命宫紫微……",
            chart_context_json={"focus": "命宫", "year": None},
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        assert msg.id is not None
        assert msg.role == "assistant"
        assert msg.chart_context_json["focus"] == "命宫"
        assert msg.created_at is not None
    finally:
        db.close()
