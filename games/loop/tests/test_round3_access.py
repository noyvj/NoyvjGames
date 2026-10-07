"""Round 3 accessibility and convenience: the screen-reader cycle summary and list view (H-4), the
worked extraction price (H-15), the live tab title (H-22), the copyable summary (H-23), and static
checks on the page for the shortcuts (H-13) and the new settings (H-16, H-17, H-18)."""

import pathlib
import re
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent.parent
INDEX = (HERE / "index.html").read_text(encoding="utf-8")
SETTINGS = (HERE / "settings.js").read_text(encoding="utf-8")
CSS = (HERE / "style.css").read_text(encoding="utf-8")


def close_loop(env):
    env.chain.funds = 5000.0
    for _ in range(10):
        env.invest_circularity("recycle")


# ------------------------------------------------------------------- H-4
def test_live_region_is_empty_until_a_cycle_has_run(game_env):
    assert game_env.module.cycle_summary_text() == ""
    assert game_env.elements["cycle-live-summary"].innerText == ""


def test_first_cycle_summary_reports_the_extraction(game_env):
    game_env.advance_cycle()
    text = game_env.elements["cycle-live-summary"].innerText
    assert text == "Cycle 1 complete: 0% circular, 50 units extracted."


def test_later_summary_says_extraction_down(game_env):
    game_env.chain.funds = 5000.0
    game_env.advance_cycle()
    for _ in range(4):
        game_env.invest_circularity("recycle")  # 20 units supplied
    game_env.advance_cycle()
    text = game_env.elements["cycle-live-summary"].innerText
    assert text == "Cycle 2 complete: 40% circular, extraction down 20 units."


def test_summary_says_up_and_unchanged(game_env):
    game_env.chain.funds = 5000.0
    game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    game_env.chain.circularity_investment["recycle"] = 0
    game_env.advance_cycle()
    assert "extraction up 5 units" in game_env.elements["cycle-live-summary"].innerText
    game_env.advance_cycle()
    assert "extraction unchanged" in game_env.elements["cycle-live-summary"].innerText


