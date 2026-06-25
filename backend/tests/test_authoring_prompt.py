from scripts.korean_authoring.briefs import get_brief
from scripts.korean_authoring.prompt import build_generation_prompt, build_review_prompt, few_shot_example


def test_few_shot_has_all_node_kinds():
    fs = few_shot_example()
    for kind in ("reading", "scene", "drill", "boss"):
        assert f'"{kind}"' in fs


def test_generation_prompt_includes_brief_and_rules():
    brief = get_brief("getting-around")
    system, user = build_generation_prompt(brief, few_shot_example())
    assert "match" in system and "listen" in system  # tap-only rule
    assert "fill" not in system or "no writing" in system.lower() or "tap-only" in system.lower()
    assert "지하철" in user  # brief vocab injected
    assert "getting-around" in user
    assert brief.boss_goal_en in user


def test_review_prompt_includes_region_json():
    brief = get_brief("getting-around")
    region = {"slug": "getting-around", "nodes": []}
    system, user = build_review_prompt(brief, region)
    assert "getting-around" in user
