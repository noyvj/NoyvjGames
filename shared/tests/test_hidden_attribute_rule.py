"""Regression guard for playtest audit S2 (2026-10-06): every stylesheet must
keep a blanket `[hidden] { display: none !important; }` so a class-level
`display:` rule can never make a hidden element visible again."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEETS = [ROOT / "style.css", *sorted((ROOT / "games").glob("*/style.css"))]


def test_every_stylesheet_has_the_blanket_hidden_rule():
    assert len(SHEETS) == 14
    for sheet in SHEETS:
        css = sheet.read_text(encoding="utf-8")
        assert "[hidden] { display: none !important; }" in css, sheet
