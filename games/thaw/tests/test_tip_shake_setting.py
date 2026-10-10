"""GG-12: the opt-in shake and crack setting (settings.js and CSS, so these are file-level checks)."""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _read(name):
    return (BASE / name).read_text(encoding="utf-8")


def test_checkbox_exists_on_both_pages_and_is_unchecked_by_default():
    for name in ("index.html", "pc.html"):
        page = _read(name)
        assert 'id="tip-shake-checkbox"' in page
        assert 'id="tip-shake-checkbox" checked' not in page


def test_setting_is_wired_and_stored():
    js = _read("settings.js")
    assert '"thaw-tip-shake"' in js and 'data-tip-shake' in js and "tip-shake-checkbox" in js
    # reset-to-default clears every flag, including this one
    assert "resetFlags" in js and "FLAGS.forEach" in js


def test_css_only_acts_when_the_setting_is_on():
    css = _read("style.css")
    block = css[css.index("GG-12: opt-in tremor"):]
    assert block.count('html[data-tip-shake="true"]') >= 4
    assert "@keyframes tip-tremor" in block and "@keyframes tip-crack" in block


def test_css_switches_it_off_for_reduced_motion_and_lite_mode():
    css = _read("style.css")
    block = css[css.index("GG-12: opt-in tremor"):]
    assert 'html[data-reduced-motion="true"][data-tip-shake="true"]' in block
    assert 'html[data-lite="true"][data-tip-shake="true"]' in block
    assert "prefers-reduced-motion: reduce" in block


def test_it_reuses_the_existing_tipping_cue_without_new_game_logic(game_env):
    game_env.region.temperature = 9.5
    game_env.advance_round()
    assert game_env.elements["game"].className == "tipping-flash"
