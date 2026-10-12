"""The Desktop boot (pc.html) is generated from index.html + pc-config.json; these keep the pieces honest from inside the game's own
folder (shared/tests/test_pc_games.py checks the same generic things for every game)."""

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
    assert DESKTOP == _generator().build("constellations", CFG)


def test_both_pages_share_the_game_id_so_the_save_is_shared():
    assert set(re.findall(r'data-game-id="([^"]+)"', CLASSIC)) == {"constellations"}
    assert set(re.findall(r'data-game-id="([^"]+)"', DESKTOP)) == {"constellations"}
    assert 'data-pc-page="pc.html"' in CLASSIC and 'data-classic-page="index.html"' in CLASSIC
    assert CLASSIC.index("layout-pref.js") < CLASSIC.index("<title>") or CLASSIC.index("layout-pref.js") < CLASSIC.index("theme.js")
    assert CLASSIC.index("layout-pref.js") < CLASSIC.index("shared/theme.js")


def test_every_id_app_js_and_settings_js_use_exists_in_both_pages():
    used = set(re.findall(r'\$\("([^"]+)"\)', APP)) | set(re.findall(r'mount\("#([\w-]+)"', APP)) | set(re.findall(r'getElementById\("([^"]+)"\)', (GAME_DIR / "settings.js").read_text(encoding="utf-8")))
    used -= set(re.findall(r'svgEl\("[a-z]+", \{ id: "([^"]+)"', APP))              # ids the script creates itself
    assert {"goals", "hint-box", "difficulty-slot", "board", "board-wrap", "achievements-list", "achievements-count", "zoom-in-button", "atlas",
            "atlas-cards", "season-list", "cursor-line", "status-line", "done-card"} <= used
    for name, html in (("index.html", CLASSIC), ("pc.html", DESKTOP)):
        assert used <= _ids(html), (name, sorted(used - _ids(html)))
    assert len(re.findall(r'(?<![-\w])id="board"', DESKTOP)) == 1


def test_every_classic_toolbar_button_is_an_icon_a_menu_entry_or_a_window_toggle():
    kept = {i for i, _e in CFG["toolbar"]["icons"]} | {i for g in CFG["toolbar"]["menu"] for i in g["ids"]}
    kept |= {toggle for _p, toggle, _t in CFG["windows"] if toggle}
    block = re.search(r'<div class="game-toolbar">(.*?)\n  </div>', CLASSIC, re.S).group(1)
    buttons = re.findall(r'<button[^>]*\bid="([^"]+)"', block)
    assert len(buttons) == 7
    for button in buttons:
        assert button in kept, button


def test_every_panel_is_reachable_from_an_icon_the_menu_or_a_window():
    panels = {m for m in re.findall(r'<section id="([\w-]+-panel)"', CLASSIC)}
    reachable = {p for p, _t, _title in CFG["windows"]}
    # the chart and difficulty panels are the stage and the side column; every other panel is a window
    assert panels - reachable == {"chart-panel", "difficulty-panel"}
    assert "#chart-panel" in CFG["zones"]["stage"] and "#difficulty-panel" in CFG["zones"]["side"]
    for _p, toggle, _title in CFG["windows"]:
        assert toggle in CLASSIC


def test_the_charts_the_atlas_and_the_achievements_are_reachable_on_the_desktop():
    for entry in (["charts-panel", "charts-toggle-button", "Charts"], ["atlas-panel", "atlas-toggle-button", "Sky Atlas"],
                  ["achievements-panel", "achievements-toggle-button", "Achievements"], ["settings-panel", "settings-toggle-button", "Settings"]):
        assert entry in CFG["windows"]
    icons = [i for i, _e in CFG["toolbar"]["icons"]]
    assert icons == ["charts-toggle-button", "atlas-toggle-button", "achievements-toggle-button", "settings-toggle-button"]
    atlas = CLASSIC[CLASSIC.index('id="atlas-panel"'):CLASSIC.index('id="achievements-panel"')]
    assert 'id="atlas"' in atlas and 'id="atlas-cards"' in atlas, "the atlas and its cards live inside the Sky Atlas window"
    assert 'id="season-list"' in CLASSIC[CLASSIC.index('id="charts-panel"'):CLASSIC.index('id="atlas-panel"')]


def test_the_desktop_tutorial_only_points_at_things_that_exist_there():
    selectors = re.findall(r'selector:\s*"([^"]+)"', PC_JS)
    assert len(selectors) >= 5
    for selector in selectors:
        assert selector.startswith("#") and selector[1:] in _ids(DESKTOP) | SHELL, selector
    assert "PC_TUTORIAL_STEPS" in CLASSIC and "CONSTELLATIONS_PC_TUTORIAL_STEPS" in PC_JS
    assert "constellationsTutorialSteps" in APP and "window.CONSTELLATIONS_PC_TUTORIAL_STEPS || classicSteps" in CLASSIC


def test_the_stage_holds_the_chart_and_the_side_column_the_tools_hints_and_goals():
    z = CFG["zones"]
    assert z["stage"] == ["#chart-panel"] and "#stats" in z["topbar"], "the stats stay in view in the top bar"
    assert "#goals" in z["side"], "the three goals stay in view in the side column"
    for needle in (".tools", "#hint-box", "#done-card", "#chart-text", ".chart-nav", "#difficulty-panel"):
        assert any(needle in s for s in z["side"]), needle
    assert z["topbar"][:2] == [".hub-back-link", "h1"]
    assert not {"#board-wrap", "#board", "#status-line", "#cursor-line"} & set(z["side"] + z["hidden"] + z["stagebar"])
    assert {".zoom-row", ".keys-note", ".tagline"} <= set(z["hidden"]), "the larger-board buttons are for small screens; the board fills the stage"


def test_only_keys_the_game_really_has_are_listed():
    keys = dict((k, v) for k, v in CFG["hints"])
    assert keys["Esc"].startswith("Put a star down") and "Menu" in keys["Esc"] and "?" in keys
    for needle in ('"ArrowLeft"', '"ArrowUp"', '"Home"', 'e.key === "z"', 'case " "', 'e.code === "KeyH"', "e.altKey", '"abcdefghijklmnopqrstuvwxyz"'):
        assert needle in APP, needle


def test_the_board_fills_the_stage_on_the_desktop_and_the_larger_sizes_stay_a_classic_thing():
    assert 'getAttribute("data-layout") === "pc"' in APP and "var z = pc ? 1 : ZOOMS[zoomIdx]" in APP
    assert "#pc-stage #board {" in PC_CSS and "max-height: none" in PC_CSS and "position: absolute" in PC_CSS
    assert "#pc-stage #board-wrap" in PC_CSS and "minmax(0, 1fr)" in PC_CSS
    # Classic is untouched: its board keeps its own height limit
    assert "max-height: 76vh" in (GAME_DIR / "style.css").read_text(encoding="utf-8")


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


def test_the_classic_page_gains_only_the_layout_script_the_achievements_and_the_tutorial_hook():
    assert "pc-shell" not in CLASSIC and "pc.css" not in CLASSIC and "NOYVJ_LAYOUT" not in CLASSIC.replace("window.NOYVJ_LAYOUT", "")
    assert CLASSIC.count("layout-pref.js") == 1 and CLASSIC.count("achievement-share.js") == 1
