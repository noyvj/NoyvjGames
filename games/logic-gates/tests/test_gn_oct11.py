"""GN-5 (par shows on the Desktop page too) and GN-6 (what tie 1 and tie 0 are, said in plain words)."""

import json
import re
from pathlib import Path

import words
from tests.helpers import call

GAME_DIR = Path(__file__).resolve().parent.parent
CLASSIC = (GAME_DIR / "index.html").read_text(encoding="utf-8")
DESKTOP = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
CONFIG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))


# --- GN-5 ---------------------------------------------------------------------------------------------------------

def test_every_level_view_carries_its_par():
    call("reset")
    v = call("start", level="straight-through")
    assert isinstance(v["level"]["par"], int)


def test_both_pages_have_the_par_line_and_the_stats_par_counter():
    for html in (CLASSIC, DESKTOP):
        assert 'id="level-unlock"' in html and 'id="stat-par"' in html


def test_the_desktop_stage_bar_shows_the_par_line_the_classic_page_shows():
    assert "#level-head" in CONFIG["zones"]["stagebar"] and "#status-strip" in CONFIG["zones"]["stagebar"]
    hidden = re.search(r"([^{}]*)\{\s*display:\s*none;?\s*\}", PC_CSS)
    for rule in re.findall(r"([^{}]+)\{\s*display:\s*none;?\s*\}", PC_CSS):
        assert "#level-unlock" not in rule, rule
    assert hidden is not None  # the other level-head pieces stay folded away
    assert re.search(r"#pc-stagebar #level-unlock\s*\{[^}]*display:\s*inline", PC_CSS)


def test_the_par_text_is_written_into_that_line_by_the_one_renderer_both_pages_share():
    assert 'setText($("level-unlock")' in APP and '"Par is "' in APP


# --- GN-6 ---------------------------------------------------------------------------------------------------------

def test_the_two_tie_boxes_on_the_drawing_carry_a_plain_tooltip():
    call("reset")
    v = call("start", level="straight-through")
    svg = v["svg"]
    for value in ("0", "1"):
        tip = words.TIE_TIPS[value]
        assert f"<title>{tip}</title>" in svg
        assert "fixed input" in tip and f"tied to {value}" in tip and "constant" in tip


def test_the_tooltips_have_no_markup_or_jargon_beyond_the_games_own_words():
    for tip in words.TIE_TIPS.values():
        assert "<" not in tip and ">" not in tip and "&" not in tip
        assert tip.endswith(".") and len(tip) < 220


def test_the_board_key_and_both_tutorials_explain_the_tie_parts():
    for html in (CLASSIC, DESKTOP):
        assert 'id="tie-key"' in html and "fixed inputs" in html
    assert 'title: "Tie 1 and tie 0"' in APP
    assert 'title: "Tie 1 and tie 0"' in PC_JS
    assert words.TIE_KEY in CLASSIC
