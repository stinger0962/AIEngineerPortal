from pathlib import Path
from tempfile import mkdtemp
from shutil import rmtree

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_DIR = Path(mkdtemp(prefix="ziwei-model-tests-"))
TEST_DATABASE_URL = f"sqlite:///{(TEST_DB_DIR / 'test.db').as_posix()}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def setup_module():
    from app.models.entities import ZiweiProfile

    ZiweiProfile.__table__.create(bind=engine, checkfirst=True)


def teardown_module():
    engine.dispose()
    if TEST_DB_DIR.exists():
        rmtree(TEST_DB_DIR, ignore_errors=True)


def test_ziwei_profile_roundtrip():
    from app.models.entities import ZiweiProfile

    db = TestingSessionLocal()
    try:
        profile = ZiweiProfile(
            name="测试命主",
            relation="self",
            gender="female",
            birth_date="2000-08-16",
            birth_time_index=2,
            chart_json={"palaces": [{"name": "命宫"}]},
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        assert profile.id is not None
        assert profile.persona == "sage"  # 默认人设
        assert profile.is_lunar_input is False
        assert profile.is_leap_month is False
        assert profile.portrait_json == {}
        assert profile.chart_json["palaces"][0]["name"] == "命宫"
        assert profile.created_at is not None
    finally:
        db.close()
