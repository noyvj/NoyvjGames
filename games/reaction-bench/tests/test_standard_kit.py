"""Milestone 5: the standard kit on the page (opening screen, tutorial, About with live and bundled sources, What's New, keyboard help,
confirm dialogs, light theme, accessibility basics) and the live PubChem read with its quiet fallback."""

import json
import re
from pathlib import Path

import info

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")


def test_the_opening_screen_is_included_after_the_save_widget_with_the_games_name():
    tail = HTML[HTML.index("pyodide.js"):]
    assert tail.index("shared/save-widget.js") < tail.index("shared/opening-screen.js") < tail.index("shared/confirm-dialog.js")
    assert 'data-game-id="reaction-bench"' in tail and 'data-game-name="Reaction Bench"' in tail and "data-tagline=" in tail
    assert tail.index("shared/tutorial.js") < tail.index("shared/save-widget.js")


def test_the_tutorial_has_a_restart_button_and_every_selector_exists():
    assert 'id="tutorial-restart-button"' in HTML and "GameTutorial.init(TUTORIAL_STEPS" in APP
    steps = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    selectors = re.findall(r'selector: "#([\w-]+)"', steps)
    assert len(selectors) >= 6 and len(re.findall(r"title: ", steps)) >= 8
    ids = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))
    assert set(selectors) <= ids, set(selectors) - ids
    assert steps.count("selector") < steps.count("title: ")                 # an intro and an outro card with no spotlight


def test_the_keyboard_help_lists_this_games_own_keys_including_the_suggestion_key():
    block = HTML.split("window.KeyboardShortcuts.init(")[1].split("</script>")[0]
    for needle in ("orders-toggle-button", "info-page-toggle-button", "H asks for a suggestion", "Esc: close the open panel", "R runs", "[ and ]"):
        assert needle in block, needle
    assert re.search(r'k === "h"', APP)


def test_confirm_dialogs_guard_the_two_things_that_take_something_from_the_player():
    assert APP.count("askThen(") >= 3 and "reaction-bench-reset" in APP and "reaction-bench-hint-answer" in APP
    assert "allowSkip: false" in APP


def test_about_names_its_sources_and_the_live_read_and_the_fallback():
    v = info.view()
    ids = [f["id"] for f in v["facts"]]
    assert {"equation", "balance", "beguin", "table", "haber", "pubchem"} <= set(ids)
    assert "could not be reached just now" in APP and "Read live on" in APP and "sources.html?game=reaction-bench" in HTML


def test_pubchem_is_read_live_with_the_day_named_and_a_quiet_fallback():
    assert "https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON" in APP
    for needle in ("read live from the PubChem Periodic Table", "live.date", "bundled snapshot", "The live read could not be reached just now", "Reading it live now"):
        assert needle in APP, needle
    assert "YearDiscovered" in APP and "AtomicMass" in APP
    assert 'live.state = "failed"' in APP
    sources = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
    pub = [s for s in sources["research"] if "pubchem" in s["url"]][0]
    assert "live" in pub["note"] and "snapshot" in pub["note"]


def test_the_page_only_reads_two_public_services_and_never_writes_anything_to_a_server():
    assert not re.search(r"method:\s*[\"'](POST|PUT|DELETE)", APP)
    assert "XMLHttpRequest" not in APP and "sendBeacon" not in APP


def test_accessibility_basics_for_the_new_controls():
    assert 'id="hint-list"' in HTML and 'aria-label="Suggestions so far"' in HTML and 'aria-live="polite"' in HTML
    assert 'class="skip-link"' in HTML and "aria-disabled" in APP and "aria-current" in APP
    assert ".dial-val.hinted" in CSS and "border-style: dashed" in CSS      # the hinted dial is dashed, never colour alone
    assert 'html[data-theme="light"]' in CSS and "data-high-contrast" in CSS and "prefers-reduced-motion" in (GAME_DIR / "settings.js").read_text(encoding="utf-8")


def test_the_whole_page_fits_a_320_pixel_phone_by_construction():
    assert "min-width: 40rem" in CSS and "overflow-x: auto" in CSS          # the periodic table scrolls inside its own box
    assert ".ledger-wrap { overflow-x: auto; }" in CSS
    assert "@media (max-width: 640px)" in CSS and "@media (max-width: 480px)" in CSS
