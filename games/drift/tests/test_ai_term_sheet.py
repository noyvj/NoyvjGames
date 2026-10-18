"""R4-DRMO-9 wiring checks: the phone term sheet opened by a long-press on a Terms chip.

Compares what index.html, pc.html, style.css, ui.js and game.py's GLOSSARY each assume about the other.
The first version of this idea used setTimeout (the hold is now measured with event.timeStamp), looked
up four ids that did not match its own markup, and stored its own copy of the definitions."""
import ast
import html as htmllib
import re
from pathlib import Path

from .pagefiles import game_css, game_source

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text()
PC_HTML = (GAME_DIR / "pc.html").read_text()
CSS = game_css()
UI = (GAME_DIR / "ui.js").read_text()
GAME_PY = game_source()


def term_js():
    start = UI.index("function termSheet")
    return UI[start:]


def glossary():
    for node in ast.parse(GAME_PY).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "GLOSSARY":
            return ast.literal_eval(node.value)
    raise AssertionError("GLOSSARY not found in game.py")


def sheet_css():
    return CSS[CSS.index("R4-DRMO-9"):]


def phone_block(css):
    """The text of the first `@media (max-width: 600px) { ... }` block in css (brace matched)."""
    start = css.index("@media (max-width: 600px) {")
    depth = 0
    for i in range(css.index("{", start), len(css)):
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        if depth == 0:
            return css[start:i + 1]
    raise AssertionError("unbalanced css")


def test_every_id_the_script_looks_up_exists_in_both_pages():
    ids = re.findall(r'getElementById\("([^"]+)"\)', term_js())
    assert set(ids) == {"glossary-sheet", "glossary-sheet-title", "glossary-sheet-text", "glossary-sheet-more",
                        "glossary-sheet-close", "glossary-sheet-open", "glossary-more-button", "info-page-panel"}
    for page in (HTML, PC_HTML):
        for id_ in ids:
            assert f'id="{id_}"' in page, id_


def test_sheet_is_an_accessible_hidden_dialog_outside_the_game_card():
    tag = re.search(r'<div id="glossary-sheet"[^>]*>', HTML).group(0)
    for needle in ('role="dialog"', 'aria-labelledby="glossary-sheet-title"', 'tabindex="-1"', " hidden"):
        assert needle in tag, needle
    assert 'id="glossary-sheet-title"' in HTML
    # Not inside #game (that card is a fixed-position containing block on some layouts) and before the ad bar
    assert HTML.index('id="neighbor-panel"') < HTML.index('id="glossary-sheet"') < HTML.index("ad-bar--bottom")


def test_definitions_on_the_terms_equal_the_game_glossary():
    for term, entry in glossary().items():
        tag = re.search(r'<button id="glossary-%s-button"[^>]*>' % term, HTML).group(0)
        text = re.search(r'data-term-def="([^"]*)"', tag).group(1)
        assert htmllib.unescape(text) == entry["text"], term
        assert htmllib.unescape(re.search(r'data-term-label="([^"]*)"', tag).group(1)) == entry["label"]
        assert ("data-real-story" in tag) == entry["real_story"], term


def test_no_timers_the_hold_is_measured_with_event_timestamps():
    js = term_js()
    assert "setTimeout" not in js and "setInterval" not in js and "requestAnimationFrame" not in js
    assert "event.timeStamp - started.t >= HOLD_MS" in js
    assert "t: event.timeStamp" in js
    assert "setTimeout" not in CSS and "setTimeout" not in UI


def test_a_long_press_does_not_also_toggle_the_popover_and_a_tap_still_does():
    js = term_js()
    # The row's capture-phase click listener swallows only the click that follows a long-press; the keyboard
    # (detail 0) is never swallowed, and a new pointerdown or keydown clears the flag.
    assert "}, true);" in js and "swallowClick && event.detail !== 0" in js
    assert js.count("swallowClick = false") >= 3
    # game.py's own tap / hover / focus handlers on the terms are still the ones registered
    assert '_make_glossary_handler(term, "click")' in GAME_PY


def test_keyboard_and_screen_reader_path():
    js = term_js()
    assert '"contextmenu"' in js                         # Menu key / Shift+F10 on a focused term, and touch long-press
    assert 'event.key === "Escape"' in js and "close(true)" in js
    assert 'event.key !== "Tab"' in js                   # Tab stays inside the sheet
    assert "opener.focus" in js and "sheet.focus" in js  # focus moves in, returns on close
    assert "glossary-sheet-open" in HTML                 # the visible button next to the term popover
    open_btn = re.search(r'<button id="glossary-sheet-open"[^>]*>([^<]*)</button>', HTML)
    assert open_btn and "bottom sheet" in open_btn.group(1)
    assert HTML.index('id="glossary-pop"') < HTML.index('id="glossary-sheet-open"') < HTML.index('id="glossary-sheet"')


def test_real_story_link_goes_through_the_popovers_own_button():
    js = term_js()
    assert "storyBtn.click()" in js
    assert "info-page-toggle-button" not in js  # on_glossary_more in game.py decides open/closed, as before
    assert "def on_glossary_more" in GAME_PY


def test_phone_rules_live_inside_the_phone_media_block():
    css = sheet_css()
    before_media = css[:css.index("@media")]
    # Outside the block the sheet and its keyboard button are simply not displayed
    assert ".glossary-sheet, .glossary-sheet-open { display: none; }" in before_media
    block = phone_block(css)
    for needle in ("position: fixed", ".glossary-sheet[hidden] { display: none; }", "z-index: 300",
                   ".glossary-sheet-open { display: inline-block"):
        assert needle in block, needle
    assert "display: block;" in block
    # clears the 50px ad bar, the pinned Advance Round button (66px up) and the floating theme / story buttons
    # on the left, whose tops are about 162px above the bottom edge (the browser test measures the real overlap)
    bottom = int(re.search(r"bottom: calc\((\d+)px \+ env", block).group(1))
    assert bottom >= 166


def test_motion_and_lite_mode():
    css = sheet_css()
    assert "prefers-reduced-motion: no-preference" in css
    anim = css[css.index("@media (max-width: 600px) and (prefers-reduced-motion: no-preference)"):]
    assert "animation: glossary-sheet-in" in anim
    for off in ("html.reduce-motion .glossary-sheet", "html.lite-mode .glossary-sheet", 'html[data-anim-speed="off"] .glossary-sheet'):
        assert off in anim
    # no transition-based slide that a [hidden] toggle could skip, and nothing outside the block animates it
    assert "transition" not in css[:css.index("@keyframes")]


def test_no_new_setting_so_nothing_to_reset():
    # The sheet is not switchable; if a setting is ever added it needs a control and a reset in settings.js
    assert "glossary-sheet" not in (GAME_DIR / "settings.js").read_text()
