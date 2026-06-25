from pathlib import Path

from scripts.korean_authoring.cli import main


def test_dry_run_emits_clean_region(tmp_path, capsys):
    rc = main(["getting-around", "--dry-run"])
    assert rc == 0
    out = Path(__file__).resolve().parents[1] / "scripts" / "korean_authoring" / "out" / "getting-around.py"
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("REGION = ")
    assert "getting-around-boss" in text
    captured = capsys.readouterr().out
    assert "emitted" in captured


def test_dry_run_unknown_slug_errors():
    rc = main(["nope", "--dry-run"])
    assert rc == 2
