"""Milestone 7: the Desktop boot (pc.html) is generated from index.html + pc-config.json; these keep the pieces honest from inside the
game's own folder (shared/tests/test_pc_games.py checks the same generic things for every game)."""

import importlib.util
import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parent.parent
CFG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
CLASSIC = (GAME_DIR / "index.html").read_text(encoding="utf-8")
DESKTOP = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
SETTINGS = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
SHELL = {"pc-stagebar", "pc-stage", "pc-side", "pc-topbar", "pc-body", "pc-menu-button", "pc-hud", "pc-readouts"}


def _ids(html):
    return set(re.findall(r'(?<![-\w])id="([^"]+)"', html))


def _generator():
    spec = importlib.util.spec_from_file_location("generate_pc_pages", ROOT / "scripts" / "generate-pc-pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pc_html_is_exactly_what_the_generator_makes_from_the_classic_page():
    assert DESKTOP == _generator().build("reaction-bench", CFG)


def test_both_pages_share_the_game_id_so_the_save_is_shared():
    assert set(re.findall(r'data-game-id="([^"]+)"', CLASSIC)) == {"reaction-bench"}
    assert set(re.findall(r'data-game-id="([^"]+)"', DESKTOP)) == {"reaction-bench"}
    assert 'data-pc-page="pc.html"' in CLASSIC and 'data-classic-page="index.html"' in CLASSIC
    assert CLASSIC.index("layout-pref.js") < CLASSIC.index("<title>") or CLASSIC.index("layout-pref.js") < CLASSIC.index("theme.js")


def test_every_id_app_js_and_settings_js_use_exists_in_both_pages():
    used = set(re.findall(r'\$\("([^"]+)"\)', APP)) | set(re.findall(r'mount\("#([\w-]+)"', APP)) | set(re.findall(r'getElementById\("([^"]+)"\)', SETTINGS))
    # the goals strip, the suggestion box, the difficulty slot, the periodic table and its card, the route note and the ledger
    assert {"goals", "hint-box", "hint-button", "difficulty-slot", "table", "element-card", "table-text", "route-line", "ledger-body", "equation",
            "choice-list", "achievements-list", "achievements-count", "orders", "shelf", "run-button"} <= used
    for name, html in (("index.html", CLASSIC), ("pc.html", DESKTOP)):
        assert used <= _ids(html), (name, sorted(used - _ids(html)))
    for needle in ("equation", "ledger-block", "bench-panel", "table", "goals", "difficulty-slot"):
        assert len(re.findall(r'(?<![-\w])id="%s"' % needle, DESKTOP)) == 1, needle


def test_every_classic_toolbar_button_is_an_icon_a_menu_entry_or_a_window_toggle():
    kept = {i for i, _e in CFG["toolbar"]["icons"]} | {i for g in CFG["toolbar"]["menu"] for i in g["ids"]}
    kept |= {toggle for _p, toggle, _t in CFG["windows"] if toggle}
    block = re.search(r'<div class="game-toolbar">(.*?)\n  </div>', CLASSIC, re.S).group(1)
    buttons = re.findall(r'<button[^>]*\bid="([^"]+)"', block)
    assert len(buttons) == 8
    for button in buttons:
        assert button in kept, button


def test_every_panel_is_reachable_from_an_icon_the_menu_or_a_window():
    panels = {m for m in re.findall(r'<section id="([\w-]+-panel)"', CLASSIC)}
    reachable = {p for p, _t, _title in CFG["windows"]}
    # the bench and difficulty panels are the stage and the side column; every other panel is a window
    assert panels - reachable == {"bench-panel", "difficulty-panel"}
    assert "#bench-panel" in CFG["zones"]["stage"] and "#difficulty-panel" in CFG["zones"]["side"]
    for _p, toggle, _title in CFG["windows"]:
        assert toggle in CLASSIC


def test_the_orders_shelf_table_achievements_and_settings_are_reachable_on_the_desktop():
    windows = {tuple(w[:2]) for w in CFG["windows"]}
    for pair in (("orders-panel", "orders-toggle-button"), ("shelf-panel", "shelf-toggle-button"), ("table-panel", "table-toggle-button"),
                 ("achievements-panel", "achievements-toggle-button"), ("settings-panel", "settings-toggle-button"),
                 ("changelog-panel", "changelog-toggle-button"), ("info-page-panel", "info-page-toggle-button")):
        assert pair in windows, pair
    table = CLASSIC[CLASSIC.index('id="table-panel"'):CLASSIC.index('id="achievements-panel"')]
    assert 'id="element-card"' in table and 'id="table-text"' in table          # the card and the text version travel inside the table window
    icons = {i for i, _e in CFG["toolbar"]["icons"]}
    assert {"orders-toggle-button", "table-toggle-button", "achievements-toggle-button", "settings-toggle-button"} <= icons
    help_ids = [g for g in CFG["toolbar"]["menu"] if g["heading"] == "Help"][0]["ids"]
    assert "tutorial-restart-button" in help_ids and "info-page-toggle-button" in help_ids and "credits-link" in help_ids


def test_the_desktop_tutorial_only_points_at_things_that_exist_there():
    selectors = re.findall(r'selector:\s*"([^"]+)"', PC_JS)
    assert len(selectors) >= 6
    for selector in selectors:
        assert selector.startswith("#") and selector[1:] in _ids(DESKTOP) | SHELL, selector
    assert "PC_TUTORIAL_STEPS" in CLASSIC and "REACTION_BENCH_PC_TUTORIAL_STEPS" in PC_JS
    assert "reactionBenchTutorialSteps" in APP and len(re.findall(r"title: ", PC_JS)) >= 8
    assert PC_JS.count("selector") < PC_JS.count("title: ")                      # an intro and an outro card with no spotlight


def test_the_stage_holds_the_bench_and_the_side_area_the_ledger_and_the_tools():
    z = CFG["zones"]
    assert z["stage"] == ["#bench-panel"] and "#stats" in z["topbar"], "the stats stay in view in the top bar"
    for needle in ("#goals", "#ledger-block", "#hint-box", "#difficulty-panel", ".order-nav"):
        assert needle in z["side"], needle
    assert z["topbar"][:2] == [".hub-back-link", "h1"]
    assert not {"#bench", "#equation", "#choice-box"} & set(z["side"] + z["hidden"] + z["stagebar"])
    block = CLASSIC[CLASSIC.index('id="ledger-block"'):CLASSIC.index('id="hint-box"')]
    for needle in ('id="ledger-heading"', 'id="ledger"', 'id="ledger-status"', 'id="run-button"', 'id="reset-dials-button"'):
        assert needle in block, needle                                            # the ledger and Run travel together


def test_only_keys_the_game_really_has_are_listed():
    keys = dict((k, v) for k, v in CFG["hints"])
    assert keys["Esc"].startswith("Menu") and "?" in keys
    for needle in ('k === "r"', 'k === "n"', 'k === "h"', 'k === "["', 'k === "]"', "ArrowUp", r"/^[1-4]$/"):
        assert needle in APP, needle
    assert {"R", "N", "H", "[ ]", "1-4"} <= set(keys)


def test_the_bench_fills_the_stage_and_the_classic_page_is_untouched():
    assert "#pc-stage > #bench-panel" in PC_CSS and "flex: 1 1 0" in PC_CSS and "#pc-stage #bench-panel > .bench { flex: 1 1 auto" in PC_CSS
    assert "margin: auto" in PC_CSS                                               # centred when there is room, top-aligned when it is taller
    assert "grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr)" in PC_CSS    # two side columns: the ledger, and the tools
    # nothing about the engine or the save changed for the Desktop boot: the page files only gained the layout script, the tutorial hook and a wrapper div
    assert "NOYVJ_LAYOUT" not in CLASSIC.replace("window.NOYVJ_LAYOUT", "") and "pc-shell" not in CLASSIC


def test_the_desktop_css_is_scoped_to_the_desktop_layout():
    for rule in re.findall(r"^([^\s/@}][^{]*)\{", PC_CSS, re.M):
        for selector in rule.split(","):
            assert selector.strip().startswith(('html[data-layout="pc"]', "#pc-")), selector


def test_the_desktop_pages_include_the_shell_and_the_game_files_in_order():
    assert DESKTOP.count("pc-shell.js") == 1 and DESKTOP.index("pc.js") < DESKTOP.index("app.js") < DESKTOP.index("pc-shell.js")
    assert DESKTOP.index("style.css") < DESKTOP.index("pc-shell.css") < DESKTOP.index("pc.css")
    assert 'data-layout="pc"' in DESKTOP and "(Desktop)" in DESKTOP


def test_this_folder_still_links_nothing_outside_itself_for_the_desktop_boot():
    for ref in re.findall(r'(?:src|href)="((?!https?:|#)[^"]+)"', DESKTOP):
        assert (GAME_DIR / ref.split("?")[0]).resolve().exists(), ref
