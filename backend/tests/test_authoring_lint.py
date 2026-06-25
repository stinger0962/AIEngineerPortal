from scripts.korean_authoring.lint import validate_region


def _good_region():
    return {
        "slug": "demo", "title": "Demo", "theme": "transit", "order_index": 3,
        "nodes": [
            {"slug": "demo-scene", "kind": "scene", "title": "S", "order_index": 0, "content_json": {
                "setting": "bus", "character": "driver",
                "lines": [{"speaker": "driver", "ko": "어디 가세요?", "romaji": "eodi gaseyo", "en": "Where to?", "audio_key": "a"}],
                "your_turns": [{"prompt_en": "Say downtown", "options": ["시내요"], "accepted": [{"ko": "시내요", "intents": ["downtown"]}]}],
                "new_vocab": [{"ko": "시내", "en": "downtown", "romaji": "sinae"}],
            }},
            {"slug": "demo-drill", "kind": "drill", "title": "D", "order_index": 1, "content_json": {
                "items": [{"type": "match", "ko": "버스", "answer": "bus", "choices": ["bus", "subway"]}],
            }},
            {"slug": "demo-boss", "kind": "boss", "title": "B", "order_index": 2, "content_json": {
                "goal_en": "ride one stop", "persona": "taxi_driver", "level": "beginner",
                "allowed_vocab": ["버스", "지하철"], "success_criteria": "rides", "max_turns": 8,
            }},
        ],
    }


def test_good_region_passes():
    assert validate_region(_good_region()) == []


def test_writing_drill_flagged():
    r = _good_region()
    r["nodes"][1]["content_json"]["items"] = [{"type": "fill", "prompt": "x", "answer": "버스"}]
    issues = validate_region(r)
    assert any("drill" in i for i in issues)


def test_choice_missing_answer_flagged():
    r = _good_region()
    r["nodes"][1]["content_json"]["items"][0]["choices"] = ["subway", "train"]
    assert any("choices" in i for i in validate_region(r))


def test_unknown_persona_flagged():
    r = _good_region()
    r["nodes"][2]["content_json"]["persona"] = "wizard"
    assert any("persona" in i for i in validate_region(r))


def test_unprefixed_slug_flagged():
    r = _good_region()
    r["nodes"][0]["slug"] = "scene"
    assert any("prefix" in i for i in validate_region(r))


def test_scene_missing_romaji_flagged():
    r = _good_region()
    r["nodes"][0]["content_json"]["lines"][0]["romaji"] = ""
    assert any("romaji" in i for i in validate_region(r))


def test_noncontiguous_order_flagged():
    r = _good_region()
    r["nodes"][2]["order_index"] = 5
    assert any("order_index" in i for i in validate_region(r))
