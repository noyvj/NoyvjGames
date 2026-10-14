"""Wiring checks for the Round 4 page features (breakpoints, speed slider, medals table, haptics, swipe-to-delete, speed chip,
chapter cards, pinch zoom, hint sheet): every id a script looks up exists, every event is sent and heard on the same
target, every engine action the page sends exists, and the new scripts are loaded by both pages."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
READ = lambda name: (GAME_DIR / name).read_text(encoding="utf-8")  # noqa: E731
HTML = READ("index.html")
PC_HTML = READ("pc.html")
APP = READ("app.js")
GAME_PY = READ("game.py")
NEW_SCRIPTS = ("haptics.js", "swipe.js", "hint-sheet.js", "zoom.js")
# ids the scripts build themselves before they use them
CREATED = {"undo-bar", "undo-bar-button", "hint-sheet", "hint-sheet-close", "hint-sheet-lines", "hint-sheet-reveal",
           "hint-sheet-answer", "hint-sheet-note", "zoom-fit-button", "playback-slider"}


def ids_in(html):
    return set(re.findall(r'\bid="([^"]+)"', html))


def test_every_id_a_script_looks_up_exists_in_the_page():
    have = ids_in(HTML) | CREATED
    for name in NEW_SCRIPTS + ("pc.js", "app.js"):
        text = READ(name)
        for found in re.findall(r'(?:getElementById|\$)\("([^"]+)"\)', text):
            assert found in have, "%s looks up #%s but nothing defines it" % (name, found)


def test_new_scripts_are_loaded_by_both_pages_and_not_audio():
    for page in (HTML, PC_HTML):
        for name in NEW_SCRIPTS:
            assert '<script src="%s"></script>' % name in page
    assert not (GAME_DIR / "sound.js").exists()
    for name in NEW_SCRIPTS:
        assert "AudioContext" not in READ(name) and "new Audio" not in READ(name)


def test_pc_config_windows_and_icons_point_at_real_elements():
    cfg = json.loads(READ("pc-config.json"))
    have = ids_in(HTML)
    for panel, toggle, _title in cfg["windows"]:
        assert panel in have and toggle in have, (panel, toggle)
    for icon_id, _glyph in cfg["toolbar"]["icons"]:
        assert icon_id in have, icon_id
    assert "snippets-panel" not in json.dumps(cfg) and "compare-toggle-button" not in json.dumps(cfg)


def test_custom_events_are_sent_and_heard_on_document():
    sources = {name: READ(name) for name in NEW_SCRIPTS + ("pc.js", "app.js")}
    events = set()
    for text in sources.values():
        events |= set(re.findall(r'new CustomEvent\("(robotScript\w+)"', text))
    assert events >= {"robotScriptSwipeDelete", "robotScriptSwipeUndo", "robotScriptHintRequest", "robotScriptHintAnswer",
                      "robotScriptHints", "robotScriptPlaybackSpeedChange", "robotScriptFrameStep"}
    joined = "\n".join(sources.values())
    for event in events:
        assert 'document.dispatchEvent(new CustomEvent("%s"' % event in joined, event
        assert 'document.addEventListener("%s"' % event in joined, event
        assert 'window.dispatchEvent(new CustomEvent("%s"' % event not in joined


def test_every_engine_action_the_page_sends_exists():
    actions = set(re.findall(r'action: "(\w+)"', APP))
    assert actions, "app.js sends no actions?"
    for action in actions:
        assert ('action == "%s"' % action) in GAME_PY or ('"%s"' % action) in GAME_PY, action
    assert "load_draft" not in APP


def test_medals_panel_is_reachable_and_drawn():
    assert 'id="medals-toggle-button"' in HTML and 'id="medals-panel"' in HTML and 'id="medals-body"' in HTML
    assert 'wirePanelToggle("medals-toggle-button", "medals-panel")' in APP
    assert "renderMedals();" in APP and "function renderMedals" in APP


def test_breakpoints_pause_a_playing_run_only():
    assert "window.ROBOT_SCRIPT_breakpoints" in READ("pc.js") and "breakpointSet().has(next[7])" in APP
    advance = APP[APP.index("function advance()"):APP.index("function finishRun()")]
    assert "play.running" in advance and "play.bpAt" in advance


def test_reduced_motion_and_effects_gate_the_haptics():
    text = READ("haptics.js")
    assert 'data-reduced-motion") === "true"' in text and 'data-effects") === "off"' in text
    assert "navigator.vibrate" in text


def test_zoom_is_a_css_variable_so_a_redrawn_svg_keeps_it():
    assert "--room-zoom" in READ("zoom.js") and "var(--room-zoom" in READ("style.css")
    assert 'style.setProperty("--room-zoom"' in READ("zoom.js")
    assert "SVG.style" not in READ("zoom.js")


def test_a_hidden_dialog_never_blocks_the_keyboard_shortcuts():
    """The Desktop shell keeps every window frame in the page as a hidden role=dialog and the hint sheet is always built, so the
    shortcut guard must only count dialogs that are showing."""
    assert "[role='dialog']:not([hidden])" in APP and "[role='dialog']\")" not in APP
    assert 'setAttribute("role", "dialog")' not in READ("hint-sheet.js")
    assert "[role='dialog']:not([hidden])" in READ("pc.js")


def test_resume_keeps_the_breakpoint_it_stopped_at_and_the_robot_where_it_is():
    start = APP[APP.index("function startPlay("):APP.index("function onRun()")]
    assert "if (i === undefined) play.bpAt = -1;" in start
    assert "applyFrame(play.frames[play.i], true);" in start
