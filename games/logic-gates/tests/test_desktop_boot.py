"""The Desktop boot (pc.html) is generated from index.html + pc-config.json; these keep the pieces honest from inside
the game's own folder (the shared tests in shared/tests/test_pc_games.py check the same things for every game)."""

import importlib.util
import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parent.parent
CFG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
CLASSIC = (GAME_DIR / "index.html").read_text(encoding="utf-8")
DESKTOP = (GAME_DIR / "pc.html").read_text(encoding="utf-8")


def _ids(html):
    return set(re.findall(r'(?<![-\w])id="([^"]+)"', html))


def _generator():
    spec = importlib.util.spec_from_file_location("generate_pc_pages", ROOT / "scripts" / "generate-pc-pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pc_html_is_exactly_what_the_generator_makes_from_the_classic_page():
    assert DESKTOP == _generator().build("logic-gates", CFG)


def test_both_pages_share_the_game_id_so_the_save_is_shared():
    assert set(re.findall(r'data-game-id="([^"]+)"', CLASSIC)) == {"logic-gates"}
    assert set(re.findall(r'data-game-id="([^"]+)"', DESKTOP)) == {"logic-gates"}
    assert 'data-pc-page="pc.html"' in CLASSIC and "layout-pref.js" in CLASSIC


def test_every_classic_toolbar_button_is_an_icon_a_menu_entry_or_a_window_toggle():
    kept = {i for i, _e in CFG["toolbar"]["icons"]} | {i for g in CFG["toolbar"]["menu"] for i in g["ids"]}
    kept |= {toggle for _p, toggle, _t in CFG["windows"] if toggle}
    block = re.search(r'<div class="game-toolbar">(.*?)\n  </div>', CLASSIC, re.S).group(1)
    for button in re.findall(r'<button[^>]*\bid="([^"]+)"', block):
        assert button in kept, button


def test_the_desktop_tutorial_only_points_at_things_that_exist_there():
    js = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
    shell = {"pc-stagebar", "pc-stage", "pc-side", "pc-topbar", "pc-body", "pc-menu-button", "pc-hud", "pc-readouts"}
    for selector in re.findall(r'selector:\s*"#([\w-]+)"', js):
        assert selector in _ids(DESKTOP) | shell, selector
    assert "PC_TUTORIAL_STEPS" in CLASSIC


def test_the_stage_is_the_board_and_the_three_goals_and_progress_stay_visible():
    assert CFG["zones"]["stage"] == ["#board-panel"]
    for needed in ("#status-strip", "#goals", "#level-head"):
        assert needed in CFG["zones"]["stagebar"]
    assert "#check-panel" in CFG["zones"]["side"] and "#parts-panel" in CFG["zones"]["side"]
    css = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
    assert "#pc-stagebar #goals" in css and "display: none" not in css.split("#pc-stagebar #goals {")[1].split("}")[0]


def test_the_desktop_css_is_scoped_to_the_desktop_layout():
    css = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
    for rule in re.findall(r"^([^\s/@}][^{]*)\{", css, re.M):
        for selector in rule.split(","):
            selector = selector.strip()
            assert selector.startswith(('html[data-layout="pc"]', 'html[data-theme="light"][data-layout="pc"]', "#pc-", ".pc-window-frame", 'html[data-theme="light"] #pc-')), selector
