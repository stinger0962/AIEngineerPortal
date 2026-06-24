import pytest

from app.services.korean.content import REGIONS, validate_node_content


def test_validate_reading_node_ok():
    validate_node_content("reading", {
        "letters": [{"jamo": "ㅏ", "sound": "a", "audio_key": "jamo_a"}],
        "blocks": [{"ko": "가", "romaji": "ga"}],
        "words": [{"ko": "가구", "en": "furniture"}],
    })


def test_validate_scene_node_ok():
    validate_node_content("scene", {
        "setting": "airport",
        "character": "officer",
        "lines": [{"speaker": "officer", "ko": "여권이요", "romaji": "yeogwonieyo", "en": "Passport, please", "audio_key": "k1"}],
        "your_turns": [{"prompt_en": "Hand over passport", "options": ["네, 여기요"], "accepted": [{"ko": "여기요", "intents": ["here you go"]}]}],
        "new_vocab": [{"ko": "여권", "en": "passport", "romaji": "yeogwon"}],
    })


def test_validate_rejects_unknown_kind():
    with pytest.raises(ValueError):
        validate_node_content("mystery", {})


def test_validate_rejects_missing_field():
    with pytest.raises(ValueError):
        validate_node_content("boss", {"goal_en": "order coffee"})  # missing persona/level/...


def test_all_seeded_content_is_valid():
    for region in REGIONS:
        for node in region["nodes"]:
            validate_node_content(node["kind"], node["content_json"])


def test_regions_cover_0_through_2():
    slugs = {r["slug"] for r in REGIONS}
    assert {"hangul-island", "arrival", "cafe-food"} <= slugs


def test_region_node_counts():
    by_slug = {r["slug"]: r for r in REGIONS}
    assert len(by_slug["hangul-island"]["nodes"]) == 5
    assert len(by_slug["arrival"]["nodes"]) == 7
    assert len(by_slug["cafe-food"]["nodes"]) == 7


def test_node_slugs_globally_unique():
    slugs = [n["slug"] for r in REGIONS for n in r["nodes"]]
    assert len(slugs) == len(set(slugs))


def test_drills_are_tap_only_no_writing():
    for region in REGIONS:
        for node in region["nodes"]:
            if node["kind"] == "drill":
                for item in node["content_json"]["items"]:
                    assert item["type"] in {"match", "listen"}, f"writing-style drill item: {item}"
