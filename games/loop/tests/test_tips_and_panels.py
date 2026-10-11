"""H-30 Replay tips and H-21 collapse chevrons with memory."""

import pathlib
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent.parent
JS = (HERE / "settings.js").read_text(encoding="utf-8")
CSS = (HERE / "style.css").read_text(encoding="utf-8")
HTML = (HERE / "index.html").read_text(encoding="utf-8")
PC_JS = (HERE / "pc.js").read_text(encoding="utf-8")


class FakeStorage:
    def __init__(self):
        self.removed = []

    def removeItem(self, key):
        self.removed.append(key)


def with_window():
    storage = FakeStorage()
    sys.modules["js"].window = types.SimpleNamespace(localStorage=storage)
    return storage


def teardown_window():
    if hasattr(sys.modules.get("js"), "window"):
        del sys.modules["js"].window


# ------------------------------------------------------------------ H-30
def test_replay_tips_brings_the_regional_hint_back(game_env):
    m = game_env.module
    game_env.chain.funds = 100.0
    m.on_dismiss_regional_hint()
    assert m.regional_hint_seen is True
    assert game_env.elements["regional-hint"].hidden is True
    game_env.elements["replay-tips-button"].dispatch("click", None)
    assert m.regional_hint_seen is False
    assert game_env.elements["regional-hint"].hidden is False  # affordable and not yet seen
    assert "Tips reset" in game_env.elements["replay-tips-status"].innerText


def test_replay_tips_clears_the_tutorial_seen_flag_in_the_browser(game_env):
    storage = with_window()
    try:
        game_env.elements["replay-tips-button"].dispatch("click", None)
    finally:
        teardown_window()
    assert storage.removed == ["tutorial-seen:loop"]


def test_replay_tips_survives_a_browser_without_storage(game_env):
    sys.modules["js"].window = types.SimpleNamespace(localStorage=object())  # no removeItem
    try:
        game_env.elements["replay-tips-button"].dispatch("click", None)
    finally:
        teardown_window()
    assert "Tips reset" in game_env.elements["replay-tips-status"].innerText


def test_replay_tips_changes_nothing_in_the_game(game_env):
    m = game_env.module
    game_env.chain.funds = 77.0
    game_env.advance_cycle()
    before = {k: v for k, v in m.get_state().items() if k != "regional_hint_seen"}
    game_env.elements["replay-tips-button"].dispatch("click", None)
    after = {k: v for k, v in m.get_state().items() if k != "regional_hint_seen"}
    assert before == after


def test_the_button_is_in_settings_on_both_pages():
    for name in ("index.html", "pc.html"):
        text = (HERE / name).read_text(encoding="utf-8")
        settings = text.split('id="settings-panel"')[1].split("</div>\n\n")[0]
        assert 'id="replay-tips-button"' in settings


# ------------------------------------------------------------------ H-21
def test_every_fold_out_remembers_its_state():
    assert 'document.querySelectorAll("details[id]")' in JS
    assert '"toggle"' in JS and "loop-panel-open:" in JS
    for ident in ("stats-panel", "audit-panel", "career-panel", "passport-panel", "ledger-panel", "rival-panel",
                  "past-chains-panel", "network-map-panel", "a11y-chain-panel"):
        assert f'id="{ident}"' in HTML


def test_the_five_main_panels_get_chevrons_only_in_the_classic_layout():
    for ident in ("chain-flow-section", "status", "circularity", "trade-network", "pool-section"):
        assert f'["{ident}",' in JS
        assert f'id="{ident}"' in HTML
    assert 'getAttribute("data-layout") === "pc"' in JS
    assert 'html[data-layout="pc"] .panel-chevron { display: none; }' in CSS


def test_a_collapsed_panel_keeps_its_live_region_and_a_visible_label():
    assert ":not(.panel-chevron):not(.sr-only)" in CSS
    assert "panel-chevron-label" in JS and ".section.is-collapsed > .panel-chevron .panel-chevron-label { display: inline; }" in CSS
    assert 'setAttribute("aria-expanded"' in JS and 'setAttribute("aria-label"' in JS


def test_the_desktop_defaults_only_apply_when_nothing_is_remembered():
    assert "remembered(" in PC_JS
    assert "!remembered(\"network-map-panel\")" in PC_JS and "!remembered(\"relabel-goods-panel\")" in PC_JS
