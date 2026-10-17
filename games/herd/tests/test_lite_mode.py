"""F-26 Herd's part of lite mode: the shared switch is in Settings and Herd's own costs are off under it."""

from pathlib import Path
from .pagefiles import game_css, page_text

HERE = Path(__file__).resolve().parent.parent
CSS = game_css()


def test_the_shared_lite_switch_is_in_settings_on_both_pages():
    for page in ("index.html", "pc.html"):
        html = page_text(page)
        assert 'id="lite-mode-checkbox" data-lite-toggle' in html and "data-lite-status" in html
        assert "shared/lite-mode.js" in html and "shared/lite-mode.css" in html


def test_haze_wisps_clouds_cow_motion_and_blur_are_off_in_lite_mode():
    for selector in (".haze-overlay", ".pasture-visual-wisp", ".pasture-visual-cloud"):
        assert f'html[data-lite="true"] {selector}' in CSS
    assert 'html[data-lite="true"] .pasture-visual-cow { animation: none' in CSS
    assert "backdrop-filter: none" in CSS


def test_no_information_is_lost_the_numbers_stay_in_text(game_env):
    game_env.farm.methane = 30.0
    game_env.module.render()
    assert "income loss" in game_env.elements["pressure-display"].innerText
    assert "Methane" in game_env.elements["methane-display"].innerText
