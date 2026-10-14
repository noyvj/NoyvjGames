"""Round 4 phone and Desktop extras (R4-HRMO-*, R4-HRPC-*): the page code can only be tested by reading it, so these tests
check the wiring the local model got wrong before: ids that exist, classes the board really draws, code that waits for
the shell, settings that have a control."""

import json
import re
from pathlib import Path

import boards
import render

GAME_DIR = Path(__file__).resolve().parent.parent
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
STYLE = (GAME_DIR / "style.css").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
PC_HTML = (GAME_DIR / "pc.html").read_text(encoding="utf-8")

# ids app.js builds itself (none: the thumb Undo button is made with .id, not looked up)
CREATED_BY_JS = set()


def _board_and_layer():
    board = boards.BY_ID[boards.ORDER[0]]
    return board, render.board_svg(board), render.lines_svg(board, board.solution)


def test_every_id_app_js_looks_up_exists_in_the_page():
    ids = set(re.findall(r"\$\(\"([A-Za-z0-9_-]+)\"\)", APP))
    missing = [i for i in sorted(ids) if i not in CREATED_BY_JS and 'id="%s"' % i not in HTML]
    # elements the older code builds itself or reads defensively
    assert not [i for i in missing if i not in {"credits-link"}], missing


def test_one_more_button_is_real_and_wired():
    assert re.search(r'<button id="one-more-button"[^>]*\bhidden\b', HTML)
    assert '$("one-more-button").addEventListener("click"' in APP
    assert ".one-more-btn[hidden]" in STYLE and "#next-button { display: none; }" in STYLE


def test_home_progress_follows_the_real_total_not_forty():
    block = APP[APP.index("function renderHomeProgress"):APP.index("function syncThumbUndo")]
    assert "= 40" not in block and "view.totals.rooms" in block
    assert 'id="home-progress"' in HTML and "hidden" not in re.search(r'<div id="home-progress"[^>]*>', HTML).group(0)


def test_thumb_undo_and_hand_layout_have_css_and_a_sync():
    assert ".hr-undo-btn" in STYLE and "position: fixed" in STYLE[STYLE.index(".hr-undo-btn {"):]
    assert "syncThumbUndo();" in APP[APP.index("  function render() {"):APP.index("// ---- sound")]
    assert 'html[data-hand="left"]' in STYLE and 'setAttribute("data-hand"' in APP
    assert 'id="undo-button"' in HTML                                  # the original Undo button keeps its id (the Z key and tests use it)


def test_phone_settings_have_controls_in_the_page():
    assert 'id="hand-checkbox"' in HTML and 'id="big-ports-checkbox"' in HTML


def test_phone_settings_are_per_device_and_resettable():
    assert "hull-repair-hand" in APP and "hull-repair-big-ports" in APP
    engine = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    assert "hand" not in engine.lower().replace("handle", "") and "big_ports" not in engine
    reset = APP[APP.index('$("display-reset-button").addEventListener'):]
    assert "applyHand(false)" in reset[:300] and "applyBigPorts(false)" in reset[:300]


def test_big_ports_css_targets_classes_the_board_draws():
    board, svg, layer = _board_and_layer()
    assert 'class="hr-port ' in svg
    assert "#board-holder.hr-big-ports .hr-port " in STYLE


def test_finger_ghost_copies_only_a_real_line_group():
    board, svg, layer = _board_and_layer()
    assert 'g class="hr-line ' in layer and 'data-line="' in layer
    assert 'g.hr-line[data-line="' in APP
    assert "hr-dragging" not in APP and "hr-dragging" not in STYLE      # the real lines are no longer moved


def test_haptics_respect_reduced_motion_and_effects():
    block = APP[APP.index("var HR_Haptics"):APP.index("var $ =")]
    assert 'data-reduced-motion' in block and 'data-effects' in block and "navigator.vibrate" in block


def test_toast_style_is_still_there():
    assert ".toast.on {" in STYLE


def test_desktop_code_waits_for_the_shell_and_hits_real_classes():
    board, svg, layer = _board_and_layer()
    body = PC_JS[PC_JS.index("window.addEventListener(\"load\""):]
    top_level = PC_JS[:PC_JS.index("window.addEventListener(\"load\"")]
    assert "getElementById" not in top_level and "querySelector" not in top_level
    for cls in ("g.hr-port", "g.hr-line", "g.hr-room"):
        assert cls in body
    assert 'class="hr-dot"' in render.lines_svg(board, {}) and "pulse-on" in body and ".hr-dot" in PC_CSS
    assert 'g class="hr-port' in svg


def test_desktop_ids_exist_in_the_generated_page():
    for pc_id in ("pc-side", "pc-stagebar", "map-holder", "result-card", "board-holder"):
        assert ('id="%s"' % pc_id in PC_HTML) or pc_id.startswith("pc-")       # the pc-* blocks are built by shared/pc-shell.js
    assert 'src="../../shared/pc-shell.js"' in PC_HTML


def test_desktop_motion_has_reduced_motion_and_off_switches():
    assert "reducedMotion()" in PC_JS and 'data-effects") === "off"' in PC_JS
    assert 'data-reduced-motion="true"] .board-holder.pulse-on' in PC_CSS
    assert "setTimeout" not in PC_JS and "setInterval" not in PC_JS


def test_desktop_hints_list_the_new_keys():
    cfg = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    keys = [h[0] for h in cfg["hints"]]
    assert "C" in keys and "F" in keys
    assert "Focus: hide the side panels" in PC_HTML
