"""Edge-case tests for hints.py public functions."""

import json

import benches
import game
import hints


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def setup_function(_fn):
    game.game.__init__()
    call(action="difficulty", level="normal")


def teardown_function(_fn):
    call(action="difficulty", level="normal")
    game.game.__init__()


def test_area_words_boundaries():
    """area_words handles zero input (0,0) and largest allowed values (bottom-right corner)."""
    bench = benches.BY_ID["c1-1"]
    assert "top left" in hints.area_words(bench, 0, 0)
    max_r, max_c = bench.board.h - 1, bench.board.w - 1
    assert "bottom right" in hints.area_words(bench, max_r, max_c)
    mid_r, mid_c = bench.board.h // 2, bench.board.w // 2
    assert "middle" in hints.area_words(bench, mid_r, mid_c)


def test_rung_cap_valid_difficulties():
    """rung_cap returns the correct cap for each difficulty level."""
    assert hints.rung_cap("normal") == 3
    assert hints.rung_cap("easy") == 3
    assert hints.rung_cap("hard") == 2


def test_next_rung_boundaries():
    """next_rung steps up correctly and returns None at the cap."""
    assert hints.next_rung(0, "normal") == 1
    assert hints.next_rung(1, "normal") == 2
    assert hints.next_rung(2, "normal") == 3
    assert hints.next_rung(3, "normal") is None
    assert hints.next_rung(0, "hard") == 1
    assert hints.next_rung(1, "hard") == 2
    assert hints.next_rung(2, "hard") is None


def test_view_clamps_rung():
    """view clamps out-of-bounds rung values to the valid range [0, cap]."""
    bench = benches.BY_ID["c1-1"]
    v_neg = hints.view(bench, -5, "normal")
    assert v_neg["rung"] == 0
    v_high = hints.view(bench, 10, "normal")
    assert v_high["rung"] == 3
    v_hard_high = hints.view(bench, 10, "hard")
    assert v_hard_high["rung"] == 2


def test_lower_first_edge_cases():
    """lower_first handles standard text and S/L prefixes correctly."""
    assert hints.lower_first("Hello") == "hello"
    assert hints.lower_first("S beam") == "S beam"
    assert hints.lower_first("L light") == "L light"
    assert hints.lower_first("mirror") == "mirror"


def test_kind_name_known_pieces():
    """kind_name returns the correct piece name for known kinds."""
    assert hints.kind_name("mirror") == "mirror"
    assert hints.kind_name("splitter") == "splitter"
    assert hints.kind_name("prism") == "prism"
    assert hints.kind_name("filter_s") == "S filter"
    assert hints.kind_name("filter_l") == "L filter"
    assert hints.kind_name("absorber") == "absorber"
