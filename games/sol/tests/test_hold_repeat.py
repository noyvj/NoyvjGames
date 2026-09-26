"""U11 (planning/TODO.md): hold-to-repeat for the mining click and the
Auto-Miner/Recycler buy buttons.

The behaviour lives in hold-repeat.js (plain DOM JS, like settings.js), so
there's no Python function to unit-test; these tests pin the structural
contract instead -- the file is wired in, the setting exists, every world's
buttons are covered by its selector, the pace can never beat manual
clicking, and the preference stays out of the save payload. The timing
itself was verified live in a browser (a 2.1s hold produced 7 repeats, a
tap produced exactly 1, and the checkbox switched it off).
"""

import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _read(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def test_hold_repeat_script_is_included_after_settings():
    html = _read("index.html")
    assert '<script src="hold-repeat.js"></script>' in html
    assert html.index("settings.js") < html.index("hold-repeat.js")


def test_settings_panel_has_the_hold_repeat_checkbox_on_by_default():
    html = _read("index.html")
    assert re.search(r'<input type="checkbox" id="hold-repeat-checkbox" checked>', html)


def test_selector_covers_every_worlds_click_and_buy_buttons():
    html = _read("index.html")
    js = _read("hold-repeat.js")
    ids = re.findall(r'id="([a-z-]*(?:click|buy-generator|buy-recycler)-button)"', html)
    assert len(ids) >= 24  # 8 worlds x 3 buttons
    for suffix in ("click-button", "buy-generator-button", "buy-recycler-button"):
        assert f'[id$="{suffix}"]' in js
    # Nothing outside those three families is ever repeated.
    assert all(i.endswith(("click-button", "buy-generator-button", "buy-recycler-button")) for i in ids)


def test_pace_is_gentle_never_faster_than_a_quick_manual_clicker():
    js = _read("hold-repeat.js")
    interval = int(re.search(r"HOLD_INTERVAL_MS = (\d+)", js).group(1))
    delay = int(re.search(r"HOLD_DELAY_MS = (\d+)", js).group(1))
    assert interval >= 200  # at most 5 a second
    assert delay >= 300  # a plain press-and-release is never mistaken for a hold


def test_preference_is_browser_level_not_save_state():
    js = _read("hold-repeat.js")
    assert "localStorage" in js
    assert "get_state" not in js and "load_state" not in js
    assert "hold-repeat" not in _read("game.py")


def test_keyboard_repeat_is_swallowed_so_enter_cannot_out_click_the_timer():
    js = _read("hold-repeat.js")
    assert "event.repeat" in js and "preventDefault" in js
