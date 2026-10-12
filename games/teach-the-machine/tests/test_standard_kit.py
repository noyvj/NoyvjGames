"""Milestone 5: the standard kit on the page (opening screen, tutorial with a toolbar restart button, About with sources, What's New,
keyboard help, confirm dialogs, light theme, accessibility basics). The page is plain files, so these tests read them."""

import json
import re
from pathlib import Path

import info

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
IDS = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))


# ---- opening screen ----------------------------------------------------------------------------------------------------
def test_the_opening_screen_is_included_after_the_save_widget_with_the_games_name():
    tail = HTML[HTML.index("pyodide.js"):]
    assert tail.index("shared/save-widget.js") < tail.index("shared/opening-screen.js") < tail.index("shared/confirm-dialog.js")
    assert tail.index("shared/tutorial.js") < tail.index("shared/save-widget.js")
    include = re.search(r'<script src="../../shared/opening-screen.js"[^>]*>', tail).group(0)
    assert 'data-game-id="teach-the-machine"' in include and 'data-game-name="Teach the Machine"' in include and "data-tagline=" in include


def test_the_page_loads_the_standard_kit_in_the_order_the_siblings_do():
    tail = HTML[HTML.index("pyodide.js"):]
    order = ["shared/tutorial.js", "shared/hub-auth.js", "shared/save-widget.js", "shared/opening-screen.js", "shared/confirm-dialog.js",
             'src="app.js"', "shared/last-played.js", "shared/whats-new-banner.js", "shared/keyboard-shortcuts.js"]
    positions = [tail.index(name) for name in order]
    assert positions == sorted(positions)


def test_new_game_starts_clean_but_keeps_the_old_copy_and_continue_keeps_it():
    """boot waits for the opening screen's answer; a New Game clears the local copy (after keeping it under its own key), Continue loads it."""
    assert "window.NoyvjOpeningScreen.choice" in APP and 'choice === "new"' in APP
    boot = APP[APP.index("async function boot()"):]
    assert boot.index("NoyvjOpeningScreen") < boot.index("loadState(")                       # the answer comes before any state is loaded
    assert "BEFORE_NEW_KEY" in boot and "removeItem(STORE_KEY)" in boot
    assert 'teach-the-machine:state-before-new-game' in APP


# ---- tutorial ----------------------------------------------------------------------------------------------------------
def test_the_tutorial_has_a_toolbar_restart_button_and_the_desktop_hook():
    assert 'id="tutorial-restart-button"' in HTML
    toolbar = HTML[HTML.index('class="game-toolbar"'):HTML.index("</div>", HTML.index('class="game-toolbar"'))]
    assert "tutorial-restart-button" in toolbar
    assert "GameTutorial.init(window.teachTheMachineTutorialSteps ? window.teachTheMachineTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS" in APP
    assert 'gameId: "teach-the-machine"' in APP
    assert "window.teachTheMachineTutorialSteps = function (classicSteps) { return window.TEACH_THE_MACHINE_PC_TUTORIAL_STEPS || classicSteps; };" in HTML
    assert HTML.index("teachTheMachineTutorialSteps") < HTML.index('src="app.js"')


def _steps():
    block = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    return block


def test_every_tutorial_selector_exists_and_the_tour_has_an_intro_and_an_outro():
    steps = _steps()
    selectors = re.findall(r'selector: "#([\w-]+)"', steps)
    assert len(selectors) >= 6 and len(re.findall(r"title: ", steps)) >= 8
    assert set(selectors) <= IDS, set(selectors) - IDS
    assert steps.count("selector") < steps.count("title: ")                      # an intro and an outro card with no spotlight
    assert len(re.findall(r"text: ", steps)) == len(re.findall(r"title: ", steps))


def test_the_tutorial_teaches_the_loop_and_does_not_promise_unbuilt_features():
    steps = _steps().lower()
    for word in ("train", "test", "why", "notebook", "shelves", "switch", "lamp", "settings", "skip"):
        assert word in steps, word
    for unbuilt in ("hint", "achievement", "goal"):
        assert unbuilt not in steps, unbuilt


def test_the_tutorial_text_is_short_and_plain():
    for text in re.findall(r'text: "([^"]+)"', _steps()):
        assert len(text) < 360, text
        assert "!" not in text


# ---- keyboard help -----------------------------------------------------------------------------------------------------
def test_the_keyboard_help_lists_this_games_own_keys_and_every_panel_it_closes_exists():
    block = HTML.split("KeyboardShortcuts.init(")[1].split("</script>")[0]
    for needle in ("lessons-toggle-button", "notebook-toggle-button", "changelog-toggle-button", "settings-toggle-button", "info-page-toggle-button",
                   "1 to 8", "T trains", "E tests", "Esc"):
        assert needle in block, needle
    for toggle, panel in re.findall(r'toggle: "([\w-]+)", panel: "([\w-]+)"', block):
        assert toggle in IDS and panel in IDS, (toggle, panel)


def test_the_keys_the_help_lists_are_the_keys_the_page_handles():
    assert 'key >= "1" && key <= "8"' in APP and 'key === "t"' in APP and 'key === "e"' in APP
    assert "aria-keyshortcuts" in HTML and 'aria-keyshortcuts="T"' in HTML and 'aria-keyshortcuts="E"' in HTML


def test_the_workshops_keys_stay_quiet_behind_a_dialog_and_the_escape_handler_defers_to_it():
    assert "function modalOpen()" in APP
    handler = APP[APP.index('document.addEventListener("keydown"'):]
    assert handler.index("modalOpen()") < handler.index('"Escape"') < handler.index('key >= "1"')
    for needle in ("[role='dialog']", "#tutorial-overlay", "#confirm-dialog-overlay"):
        assert needle in APP, needle
    assert 'querySelector(".confirm-dialog, [role=\'dialog\']")' not in APP           # a hidden dialog must not silence the keys for good


