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
    assert DESKTOP == _generator().build("picture-grid", CFG)


def test_both_pages_share_the_game_id_so_the_save_is_shared():
    assert set(re.findall(r'data-game-id="([^"]+)"', CLASSIC)) == {"picture-grid"}
    assert set(re.findall(r'data-game-id="([^"]+)"', DESKTOP)) == {"picture-grid"}
    assert 'data-pc-page="pc.html"' in CLASSIC and 'data-classic-page="index.html"' in CLASSIC
    assert CLASSIC.index("layout-pref.js") < CLASSIC.index("<title>") or CLASSIC.index("layout-pref.js") < CLASSIC.index("theme.js")


def test_every_id_app_js_and_settings_js_use_exists_in_both_pages():
    used = set(re.findall(r'\$\("([^"]+)"\)', APP)) | set(re.findall(r'mount\("#([\w-]+)"', APP)) | set(re.findall(r'getElementById\("([^"]+)"\)', (GAME_DIR / "settings.js").read_text(encoding="utf-8")))
    assert {"goals", "hint-box", "difficulty-slot", "slideshow-button", "achievements-list", "achievements-count"} <= used
    for name, html in (("index.html", CLASSIC), ("pc.html", DESKTOP)):
        assert used <= _ids(html), (name, sorted(used - _ids(html)))
    assert len(re.findall(r'(?<![-\w])id="board"', DESKTOP)) == 1


def test_every_classic_toolbar_button_is_an_icon_a_menu_entry_or_a_window_toggle():
    kept = {i for i, _e in CFG["toolbar"]["icons"]} | {i for g in CFG["toolbar"]["menu"] for i in g["ids"]}
    kept |= {toggle for _p, toggle, _t in CFG["windows"] if toggle}
    block = re.search(r'<div class="game-toolbar">(.*?)\n  </div>', CLASSIC, re.S).group(1)
    buttons = re.findall(r'<button[^>]*\bid="([^"]+)"', block)
    assert len(buttons) == 6
    for button in buttons:
        assert button in kept, button


def test_every_panel_is_reachable_from_an_icon_the_menu_or_a_window():
    panels = {m for m in re.findall(r'<section id="([\w-]+-panel)"', CLASSIC)}
    reachable = {p for p, _t, _title in CFG["windows"]}
    # the frame and difficulty panels are the stage and the side column; every other panel is a window
    assert panels - reachable == {"frame-panel", "difficulty-panel"}
    assert "#frame-panel" in CFG["zones"]["stage"] and "#difficulty-panel" in CFG["zones"]["side"]
    for _p, toggle, _title in CFG["windows"]:
        assert toggle in CLASSIC


def test_the_achievements_the_gallery_and_the_slideshow_are_reachable_on_the_desktop():
    assert ["achievements-panel", "achievements-toggle-button", "Achievements"] in CFG["windows"]
    assert ["gallery-panel", "gallery-toggle-button", "The Long Gallery"] in CFG["windows"]
    inside_gallery = CLASSIC[CLASSIC.index('id="gallery-panel"'):CLASSIC.index('id="achievements-panel"')]
    assert 'id="slideshow-button"' in inside_gallery and 'id="large-view"' in inside_gallery


def test_the_desktop_tutorial_only_points_at_things_that_exist_there():
    selectors = re.findall(r'selector:\s*"([^"]+)"', PC_JS)
    assert len(selectors) >= 5
    for selector in selectors:
        assert selector.startswith("#") and selector[1:] in _ids(DESKTOP) | SHELL, selector
    assert "PC_TUTORIAL_STEPS" in CLASSIC and "PICTURE_GRID_PC_TUTORIAL_STEPS" in PC_JS
    assert "pictureGridTutorialSteps" in APP


def test_the_stage_holds_the_frame_and_the_side_column_the_tools_and_clues():
    z = CFG["zones"]
    assert z["stage"] == ["#frame-panel"] and "#stats" in z["topbar"], "the stats stay in view in the top bar"
    assert "#goals" in z["side"], "the three goals stay in view in the side column"
    for needle in (".tools", "#hint-box", "#hung-card", "#clue-text", ".frame-nav"):
        assert any(needle in s for s in z["side"]), needle
    assert z["topbar"][:2] == [".hub-back-link", "h1"]
    assert not {"#board-wrap", "#board"} & set(z["side"] + z["hidden"] + z["stagebar"])


def test_only_keys_the_game_really_has_are_listed():
    keys = dict((k, v) for k, v in CFG["hints"])
    assert keys["Esc"].startswith("Menu") and "?" in keys
    for needle in ('key === "f"', 'key === "x"', 'key === "h"', 'key === " "', 'ArrowUp', 'key === "z"'):
        assert needle in APP or needle.replace("key", "e.key") in APP, needle


def test_the_board_fits_the_height_of_the_desktop_stage():
    assert 'getAttribute("data-layout") === "pc"' in APP and "heightAt(cp)" in APP
    assert "wrap.clientHeight" in APP and "CELL_MAX_PC" in APP
    # Classic is untouched: without the pc attribute the height limit is infinite
    assert "var availH = pc ?" in APP and ": Infinity" in APP


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
