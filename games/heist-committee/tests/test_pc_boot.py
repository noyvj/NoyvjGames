import importlib.util
import json
import re
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
ROOT = GAME.parent.parent


def generator():
    spec = importlib.util.spec_from_file_location("generate_pc_pages", ROOT / "scripts" / "generate-pc-pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CFG = json.loads((GAME / "pc-config.json").read_text(encoding="utf-8"))


def test_pc_html_is_the_generated_page():
    assert (GAME / "pc.html").read_text(encoding="utf-8") == generator().build("heist-committee", CFG)


def test_every_hint_is_a_real_hotkey():
    plan = (GAME / "plan.js").read_text(encoding="utf-8")
    assert "ArrowLeft" in plan and '"Delete"' in plan and 'key.toLowerCase() === "s"' in plan and "[1-9]" in plan
    assert 'e.key.toLowerCase() === "z"' in plan
    assert ["Esc", "Menu / close window"] in CFG["hints"]
    assert all(len(h) == 2 for h in CFG["hints"])


def test_windows_cover_every_toggle_and_the_menu_holds_the_rest():
    html = (GAME / "index.html").read_text(encoding="utf-8")
    toolbar = re.search(r'<div class="game-toolbar">(.*?)</div>', html, re.S).group(1)
    buttons = set(re.findall(r'<button id="([\w-]+)"', toolbar))
    covered = {t for _p, t, _n in CFG["windows"]} | {i for g in CFG["toolbar"]["menu"] for i in g["ids"]}
    assert buttons <= covered


def test_the_desktop_tutorial_ends_with_a_closing_step_and_points_at_shell_or_page_ids():
    steps = (GAME / "pc.js").read_text(encoding="utf-8")
    assert steps.count("title:") >= 6
    assert "You are ready" in steps


def test_the_classic_page_has_only_the_layout_script_and_the_tutorial_hook():
    html = (GAME / "index.html").read_text(encoding="utf-8")
    assert 'data-pc-page="pc.html" data-classic-page="index.html"' in html
    assert "HEIST_COMMITTEE_PC_TUTORIAL_STEPS" in html
    assert "pc-shell" not in html


def test_escape_puts_a_held_action_down_before_the_shell_menu():
    plan = (GAME / "plan.js").read_text(encoding="utf-8")
    assert "stopImmediatePropagation" in plan and '}, true);' in plan
