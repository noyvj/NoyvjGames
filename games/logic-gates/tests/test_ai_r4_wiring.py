"""Round 4 (local AI, audited): the engine side of the wire hover card (R4-LGPC-3), and checks that the page JS only reaches for
ids and data attributes that exist (the local model shipped several that did not)."""

import re
from pathlib import Path

from tests.helpers import call, fresh, solve

GAME = Path(__file__).resolve().parent.parent


def solve_through(level_id):
    """Fresh game, then solve every level in order up to and including level_id (levels open as chips are earned)."""
    import levels
    fresh()
    for lv in levels.LEVELS:
        v = solve(lv["id"])
        if lv["id"] == level_id:
            return v
    raise AssertionError(level_id)


def test_wire_carries_value_source_and_rows_high():
    solve_through("both")              # Y = A AND B
    v = call("flip", name="A")
    v = call("flip", name="B")         # A = B = 1
    wires = re.findall(r'<path class="lg-wire[^"]*"([^>]*)/>', v["svg"])
    assert wires, "the solved board has wires"
    for attrs in wires:
        assert 'data-value="' in attrs and 'data-src="' in attrs
    # the wire out of the AND chip is 1 only on the row A=1, B=1
    out = [a for a in wires if 'data-src="1.Y"' in a]
    assert out and 'data-value="1"' in out[0] and 'data-rows="11"' in out[0]
    # the wire from switch A is 1 on the rows where A is 1
    a_wire = [a for a in wires if 'data-src="in:A"' in a]
    assert a_wire and 'data-rows="10 11"' in a_wire[0]


def test_wire_rows_follow_the_live_value():
    solve_through("invert")            # Y = NOT A
    v0 = call("open")
    ys = [a for a in re.findall(r'<path class="lg-wire[^"]*"([^>]*)/>', v0["svg"]) if 'data-src="1.Y"' in a]
    assert ys and 'data-value="1"' in ys[0] and 'data-rows="0"' in ys[0]
    v1 = call("flip", name="A")
    ys = [a for a in re.findall(r'<path class="lg-wire[^"]*"([^>]*)/>', v1["svg"]) if 'data-src="1.Y"' in a]
    assert 'data-value="0"' in ys[0] and 'data-rows="0"' in ys[0]     # the rows do not change, the live value does


def test_sequence_levels_have_no_rows_list():
    fresh()
    from levels import LEVELS
    seq = [lv for lv in LEVELS if lv.get("steps")][0]
    # open it directly (the picker rules do not matter to the render), then check no data-rows are written
    import game
    game.meta["current"] = seq["id"]
    game.probe["prog"] = None
    v = call("open")
    assert "data-rows=" not in v["svg"]


def test_page_js_only_uses_ids_the_pages_have():
    js = (GAME / "app.js").read_text()
    for page in ("index.html", "pc.html"):
        html = (GAME / page).read_text()
        for ident in ("lg-fit-btn", "chip-drawer", "chip-drawer-handle", "chip-drawer-content", "mobile-chapter-cards", "board-holder", "board-scroll"):
            assert f'id="{ident}"' in html, (page, ident)
    for ident in re.findall(r'\$\("([a-z-]+)"\)', js):
        assert f'id="{ident}"' in (GAME / "index.html").read_text() or ident in ("announce",), ident


def test_removed_dead_code_stays_removed():
    js = (GAME / "app.js").read_text() + (GAME / "pc.js").read_text() + (GAME / "chip-drawer.js").read_text()
    for dead in ("lg-place-chip", "chip-drawer:place", "NoyvjResultSheet", "data-lg-landscape", "lg-snap-btn", "lg-selected", "LG_CONTROLS"):
        assert dead not in js, dead
    assert not (GAME / "result-sheet.js").exists()
    assert 'result-sheet' not in (GAME / "index.html").read_text()


def test_hover_card_reads_only_attributes_the_board_writes():
    pcjs = (GAME / "pc.js").read_text()
    render = (GAME / "render.py").read_text()
    for attr in ("data-value", "data-src", "data-rows"):
        assert attr in pcjs and attr in render


def test_dialog_guard_ignores_hidden_frames():
    # on pc.html every window frame is a hidden role=dialog; a shortcut guard must only count the open ones
    js = (GAME / "app.js").read_text()
    assert "[role='dialog']:not([hidden])" in js


def test_hotkey_types_exist_on_the_shelf():
    import levels
    for t in ("and", "or", "xor", "not"):
        assert t in levels.REGISTRY
