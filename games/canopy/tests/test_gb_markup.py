"""GB batch 1: static checks on index.html / style.css (accessibility, reduced
motion, light theme) for the new elements."""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HTML = (HERE / "index.html").read_text(encoding="utf-8")
CSS = (HERE / "style.css").read_text(encoding="utf-8")
GAME = (HERE / "game.py").read_text(encoding="utf-8")

NEW_IDS = [
    "season-indicator", "season-text", "weather-text", "perfect-streak-text", "forest-visual",
    "forest-title-display", "tend-button", "tend-status", "undo-clear-button", "forest-name-input",
    "plot-nickname-input", "almanac-toggle-button", "almanac-panel",
]


def test_every_new_element_exists_once():
    for element_id in NEW_IDS:
        assert HTML.count(f'id="{element_id}"') == 1, element_id


def test_interactive_new_elements_are_real_controls():
    for element_id in ("tend-button", "undo-clear-button", "almanac-toggle-button"):
        assert re.search(rf'<button id="{element_id}"[^>]*type="button"', HTML), element_id
    for element_id in ("forest-name-input", "plot-nickname-input"):
        assert f'<label class="names-label" for="{element_id}">' in HTML
        assert re.search(rf'<input id="{element_id}"[^>]*type="text"', HTML)


def test_status_regions_are_announced_politely():
    assert re.search(r'<p id="season-indicator"[^>]*role="status"', HTML)
    assert re.search(r'<p id="tend-status"[^>]*aria-live="polite"', HTML)
    assert re.search(r'id="perfect-streak-text"[^>]*tabindex="0"', HTML)  # the rule lives in its title: reachable by keyboard


def test_hotkeys_are_wired_and_listed_in_the_shortcut_help():
    for needle in ('key !== "t"', 'get("tend_plot")', 'get("collect_golden_seedling")', 'get("undo_last_clear")',
                   "T — tend", "G — catch a golden seedling", "U — undo the last clear"):
        assert needle in HTML, needle
    assert 'tag === "INPUT"' in HTML  # typing in the name fields must not fire hotkeys


def test_every_new_animation_has_a_reduced_motion_rule():
    start = CSS.index("GB batch 1 (planning/IMPROVEMENT-IDEAS-ROUND-3.md section GB)")
    block = re.sub(r"/\*.*?\*/", "", CSS[start:CSS.index("Light theme (Y11b")], flags=re.S)
    media_at = block.index("@media (prefers-reduced-motion: reduce)")
    media = block[media_at:]
    animated = {a.strip() for a in re.findall(r"^([^{}@]+)\{[^}]*animation:", block[:media_at], flags=re.M)}
    assert len(animated) >= 6
    for selector in animated:
        first = selector.split(",")[0].strip().split("::")[0].split(" ")[-1]
        assert first in media or selector in media, selector


def test_new_readouts_have_light_theme_rules():
    light = CSS[CSS.index("GB batch 1 (light theme)"):]
    for needle in (".season-indicator", ".plot-tile.plot-golden-seedling", ".plot-tile.plot-heart-tree",
                   ".names-input", ".almanac-item", ".undo-chip"):
        assert needle in light, needle
    for line in re.findall(r"^([^{}\n]+)\{", light, flags=re.M):
        for part in line.split(","):
            assert part.strip().startswith('html[data-theme="light"]'), part


def test_features_do_not_add_banned_timer_apis():
    assert "requestAnimationFrame" not in GAME and GAME.count("setInterval(") == 1
    gb = GAME[GAME.index("# GB batch 1 -- behaviour"):GAME.index("def render():")]
    assert "setInterval" not in gb and "setTimeout(" in gb  # only the pulse/flash clean-ups


def test_no_wildcards_or_randomness_were_added():
    assert "import random" not in GAME and "Math.random" not in HTML
