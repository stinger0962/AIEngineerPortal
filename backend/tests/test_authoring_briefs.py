from app.services.korean.personas import PERSONAS
from scripts.korean_authoring.briefs import RegionBrief, get_brief, BRIEFS


def test_getting_around_brief_present():
    b = get_brief("getting-around")
    assert isinstance(b, RegionBrief)
    assert b.slug == "getting-around"
    assert b.order_index == 3
    assert b.counts == {"scenes": 3, "drills": 3, "boss": 1}
    assert b.boss_persona in PERSONAS
    assert len(b.target_vocab) >= 4
    assert all({"ko", "en", "romaji"} <= set(v) for v in b.target_vocab)


def test_unknown_brief_raises():
    import pytest
    with pytest.raises(KeyError):
        get_brief("does-not-exist")