def test_the_shortcut_keys_do_not_clash_with_the_shared_help_key():
    assert 'key === "?"' not in APP and "e.key === '?'" not in APP        # ? belongs to shared/keyboard-shortcuts.js


# ---- confirm dialogs ---------------------------------------------------------------------------------------------------
def test_start_over_asks_first_and_cannot_be_silenced():
    assert "askThen(" in APP and "teach-the-machine-reset" in APP and "allowSkip: false" in APP
    reset = APP[APP.index("teach-the-machine-reset") - 200:APP.index("teach-the-machine-reset") + 400]
    assert 'action: "reset"' in reset
    assert 'id="reset-button"' in HTML and "It asks first" in HTML
    assert 'action: "reset"' not in APP.replace(reset, "")                                 # no other path resets without asking


def test_nothing_that_loses_progress_runs_from_a_bare_key():
    keys = APP[APP.index('key >= "1"'):]
    assert "reset" not in keys.split("async function boot")[0]


# ---- About, sources, what's new ----------------------------------------------------------------------------------------
def test_about_names_its_sources_the_live_read_and_the_fallback_and_links_the_sources_page():
    v = info.view()
    assert len(v["facts"]) >= 3 and v["pledge"] and v["how"]
    assert "could not be reached just now" in APP and "Read live on" in APP
    assert "sources.html?game=teach-the-machine" in HTML and 'id="sources-link"' in HTML
    assert 'target = "_blank"' in APP and "noopener noreferrer" in APP                      # source links open safely
    sources = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    assert sources["game"] == "teach-the-machine" and sources["research"]


def test_whats_new_is_a_toolbar_panel_fed_by_the_changelog_and_shared_with_the_returning_player_banner():
    assert 'id="changelog-toggle-button"' in HTML and 'id="changelog-panel"' in HTML and 'id="changelog-entries"' in HTML
    assert "window.CHANGELOG_JSON = text" in APP and "shared/whats-new-banner.js" in HTML
    data = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    assert len(data) >= 2
    assert any("opening screen" in e["entry"] and "tutorial" in e["entry"].lower() for e in data)
    dates = [e["date"] for e in data]
    assert dates == sorted(dates, reverse=True)                                           # the file is written newest first


def test_same_day_changelog_entries_keep_their_file_order():
    assert "a.date < b.date ? 1 : a.date > b.date ? -1 : 0" in APP


# ---- light theme and accessibility -------------------------------------------------------------------------------------
def test_light_theme_is_switchable_from_settings_and_follows_the_site_theme():
    assert 'id="theme-setting-button"' in HTML and "NoyvjTheme" in SETTINGS and "noyvj-theme-change" in SETTINGS
    assert "../../shared/theme.js" in HTML and "../../shared/theme-light-games.css" in HTML
    assert 'html[data-theme="light"]' in CSS


def test_reduced_motion_effects_and_high_contrast_are_honoured_and_the_tour_respects_them():
    for attr in ("data-reduced-motion", "data-effects", "data-high-contrast"):
        assert attr in SETTINGS and attr in CSS, attr
    assert "prefers-reduced-motion" in SETTINGS
    assert "animation: none" in CSS or "animation-duration" in CSS or "transition: none" in CSS


def test_the_toolbar_has_short_labels_for_a_phone_and_the_short_label_is_not_the_only_name():
    for button in ("tutorial-restart-button", "changelog-toggle-button", "notebook-toggle-button"):
        tag = HTML[HTML.index('id="%s"' % button):]
        tag = tag[:tag.index("</button>")]
        assert 'class="btn-long"' in tag and 'class="btn-short" aria-hidden="true"' in tag, button
    assert "max-width: 420px" in CSS and ".btn-short { display: inline; }" in CSS


def test_panels_are_real_regions_with_headings_and_their_buttons_say_when_they_are_open():
    for name in ("lessons", "notebook", "changelog", "info-page", "settings"):
        panel = HTML[HTML.index('id="%s-panel"' % name):]
        panel = panel[:panel.index("</section>")]
        assert 'aria-labelledby="%s-heading"' % name in HTML and 'id="%s-heading"' % name in panel
        assert 'aria-controls="%s-panel"' % name in HTML
    assert 'aria-expanded="false"' in HTML and 'aria-expanded", String(open)' in APP


def test_the_page_has_a_skip_link_a_live_region_and_the_shared_touch_target_sheet():
    assert 'class="skip-link"' in HTML and 'href="#lesson-panel"' in HTML and 'id="lesson-panel"' in HTML and 'tabindex="-1"' in HTML
    assert 'id="announce"' in HTML and 'aria-live="polite"' in HTML and 'role="status"' in HTML
    assert "../../shared/touch-targets.css" in HTML and "../../shared/a11y.css" in HTML
    assert "min-height: 44px" in CSS or "min-height: 2.75rem" in CSS or "touch-targets" in HTML


def test_the_page_fits_a_320_pixel_phone_by_construction():
    assert "overflow-wrap" in CSS or "word-break" in CSS
    assert "overflow-x: hidden" not in CSS                                                  # nothing is clipped to hide a layout problem
    assert 'name="viewport" content="width=device-width, initial-scale=1.0"' in HTML
    assert "@media (max-width: 420px)" in CSS or "@media (max-width: 480px)" in CSS or "@media (max-width: 640px)" in CSS


def test_the_standard_kit_adds_no_clock_and_no_random_source_to_the_view():
    for banned in ("Math.random", "Date.now", "setInterval", "entropy"):
        assert banned not in APP, banned
