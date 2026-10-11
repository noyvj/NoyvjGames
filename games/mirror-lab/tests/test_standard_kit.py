"""Milestone 5, the standard kit: opening screen, tutorial, About, What's New, keyboard help, confirm dialogs, light theme, accessibility."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
CSS = (GAME_DIR / "style.css").read_text(encoding="utf-8")
CHANGELOG = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
IDS = set(re.findall(r'(?<![-\w])id="([^"]+)"', HTML))


def _tail_order(names):
    tail = HTML[HTML.index("pyodide.js"):]
    positions = [tail.index(n) for n in names]
    assert positions == sorted(positions), names


def test_the_opening_screen_is_wired_the_way_the_siblings_do_it():
    assert re.search(r'<script src="\.\./\.\./shared/opening-screen\.js" data-game-id="mirror-lab" data-game-name="Mirror Lab"', HTML)
    _tail_order(["shared/tutorial.js", "shared/hub-auth.js", "shared/save-widget.js", "shared/opening-screen.js", "shared/confirm-dialog.js", "shared/difficulty.js", 'src="app.js"',
                 "shared/whats-new-banner.js", "shared/keyboard-shortcuts.js"])
    assert "settings-toggle-button" in IDS and "info-page-toggle-button" in IDS        # the screen's Settings and Info buttons click these


def test_the_tutorial_is_skippable_reopenable_and_points_at_real_elements():
    assert "tutorial-restart-button" in IDS and 'GameTutorial.init(window.mirrorLabTutorialSteps ? window.mirrorLabTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "mirror-lab" })' in APP
    block = APP.split("var TUTORIAL_STEPS = [")[1].split("];")[0]
    selectors = re.findall(r'selector: "#([^"]+)"', block)
    assert len(selectors) >= 6 and len(re.findall(r"title:", block)) >= 8
    assert set(selectors) <= IDS, set(selectors) - IDS
    for text in re.findall(r'text: "([^"]+)"', block):
        assert len(text) < 420                                                          # short cards, not paragraphs of paragraphs
    assert "Skip" in block or "skip" in block


def test_whats_new_has_a_panel_a_changelog_and_the_shared_banner():
    assert len(CHANGELOG) >= 3
    for e in CHANGELOG:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) and 40 < len(e["entry"]) < 900
    dates = [e["date"] for e in CHANGELOG]
    assert dates == sorted(dates, reverse=True)
    assert "window.CHANGELOG_JSON = text" in APP and 'data-game-id="mirror-lab"' in HTML.split("whats-new-banner.js")[1][:40]
    assert "changelog-panel" in IDS and "changelog-entries" in IDS and "changelog-toggle-button" in IDS


def test_the_keyboard_help_lists_every_panel_toggle_and_the_bench_keys():
    block = HTML.split("KeyboardShortcuts.init(")[1].split("</script>")[0]
    pairs = re.findall(r'toggle: "([^"]+)", panel: "([^"]+)"', block)
    assert len(pairs) == 6
    for toggle, panel in pairs:
        assert toggle in IDS and panel in IDS
        assert re.search(r'id="%s"[^>]*aria-controls="%s"' % (toggle, panel), HTML)
        assert re.search(r'<section id="%s"[^>]*\bhidden\b' % panel, HTML)
    for key_text in ("arrow keys", "Enter", "Escape", "Tab"):
        assert key_text in block


def test_destructive_actions_ask_first_through_the_shared_confirm_dialog():
    assert "ConfirmDialog.ask" in APP
    assert "mirror-lab-reset" in APP and "mirror-lab-place-answer" in APP
    for ask in re.findall(r"ConfirmDialog\.ask\(\{[^}]*\}", APP):
        assert "allowSkip: false" in ask                                                # never offer "don't ask again" for these two
    assert 'id="reset-button"' in HTML and "Erases your cleared benches" in HTML


def test_the_light_theme_has_its_own_values_for_every_colour_and_a_switch():
    dark = CSS.split(":root {")[1].split("}")[0]
    light = CSS.split('html[data-theme="light"] {')[1].split("}")[0]
    dark_vars = set(re.findall(r"(--[\w-]+):", dark))
    light_vars = set(re.findall(r"(--[\w-]+):", light))
    assert dark_vars == light_vars, dark_vars ^ light_vars
    assert "theme-setting-button" in IDS and "shared/theme-light-games.css" in HTML and "shared/theme.js" in HTML
    for new_class in (".ml-ghost-frame", ".goals", ".hint-box"):
        block = CSS.split(new_class)[1].split("}")[0]
        assert not re.search(r"#[0-9a-fA-F]{3,6}\b", block), new_class                 # new rules use the theme variables, never a fixed colour


def test_accessibility_labels_focus_and_targets():
    assert 'class="skip-link" href="#bench-panel"' in HTML and 'id="bench-panel"' in HTML
    assert 'role="status" aria-live="polite"' in HTML and 'id="announce"' in HTML
    for panel in re.findall(r'<section id="([^"]+-panel)"', HTML):
        assert re.search(r'<section id="%s"[^>]*aria-label(?:ledby)?="[^"]+"' % panel, HTML), panel
    for m in re.finditer(r'<input type="checkbox" id="([^"]+)"', HTML):
        assert re.search(r'<label>\s*<input type="checkbox" id="%s"' % m.group(1), HTML)
    for m in re.finditer(r"<button\b([^>]*)>([^<]*)</button>", HTML):
        attrs, label = m.groups()
        assert label.strip() or "aria-label" in attrs, attrs                              # no icon-only buttons
        assert 'type="button"' in attrs
    assert re.search(r"button, select \{[^}]*min-height: 44px", CSS)
    assert "button:focus-visible" in CSS and "outline: 3px solid var(--focus)" in CSS
    assert "data-reduced-motion" in CSS and "data-effects" in CSS and "data-high-contrast" in CSS
    assert re.search(r'id="hint-box" class="hint-box" tabindex="-1"', HTML)               # focus has somewhere to go when the hint button is hidden


def test_the_hint_controls_say_it_in_words_and_never_in_colour_alone():
    assert "Would you like a suggestion?" in HTML and "Place them" in HTML
    assert "Another hint" in APP and "dotted" in APP + HTML
    assert "ml-ghost-frame" in CSS and "stroke-dasharray" in CSS.split(".ml-ghost-frame")[1].split("}")[0]


def test_the_page_never_registers_a_service_worker_or_the_hub_only_includes_yet():
    assert "serviceWorker" not in HTML + APP
    assert "last-played.js" not in HTML                    # hub registration (QI-10-R) adds this
    assert 'src="../../shared/layout-pref.js" data-game-id="mirror-lab" data-pc-page="pc.html" data-classic-page="index.html"' in HTML      # the Desktop boot (QI-10-7)
