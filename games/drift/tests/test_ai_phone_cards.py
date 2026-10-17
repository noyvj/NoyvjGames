"""R4-DRMO-2 wiring checks: the swipe cards on phones.

Compares what index.html, style.css and ui.js each assume about the other, since the first version
of this idea hid the 'Open neighbouring district' button and forced the panel visible."""
import re
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
HTML = (GAME_DIR / "index.html").read_text()
CSS = (GAME_DIR / "style.css").read_text()
JS = (GAME_DIR / "ui.js").read_text()
PC_HTML = (GAME_DIR / "pc.html").read_text()


def phone_css():
    start = CSS.index("R4-DRMO-2")
    return CSS[start:]


def test_neighbor_panel_is_a_sibling_card_of_game_inside_the_container():
    assert HTML.index('<div id="mobile-swipe-container">') < HTML.index('<div id="game">') < HTML.index('id="neighbor-panel"')
    # #game closes right before the neighbour panel opens, so the panel is a sibling card
    assert re.search(r"</div>\s*<div id=\"neighbor-panel\"", HTML)


def test_ui_js_ids_exist_in_both_pages():
    ids = re.findall(r'getElementById\("([^"]+)"\)', JS[JS.index("function mobileSwipe"):])
    assert set(ids) == {"mobile-swipe-container", "neighbor-panel", "swipe-to-neighbor", "swipe-to-region", "game"}
    for page in (HTML, PC_HTML):
        for id_ in ids:
            assert f'id="{id_}"' in page


def test_open_button_and_panel_visibility_are_not_overridden():
    css = phone_css()
    assert "neighbor-open-button" not in css
    assert "!important" not in css
    assert "#neighbor-panel[hidden] { display: none; }" in css


def test_card_layout_is_phone_only_and_the_nav_buttons_are_hidden_elsewhere():
    css = phone_css()
    before_media = css[:css.index("@media")]
    assert ".swipe-nav { display: none; }" in before_media
    assert "#mobile-swipe-container" not in before_media
    assert "scroll-snap-type: x mandatory" in css


def test_smooth_scrolling_only_when_motion_is_allowed():
    css = phone_css()
    assert "scroll-behavior: smooth" in css
    smooth = css.index("scroll-behavior: smooth")
    assert "prefers-reduced-motion: no-preference" in css[:smooth]
    assert "reduce-motion" in JS
