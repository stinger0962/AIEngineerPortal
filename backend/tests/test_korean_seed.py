from pathlib import Path
from tempfile import mkdtemp

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import KoreanNode, KoreanRegion
from app.services.seed_service import seed_database

DB = Path(mkdtemp(prefix="korean-seed-")) / "t.db"
engine = create_engine(f"sqlite:///{DB.as_posix()}", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_seed_creates_regions_and_nodes_idempotently():
    # Exclude ai_feedback table — it uses PostgreSQL JSONB which SQLite can't compile.
    tables = [t for t in Base.metadata.sorted_tables if t.name != "ai_feedback"]
    Base.metadata.create_all(bind=engine, tables=tables)
    db = Session()
    try:
        seed_database(db)
        seed_database(db)  # second run must not duplicate
        regions = db.scalars(select(KoreanRegion)).all()
        nodes = db.scalars(select(KoreanNode)).all()
        assert len(regions) == 8
        assert len(nodes) == 54  # 5 + 7 + 7 + 7 + 7 + 7 + 7 + 7
    finally:
        db.close()
