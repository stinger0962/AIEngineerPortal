from pathlib import Path
from tempfile import mkdtemp

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import KoreanProgress, MemoryCard, User
from app.services.korean import service as ksvc
from app.services.seed_service import seed_database

DB = Path(mkdtemp(prefix="korean-svc-")) / "t.db"
engine = create_engine(f"sqlite:///{DB.as_posix()}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _setup():
    Base.metadata.create_all(
        bind=engine,
        tables=[t for t in Base.metadata.sorted_tables if t.name != "ai_feedback"],
    )
    db = Session()
    seed_database(db)
    return db


def test_get_map_first_node_unlocked_rest_locked():
    db = _setup()
    try:
        uid = db.scalar(select(User.id))
        m = ksvc.get_map(db, uid)
        first_region = m[0]
        assert first_region["nodes"][0]["status"] == "unlocked"
        assert first_region["nodes"][1]["status"] == "locked"
    finally:
        db.close()


def test_complete_node_unlocks_next_and_seeds_cards():
    db = _setup()
    try:
        uid = db.scalar(select(User.id))
        m = ksvc.get_map(db, uid)
        first_slug = m[0]["nodes"][0]["slug"]
        ksvc.complete_node(db, uid, first_slug, score=1.0, stars=3)
        m2 = ksvc.get_map(db, uid)
        assert m2[0]["nodes"][0]["status"] == "completed"
        assert m2[0]["nodes"][1]["status"] == "unlocked"
    finally:
        db.close()


def test_reset_progress_clears_only_this_user():
    db = _setup()
    try:
        uid = db.scalar(select(User.id))
        first_slug = ksvc.get_map(db, uid)[0]["nodes"][0]["slug"]
        ksvc.complete_node(db, uid, first_slug, score=1.0, stars=3)
        ksvc.reset_progress(db, uid)
        assert db.scalars(select(KoreanProgress).where(KoreanProgress.user_id == uid)).all() == []
        assert db.scalars(select(MemoryCard).where(MemoryCard.category == "korean")).all() == []
        assert ksvc.get_map(db, uid)[0]["nodes"][0]["status"] == "unlocked"
    finally:
        db.close()
