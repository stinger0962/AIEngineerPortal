import ast

from scripts.korean_authoring.emit import render_region_python


def test_round_trips_and_preserves_korean():
    region = {
        "slug": "demo", "title": "Demo", "theme": "transit", "order_index": 3,
        "nodes": [{"slug": "demo-x", "kind": "drill", "title": "데모", "order_index": 0,
                   "content_json": {"items": [{"type": "match", "ko": "버스", "answer": "bus", "choices": ["bus", "subway"]}]}}],
    }
    text = render_region_python(region)
    assert text.startswith("REGION = ")
    literal = text[len("REGION = "):]
    assert ast.literal_eval(literal) == region
    assert "버스" in text
