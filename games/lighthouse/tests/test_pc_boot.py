"""The Desktop boot: pc.html is generated from index.html and pc-config.json (never edited by hand), every id the config
names exists, every tutorial step points at something that exists there, and the stylesheet only touches the pc layout."""

import importlib.util
import json
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parent.parent
PC_HTML = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
PC_CSS = (GAME_DIR / "pc.css").read_text(encoding="utf-8")
PC_JS = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
CFG = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
SHELL_IDS = {"pc-stagebar", "pc-stage", "pc-side", "pc-topbar", "pc-body", "pc-menu-button", "pc-hud", "pc-readouts", "pc-menu-panel",
             "pc-hintbar", "pc-toasts", "pc-toolbar-source", "pc-hidden-readouts", "pc-fullscreen-button", "pc-classic-button", "pc-menu-display"}


def _generator():
    spec = importlib.util.spec_from_file_location("generate_pc_pages", ROOT / "scripts" / "generate-pc-pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pc_html_is_exactly_what_the_generator_builds_for_this_game():
    assert PC_HTML == _generator().build("lighthouse", CFG)
    assert 'data-layout="pc"' in PC_HTML and "pc-shell.js" in PC_HTML and 'src="pc.js"' in PC_HTML and 'href="pc.css"' in PC_HTML


def test_classic_page_redirects_to_the_desktop_page_only_through_the_shared_script():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert 'shared/layout-pref.js" data-game-id="lighthouse" data-pc-page="pc.html" data-classic-page="index.html"' in html
    assert "pc-shell" not in html and "pc.css" not in html


def test_every_config_target_exists_on_the_page():
    ids = set(re.findall(r'\sid="([^"]+)"', PC_HTML))
    for panel, toggle, title in CFG["windows"]:
        assert panel in ids and toggle in ids and title
    for button, emoji in CFG["toolbar"]["icons"]:
        assert button in ids and emoji
    in_menu = {i for group in CFG["toolbar"]["menu"] for i in group["ids"]}
    assert all(i in ids for i in in_menu)
    toolbar = re.search(r'<div class="game-toolbar">(.*?)</div>', PC_HTML, flags=re.S).group(1)
    for button in re.findall(r'<button[^>]*\sid="([^"]+)"', toolbar):
        assert button in in_menu or button in {b for b, _e in CFG["toolbar"]["icons"]} or button in {t for _p, t, _x in CFG["windows"]}, button
    for zone, selectors in CFG["zones"].items():
        for selector in selectors:
            m = re.match(r"#([\w-]+)", selector)
            if m:
                assert m.group(1) in ids, (zone, selector)
    for selector, _emoji, _label in CFG["readouts"]:
        assert selector[1:] in ids


def test_the_desktop_tutorial_only_points_at_things_that_exist_there():
    ids = set(re.findall(r'\sid="([^"]+)"', PC_HTML)) | SHELL_IDS
    selectors = re.findall(r'selector:\s*"([^"]+)"', PC_JS)
    assert len(selectors) >= 8
    for selector in selectors:
        assert selector.startswith("#") and selector[1:] in ids, selector
    assert "window.LIGHTHOUSE_PC_TUTORIAL_STEPS" in PC_JS
    assert "LIGHTHOUSE_PC_TUTORIAL_STEPS" in (GAME_DIR / "index.html").read_text(encoding="utf-8")


def test_the_hints_name_only_keys_the_game_really_has():
    keys = {k for k, _ in CFG["hints"]}
    assert {"Space", "[ ]", "1-4", "W", "T", "Esc"} <= keys
    app = (GAME_DIR / "app.js").read_text(encoding="utf-8")
    assert 'k === "w"' in app and 'k === "t"' in app and 'k >= "1" && k <= "4"' in app


def test_the_desktop_stylesheet_is_scoped_to_the_pc_layout():
    css = re.sub(r"/\*.*?\*/", "", PC_CSS, flags=re.S)
    for selector in re.findall(r"^([^@/\n{}][^{}]*)\{", css, flags=re.M):
        for part in selector.split(","):
            part = part.strip()
            if part:
                assert re.match(r'^(html\[data-layout="pc"\]|html\[data-theme="(?:light|dark)"\]|#pc-|\.pc-|\.pc-window-frame|#theme|html\[data-layout)', part) or "pc-" in part, part
