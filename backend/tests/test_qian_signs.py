from app.services.qian.signs import all_signs, get_sign
from app.services.qian.draw import draw_sign


def test_corpus_complete():
    signs = all_signs()
    assert len(signs) == 100
    ids = sorted(s["id"] for s in signs)
    assert ids == list(range(1, 101))
    for s in signs:
        for f in ("grade", "palace", "title", "poetry", "meaning", "holy"):
            assert s[f] and isinstance(s[f], str), f"sign {s['id']} 字段 {f} 为空"


def test_get_sign():
    assert get_sign(1)["id"] == 1
    assert get_sign(999) is None


def test_draw_in_range():
    seen = set()
    for _ in range(300):
        s = draw_sign()
        assert 1 <= s["id"] <= 100
        seen.add(s["id"])
    assert len(seen) > 30
