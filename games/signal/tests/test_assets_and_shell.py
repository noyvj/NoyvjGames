"""achievements.json / changelog.json / index.html wiring / app.js parity."""

import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")
APP_JS = (GAME_DIR / "app.js").read_text(encoding="utf-8")


def test_achievements_catalog_shape(game):
    data = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))
    ach = data["achievements"]
    assert len(ach) == 18
    ids = [a["id"] for a in ach]
    assert len(set(ids)) == len(ids)
    for a in ach:
        assert re.fullmatch(r"[a-z0-9_]{1,64}", a["id"])
        assert a["label"].strip() and a["description"].strip()
    plan = {"first_contact", "clean_signal", "under_par", "lucky_guess", "three_in_a_row", "week_on_air",
            "month_on_air", "hard_copy", "both_bands", "last_gasp", "static", "archivist", "overlap",
            "silent_night", "show_off", "puzzle_100"}
    assert plan <= set(ids)  # all 16 achievements the plan lists (item 5 is three of them)
    assert game.ACHIEVEMENT_IDS == ids


def test_every_achievement_id_is_reachable_by_the_engine(game):
    """Each id appears as a literal `_earn(...)` target, so none is dead."""
    source = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    for aid in game.ACHIEVEMENT_IDS:
        assert '_earn("%s"' % aid in source, aid


def test_changelog_shape_and_order(game):
    log = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))["changelog"]
    assert 1 <= len(log) <= 30
    dates = [e["date"] for e in log]
    assert dates == sorted(dates, reverse=True)
    for e in log:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]) and e["entry"].strip()
    assert game.CHANGELOG == log


def test_epoch_matches_between_engine_and_shell(game):
    assert re.search(r'var EPOCH = "%s";' % re.escape(game.EPOCH), APP_JS)


def test_shell_includes_every_shared_piece():
    for needle in (
        "shared/theme.js", "shared/theme-light-games.css", "shared/site-settings.js", "shared/tutorial.js",
        "shared/mobile-dock.js", "shared/confirm-dialog.js", "shared/hub-auth.js", "shared/save-widget.js",
        "shared/opening-screen.js", "shared/last-played.js", "shared/whats-new-banner.js",
        "shared/achievement-stats.js", "shared/leaderboard.js", "shared/keyboard-shortcuts.js",
        "ad-bar.css", "manifest.json", "settings.js", 'data-game-id="signal"',
    ):
        assert needle in HTML, needle
    assert 'data-board="best_streak"' in HTML and 'data-order="desc"' in HTML
    assert "pyodide.js" not in HTML  # the engine is loaded lazily by app.js, never in <head>
    assert "pyodide" in APP_JS and "PYODIDE_URL" in APP_JS


def test_every_shared_script_the_page_references_exists():
    for src in re.findall(r'(?:src|href)="(\.\./\.\./[^"]+)"', HTML):
        assert (GAME_DIR / src).resolve().exists(), src


def test_ids_the_shared_scripts_and_app_expect_exist():
    ids = set(re.findall(r'id="([^"]+)"', HTML))
    for needed in (
        "tutorial-restart-button", "howto-toggle-button", "howto-panel", "achievements-toggle-button",
        "achievements-panel", "changelog-toggle-button", "changelog-panel", "settings-toggle-button",
        "settings-panel", "info-page-toggle-button", "info-page-panel", "leaderboard-mount", "board", "commit-button",
    ):
        assert needed in ids, needed
    for used in re.findall(r'\$\("([a-z-]+)"\)', APP_JS):
        assert used in ids, used


def test_engine_has_no_dom_dependency():
    source = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    assert "document." not in source and "getElementById" not in source
    assert len(re.findall(r"^\s+import js\b", source, re.M)) == 2  # the optional asset read and the optional UI hook, both guarded


def test_settings_js_uses_its_own_storage_keys_and_stays_out_of_the_save():
    text = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert "signal-text-scale" in text and "signal-high-contrast" in text and "signal-reduced-motion" in text
    assert "pyodide.globals" not in text and "window.pyodide" not in text


def test_favicon_is_a_valid_small_svg():
    svg = (GAME_DIR / "favicon-signal.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and svg.strip().endswith("</svg>") and len(svg) < 2000