def test_summary_notes_a_closed_loop_and_combo(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    game_env.advance_cycle()
    text = game_env.elements["cycle-live-summary"].innerText
    assert "Loop closed. Combo times 2." in text and "extraction unchanged" in text


def test_the_list_view_mirrors_ring_partners_and_meters(game_env):
    game_env.invest_circularity("repair")
    game_env.module.render()
    html = game_env.elements["a11y-chain-list"].innerHTML
    for expected in ("Repair Networks: 1 bought", "Reuse Systems: 0 bought", "Recycling Loops",
                     "Trade Link: 0 bought", "Overseas Consortium", "Environmental damage",
                     "Circular this cycle"):
        assert expected in html
    assert html.count("<li>") >= 9


def test_list_view_escapes_text(game_env):
    html = game_env.elements["a11y-chain-list"].innerHTML
    assert "<script" not in html


def test_page_has_the_live_region_and_list(game_env):
    assert 'id="cycle-live-summary" class="sr-only" role="status" aria-live="polite"' in INDEX
    assert 'id="a11y-chain-list"' in INDEX and ".sr-only" in CSS


# ------------------------------------------------------------------ H-15
def test_cost_equation_shows_base_multiplier_cap_and_result(game_env):
    game_env.chain.total_extracted = 250.0  # damage 50% -> multiplier 1.75
    game_env.module.render()
    text = game_env.elements["cost-equation-display"].innerText
    assert text == "Each extracted unit costs: base 2.0 x damage multiplier 1.75 (cap 2.5) = 3.50 funds."
    assert game_env.elements["cost-equation-display"].title == text


def test_cost_equation_at_the_ceiling(game_env):
    game_env.chain.total_extracted = 5000.0
    assert "x damage multiplier 2.50 (cap 2.5) = 5.00" in game_env.module.cost_equation_text()


# ------------------------------------------------------------------ H-22
def test_tab_title_follows_the_cycle_and_share(game_env):
    document = sys.modules["js"].document
    assert document.title == "Loop - C1 - 0% circular"
    game_env.chain.funds = 5000.0
    for _ in range(5):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    assert document.title == "Loop - C2 - 50% circular"


# ------------------------------------------------------------------ H-23
def test_summary_text_before_a_close(game_env):
    text = game_env.module.summary_text()
    assert text.startswith("Loop Electronics - cycle 1 - 0% circular - score 300")


def test_summary_text_after_a_close_has_a_block_row(game_env):
    close_loop(game_env)
    game_env.advance_cycle()
    game_env.advance_cycle()
    lines = game_env.module.summary_text().split("\n")
    assert lines[0].startswith("Loop Electronics - closed cycle 1 - score ")
    assert lines[1] == "██"
    assert game_env.elements["summary-text"].innerText == game_env.module.summary_text()


def test_block_row_scales_and_is_capped(game_env):
    module = game_env.module
    assert module.summary_blocks([0.0, 0.5, 1.0]) == "▁▅█"
    assert len(module.summary_blocks([1.0] * 100)) == 40
    assert module.summary_blocks([]) == ""


def test_copy_button_falls_back_to_showing_the_text(game_env):
    game_env.elements["copy-summary-button"].dispatch("click", None)
    assert game_env.elements["copy-summary-status"].innerText == "Select the text above to copy it."


def test_copy_button_uses_the_clipboard_when_there(game_env):
    written = []
    clip = types.SimpleNamespace(writeText=lambda text: written.append(text))
    sys.modules["js"].navigator = types.SimpleNamespace(clipboard=clip)
    try:
        game_env.elements["copy-summary-button"].dispatch("click", None)
    finally:
        del sys.modules["js"].navigator
    assert written == [game_env.module.summary_text()]
    assert game_env.elements["copy-summary-status"].innerText == "Copied to the clipboard."


# ------------------------------------------------------------------ H-13
def test_shortcuts_map_to_real_buttons_and_are_listed_in_help():
    for key, button in (("' '", "advance-cycle-button"), ('"1"', "repair-invest-button"),
                        ('"2"', "reuse-invest-button"), ('"3"', "recycle-invest-button"),
                        ("t", "trade-link-invest-button")):
        assert f'id="{button}"' in INDEX
    block = INDEX[INDEX.index("H-13: game shortcuts"):]
    for button in ("advance-cycle-button", "repair-invest-button", "reuse-invest-button",
                   "recycle-invest-button", "trade-link-invest-button"):
        assert f'"{button}"' in block
    for line in ("Space — advance the cycle", "1 / 2 / 3", "T — buy a Trade Link"):
        assert line in INDEX


def test_shortcuts_stay_quiet_while_typing_or_over_dialogs():
    block = INDEX[INDEX.index("H-13: game shortcuts"):]
    assert "INPUT|TEXTAREA|SELECT|BUTTON|A|SUMMARY" in block
    for blocker in ("#opening-screen", "#tutorial-overlay", ".confirm-dialog-overlay", "#pc-backdrop"):
        assert blocker in block


def test_desktop_bar_lists_the_shortcuts():
    import json
    hints = json.loads((HERE / "pc-config.json").read_text())["hints"]
    keys = [h[0] for h in hints]
    assert "Space" in keys and "1 2 3" in keys and "T" in keys


# ------------------------------------------------------- H-16 / H-17 / H-18
def test_settings_panel_has_the_new_controls():
    for control in ("high-contrast-checkbox", "dyslexia-font-checkbox", "flow-speed-off-button",
                    "flow-speed-slow-button", "flow-speed-normal-button", "flow-speed-fast-button"):
        assert f'id="{control}"' in INDEX
        assert control in SETTINGS or control.startswith("flow-speed")
    assert '"flow-speed-" + name + "-button"' in SETTINGS


def test_settings_persist_and_reset():
    for key in ("loop-high-contrast", "loop-dyslexia-font", "loop-flow-speed"):
        assert key in SETTINGS
    reset = SETTINGS[SETTINGS.index("settingsResetButton.addEventListener"):]
    for call in ("applyContrast(false)", "applyDyslexia(false)", "applyFlowSpeed(DEFAULT_FLOW_SPEED)"):
        assert call in reset


def test_css_honours_every_new_setting():
    for selector in ('html[data-high-contrast="true"]', 'html[data-dyslexia-font="true"]',
                     'html[data-flow-speed="off"]', 'html[data-flow-speed="slow"]',
                     'html[data-flow-speed="fast"]'):
        assert selector in CSS
    # high contrast has a light-theme variant and drops the starfield
    assert 'html[data-high-contrast="true"][data-theme="light"]' in CSS
    assert 'html[data-high-contrast="true"] .ambient-bg { display: none; }' in CSS


def test_every_new_page_id_exists_in_the_desktop_page_too():
    pc = (HERE / "pc.html").read_text(encoding="utf-8")
    ids = set(re.findall(r'\bid="([^"]+)"', INDEX))
    assert ids <= set(re.findall(r'\bid="([^"]+)"', pc))
    for needed in ("career-panel", "insurance-button", "goods-category-shipyard-button", "near-miss-display"):
        assert needed in ids
