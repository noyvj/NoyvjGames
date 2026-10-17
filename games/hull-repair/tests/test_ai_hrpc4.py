"""R4-HRPC-4 (Desktop): Tab picks the next line, arrows extend it, Backspace trims it. The picking lives in app.js
(pickLine, which has the cursor) and pc.js only forwards Tab, so these tests check the wiring and the engine calls the
picking relies on (begin on the end of an unjoined line, move forward and back)."""

import json
import re
from pathlib import Path

import boards
import game


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
PC_HTML = (GAME_DIR / "pc.html").read_text(encoding="utf-8")


def test_pc_js_forwards_tab_to_the_function_app_js_defines():
    assert "window.hullRepairPickLine = pickLine;" in APP
    assert "window.hullRepairPickLine(" in PC_JS
    # the first version edited the engine-built SVG (points of a polyline that does not exist); it must not come back
    assert 'setAttribute("points"' not in PC_JS and "keyboard-active" not in PC_JS + PC_CSS


def test_tab_is_only_intercepted_when_a_line_was_picked():
    block = PC_JS[PC_JS.index("R4-HRPC-4"):PC_JS.index("R4-HRPC-10")]
    assert re.search(r"if \(window\.hullRepairPickLine\(e\.shiftKey \? -1 : 1\)\) e\.preventDefault\(\);", block)
    pick = APP[APP.index("function pickLine"):APP.index("window.hullRepairPickLine")]
    assert "return false" in pick                      # no further line: Tab leaves the board (no keyboard trap)
    assert 'state === "connected"' in pick             # a joined line is never picked back up (it would restart it)


def test_the_shortcut_is_listed_in_the_desktop_keys_and_the_page_is_current():
    assert "Pick up the next unjoined line" in PC_HTML
    assert "Extend active line" not in PC_HTML


def test_engine_calls_pickline_makes_extend_and_trim_a_line():
    fresh()
    bid = boards.ORDER[0]
    call(action="pick", board=bid)
    b = boards.BY_ID[bid]
    c = b.lines[0]
    path = b.solution[c]
    # first Tab on an empty line: begin on its source port, then an arrow (move) extends it
    assert call(action="begin", x=path[0][0], y=path[0][1])["ok"]
    assert call(action="move", cells=[list(path[1])])["ok"]
    assert call(action="end")["ok"]
    lines = {line["c"]: line for line in call(action="open")["board"]["lines"]}
    assert lines[c]["state"] == "drawing"
    # a later Tab: begin on the end of the unjoined line, extend one more cell, then Backspace (move back) trims it
    head = path[1]
    assert call(action="begin", x=head[0], y=head[1])["ok"]
    assert call(action="move", cells=[list(path[2])])["ok"]
    assert call(action="move", cells=[list(path[1])])["ok"]
    after = call(action="end")
    assert after["board"]["paths"][c] == [list(p) for p in path[:2]]
