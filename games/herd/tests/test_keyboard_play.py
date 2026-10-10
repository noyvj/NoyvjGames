"""F-10 (keyboard and screen-reader play): arrow keys on the buy buttons, the shortcut cheat sheet
in How to Play, the extra lines in the "?" overlay. The behaviour is plain JS in settings.js, so
these tests pin the wiring; the live key presses are covered by the build notes in CLAUDE.md."""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SETTINGS_JS = (HERE / "settings.js").read_text(encoding="utf-8")
INDEX_HTML = (HERE / "index.html").read_text(encoding="utf-8")
PC_HTML = (HERE / "pc.html").read_text(encoding="utf-8")


def _lever_ids():
    block = re.search(r"const LEVER_SELECTOR = \[(.*?)\]\.join", SETTINGS_JS, re.S).group(1)
    return re.findall(r'"#([a-z-]+)"', block)


def test_every_lever_button_in_the_arrow_list_exists_on_both_pages():
    ids = _lever_ids()
    assert len(ids) >= 12
    for id_ in ids:
        assert f'id="{id_}"' in INDEX_HTML, id_
        assert f'id="{id_}"' in PC_HTML, id_


def test_the_bulk_stepper_group_exists_for_left_right_arrows():
    assert 'id="bulk-stepper"' in INDEX_HTML and 'role="group"' in INDEX_HTML
    assert 'const STEPPER_SELECTOR = "#bulk-stepper button"' in SETTINGS_JS


def test_arrow_keys_are_handled_and_modifier_chords_are_left_alone():
    for key in ("ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End"):
        assert key in SETTINGS_JS
    assert "event.ctrlKey" in SETTINGS_JS and "event.metaKey" in SETTINGS_JS and "event.altKey" in SETTINGS_JS
    assert "event.preventDefault()" in SETTINGS_JS


def test_cheat_sheet_lists_each_shortcut_and_is_rebuilt_if_the_panel_is_redrawn():
    for label in ("Tab / Shift + Tab", "Up / Down arrow", "Home / End", "Left / Right arrow", "Esc"):
        assert label in SETTINGS_JS
    assert "new MutationObserver(ensure).observe(howto" in SETTINGS_JS
    assert ".howto-keys" in (HERE / "style.css").read_text(encoding="utf-8")


def test_the_question_mark_overlay_gets_herds_own_lines():
    assert "extra: [" in INDEX_HTML and "Up / Down arrow: move between the buy buttons" in INDEX_HTML


def test_grow_herd_button_announces_the_keyboard_tip():
    assert 'aria-describedby="lever-keys-hint"' in INDEX_HTML
    assert 'id="lever-keys-hint" class="sr-only"' in INDEX_HTML
