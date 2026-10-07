"""GB batch 3: static checks that the level select, Seed Vault and level-box elements exist on BOTH
pages (index.html and the generated pc.html), are reachable on the Desktop boot, and are wired the
way the shared components expect."""

import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent
HTML = (HERE / "index.html").read_text(encoding="utf-8")
PC_HTML = (HERE / "pc.html").read_text(encoding="utf-8")
CONFIG = json.loads((HERE / "pc-config.json").read_text(encoding="utf-8"))

NEW_IDS = [
    "levels-open-button", "vault-toggle-button", "vault-panel", "vault-summary", "vault-crews", "vault-note",
    "vault-tree", "level-box", "level-status", "spirit-line", "level-leave-button", "level-effects-checkbox",
]


def test_every_new_id_exists_once_on_each_page():
    for element_id in NEW_IDS:
        assert HTML.count(f'id="{element_id}"') == 1, ("index.html", element_id)
        assert PC_HTML.count(f'id="{element_id}"') == 1, ("pc.html", element_id)


def test_the_desktop_page_is_not_stale():
    spec = importlib.util.spec_from_file_location("gen", ROOT / "scripts" / "generate-pc-pages.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert gen.build("canopy", CONFIG) == PC_HTML


def test_the_shared_components_are_included_on_both_pages():
    for page in (HTML, PC_HTML):
        assert '<script src="../../shared/skill-tree.js"></script>' in page
        assert '<link rel="stylesheet" href="../../shared/skill-tree.css">' in page
        assert re.search(r'<script src="../../shared/level-select.js" data-game-id="canopy" data-levels="levels.json" data-open="#levels-open-button"></script>', page)
    assert (HERE / "levels.json").exists()


def test_the_levels_button_is_a_real_button_with_a_visible_name():
    assert re.search(r'<button id="levels-open-button"[^>]*type="button">🗺️ Levels</button>', HTML)
    assert re.search(r'<button id="vault-toggle-button"[^>]*type="button">', HTML)


def test_the_desktop_menu_and_windows_reach_the_new_panels():
    menu_ids = [i for group in CONFIG["toolbar"]["menu"] for i in group["ids"]]
    assert "levels-open-button" in menu_ids
    assert ["vault-panel", "vault-toggle-button", "Seed Vault"] in CONFIG["windows"]
    assert "#level-box" in CONFIG["zones"]["stagebar"]
    assert any(h[0] == "P" for h in CONFIG["hints"])


def test_the_level_box_is_a_status_region_and_the_spirit_line_is_not_double_announced():
    assert re.search(r'<p id="level-status"[^>]*role="status"', HTML)
    assert re.search(r'<p id="spirit-line"[^>]*hidden>', HTML) and 'id="spirit-line" class="spirit-line" role' not in HTML
    assert re.search(r'<div id="level-box"[^>]*hidden>', HTML)


def test_the_poacher_key_is_routed_and_listed():
    assert 'key !== "p"' in HTML and 'get("hotkey_drive_off_poacher")' in HTML
    assert "P — drive off the poacher" in HTML
    assert '{ toggle: "vault-toggle-button", panel: "vault-panel" }' in HTML


def test_the_level_select_does_not_fight_the_grid_keys_or_the_desktop_menu():
    assert HTML.count("#level-select:not([hidden])") == 2  # the arrow-key and C/R modal lists
    assert "e.__pcMenuOpened = true" in HTML


def test_the_level_select_is_not_nested_in_a_game_panel():
    """The component appends its own dialog to <body>; nothing in the page should pre-create it."""
    assert 'id="level-select"' not in HTML
